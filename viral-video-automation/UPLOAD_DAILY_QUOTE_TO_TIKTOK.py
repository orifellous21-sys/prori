import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from DAILY_QUOTE_VIDEO_EMAIL import OUTPUT, choose_quote


ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(ROOT, "tiktok_uploads")
TIME_ZONE = ZoneInfo("Asia/Jerusalem")
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
CREATOR_INFO_URL = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"


def local_now():
    return datetime.now(TIME_ZONE)


def local_date_key(now):
    return now.strftime("%Y-%m-%d")


def fail(message):
    print(json.dumps({"ok": False, "error": message}, indent=2))
    sys.exit(1)


def post_form(url, data):
    body = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        fail(f"TikTok token refresh failed {error.code}: {details}")


def post_json(url, payload, access_token):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        fail(f"TikTok API error {error.code}: {details}")


def get_access_token():
    client_key = os.environ.get("TIKTOK_CLIENT_KEY")
    client_secret = os.environ.get("TIKTOK_CLIENT_SECRET")
    refresh_token = os.environ.get("TIKTOK_REFRESH_TOKEN")
    if not client_key or not client_secret or not refresh_token:
        fail("Missing one or more TikTok OAuth secrets.")

    result = post_form(
        TOKEN_URL,
        {
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )
    token = result.get("access_token")
    if not token:
        fail(f"TikTok token refresh did not return access_token: {result}")
    if result.get("refresh_token") and result["refresh_token"] != refresh_token:
        print("WARNING: TikTok returned a new refresh_token. Update TIKTOK_REFRESH_TOKEN if uploads later fail.")
    return token


def tiktok_response_data(result):
    if result.get("error", {}).get("code") not in (None, "ok"):
        fail(f"TikTok returned an error: {result}")
    return result.get("data", {})


def build_title(date_key, quote):
    quote_text = quote["text"]
    speaker = quote["speaker"]
    caption = f'"{quote_text}" - {speaker}\n\n#quotes #wisdom #fyp'
    return caption[:2200]


def choose_privacy_level(creator_info):
    requested = os.environ.get("TIKTOK_PRIVACY_LEVEL", "").strip()
    options = creator_info.get("privacy_level_options") or []
    if requested:
        if requested not in options:
            fail(f"Requested TIKTOK_PRIVACY_LEVEL={requested} is not available. Options: {options}")
        return requested
    for option in ("PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"):
        if option in options:
            return option
    fail(f"TikTok returned no usable privacy_level_options: {creator_info}")


def query_creator_info(access_token):
    return tiktok_response_data(post_json(CREATOR_INFO_URL, {}, access_token))


def init_upload(access_token, video_path, title, privacy_level):
    size = os.path.getsize(video_path)
    chunk_size = size
    payload = {
        "post_info": {
            "title": title,
            "privacy_level": privacy_level,
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
            "video_cover_timestamp_ms": 1000,
            "brand_content_toggle": False,
            "brand_organic_toggle": False,
            "is_aigc": os.environ.get("TIKTOK_IS_AIGC", "1") != "0",
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": size,
            "chunk_size": chunk_size,
            "total_chunk_count": 1,
        },
    }
    data = tiktok_response_data(post_json(INIT_URL, payload, access_token))
    upload_url = data.get("upload_url")
    publish_id = data.get("publish_id")
    if not upload_url or not publish_id:
        fail(f"TikTok did not return upload_url and publish_id: {data}")
    return upload_url, publish_id, size


def upload_file(upload_url, video_path, size):
    with open(video_path, "rb") as handle:
        data = handle.read()
    request = urllib.request.Request(
        upload_url,
        data=data,
        headers={
            "Content-Type": "video/mp4",
            "Content-Length": str(size),
            "Content-Range": f"bytes 0-{size - 1}/{size}",
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            response.read()
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        fail(f"TikTok file upload failed {error.code}: {details}")


def fetch_status(access_token, publish_id):
    return tiktok_response_data(post_json(STATUS_URL, {"publish_id": publish_id}, access_token))


def wait_for_status(access_token, publish_id):
    last = {}
    for _ in range(12):
        last = fetch_status(access_token, publish_id)
        status = last.get("status")
        if status in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX", "FAILED"):
            return last
        time.sleep(10)
    return last


def main():
    if os.environ.get("TIKTOK_TOKEN_CHECK_ONLY") == "1":
        get_access_token()
        print(json.dumps({"ok": True, "tiktok_oauth": "token refresh succeeded"}, indent=2))
        return

    now = local_now()
    force_send = os.environ.get("FORCE_SEND") == "1"
    if not force_send and now.hour < 16:
        print(f"Skipping TikTok upload: it is {now:%H:%M} in Asia/Jerusalem, before 16:00.")
        return

    date_key = local_date_key(now)
    video_path = os.path.join(OUTPUT, f"daily_quote_youtube_{date_key}.mp4")
    state_path = os.path.join(STATE_DIR, f"{date_key}.json")
    if os.path.exists(state_path):
        print(f"Skipping TikTok upload: state already exists for {date_key}.")
        return
    if not os.path.exists(video_path):
        print(f"Skipping TikTok upload: video file does not exist: {video_path}")
        return

    quote = choose_quote(date_key)
    access_token = get_access_token()
    creator_info = query_creator_info(access_token)
    privacy_level = choose_privacy_level(creator_info)
    title = build_title(date_key, quote)

    if os.environ.get("TIKTOK_UPLOAD_DRY_RUN") == "1":
        print(json.dumps({"ok": True, "dry_run": True, "video": video_path, "privacy_level": privacy_level, "title": title}, indent=2))
        return

    upload_url, publish_id, size = init_upload(access_token, video_path, title, privacy_level)
    upload_file(upload_url, video_path, size)
    status = wait_for_status(access_token, publish_id)

    os.makedirs(STATE_DIR, exist_ok=True)
    state = {
        "date": date_key,
        "publish_id": publish_id,
        "title": title,
        "privacy_level": privacy_level,
        "status": status,
        "uploaded_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    with open(state_path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
        handle.write("\n")

    print(json.dumps({"ok": True, "tiktok": state}, indent=2))


if __name__ == "__main__":
    main()
