import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from DAILY_QUOTE_VIDEO_EMAIL import OUTPUT, choose_quote


ROOT = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(ROOT, "youtube_uploads")
TIME_ZONE = ZoneInfo("Asia/Jerusalem")
TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


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
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def request_json(url, payload, headers, method="POST"):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json; charset=UTF-8"},
        method=method,
    )
    try:
        return urllib.request.urlopen(request, timeout=60)
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        fail(f"YouTube API error {error.code}: {details}")


def get_access_token():
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    if not client_id or not client_secret or not refresh_token:
        fail("Missing one or more YouTube OAuth secrets.")

    result = post_form(
        TOKEN_URL,
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    token = result.get("access_token")
    if not token:
        fail(f"Google token refresh did not return access_token: {result}")
    return token


def build_metadata(date_key, quote):
    quote_text = quote["text"]
    speaker = quote["speaker"]
    title_quote = quote_text if len(quote_text) <= 62 else f"{quote_text[:59].rstrip()}..."
    title = f"{speaker}: {title_quote} #Shorts"
    if len(title) > 100:
        title = f"{speaker} quote #Shorts"
    description = (
        f'"{quote_text}"\n'
        f"- {speaker}\n\n"
        "Daily historical quote short.\n"
        "#shorts #quotes #wisdom"
    )
    return {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["shorts", "quotes", "wisdom", speaker],
            "categoryId": "22",
        },
        "status": {
            "privacyStatus": os.environ.get("YOUTUBE_PRIVACY_STATUS", "public"),
            "selfDeclaredMadeForKids": False,
        },
    }


def start_resumable_upload(access_token, metadata, video_path):
    params = urllib.parse.urlencode({"uploadType": "resumable", "part": "snippet,status"})
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Upload-Content-Length": str(os.path.getsize(video_path)),
        "X-Upload-Content-Type": "video/mp4",
    }
    response = request_json(f"{UPLOAD_URL}?{params}", metadata, headers)
    location = response.headers.get("Location")
    if not location:
        fail("YouTube did not return a resumable upload URL.")
    return location


def upload_video(upload_url, access_token, video_path):
    with open(video_path, "rb") as handle:
        data = handle.read()
    request = urllib.request.Request(
        upload_url,
        data=data,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "video/mp4",
            "Content-Length": str(len(data)),
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        fail(f"YouTube upload failed {error.code}: {details}")


def main():
    now = local_now()
    force_send = os.environ.get("FORCE_SEND") == "1"
    if not force_send and now.hour < 16:
        print(f"Skipping YouTube upload: it is {now:%H:%M} in Asia/Jerusalem, before 16:00.")
        return

    date_key = local_date_key(now)
    video_path = os.path.join(OUTPUT, f"daily_quote_youtube_{date_key}.mp4")
    state_path = os.path.join(STATE_DIR, f"{date_key}.json")
    if os.path.exists(state_path):
        print(f"Skipping YouTube upload: state already exists for {date_key}.")
        return
    if not os.path.exists(video_path):
        print(f"Skipping YouTube upload: video file does not exist: {video_path}")
        return

    quote = choose_quote(date_key)
    metadata = build_metadata(date_key, quote)
    if os.environ.get("YOUTUBE_UPLOAD_DRY_RUN") == "1":
        print(json.dumps({"ok": True, "dry_run": True, "video": video_path, "metadata": metadata}, indent=2))
        return

    access_token = get_access_token()
    upload_url = start_resumable_upload(access_token, metadata, video_path)
    result = upload_video(upload_url, access_token, video_path)
    video_id = result.get("id")
    if not video_id:
        fail(f"YouTube upload response did not include a video id: {result}")

    os.makedirs(STATE_DIR, exist_ok=True)
    state = {
        "date": date_key,
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": metadata["snippet"]["title"],
        "privacyStatus": metadata["status"]["privacyStatus"],
        "uploaded_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    with open(state_path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
        handle.write("\n")

    print(json.dumps({"ok": True, "youtube": state}, indent=2))


if __name__ == "__main__":
    main()
