import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
from datetime import datetime

import numpy as np


API_BASE = "https://api.json2video.com/v2"
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "output", "json2video")
TEMP = os.path.join(ROOT, "output", "json2video_temp")
os.makedirs(OUT, exist_ok=True)
os.makedirs(TEMP, exist_ok=True)

API_KEY = os.environ.get("J2V_API_KEY")
if not API_KEY:
    raise SystemExit("Missing J2V_API_KEY environment variable")

SCRIPT = (
    "In 1919, Boston was hit by a wave nobody expected. "
    "Not water. Molasses. "
    "A giant storage tank split open and released more than two million gallons of black syrup. "
    "The wave smashed buildings, lifted a train off its tracks, and buried streets in sticky darkness. "
    "People thought it was a joke. It became one of America's strangest disasters. "
    "The lesson is simple: even ordinary things become terrifying when nobody respects pressure."
)

CAPTIONS = [
    (0.4, 3.1, "BOSTON WAS HIT BY A WAVE"),
    (3.1, 5.2, "NOT WATER"),
    (5.2, 7.2, "MOLASSES"),
    (7.2, 11.2, "TWO MILLION GALLONS BROKE FREE"),
    (11.2, 15.5, "THE BLACK WAVE SMASHED BUILDINGS"),
    (15.5, 19.0, "AND LIFTED A TRAIN OFF ITS TRACKS"),
    (19.0, 23.2, "PEOPLE THOUGHT IT WAS A JOKE"),
    (23.2, 27.4, "IT BECAME ONE OF AMERICA'S STRANGEST DISASTERS"),
    (27.4, 30.0, "NEVER IGNORE PRESSURE"),
]


def request_json(method, url, data=None, headers=None, timeout=60):
    body = None if data is None else json.dumps(data).encode("utf-8")
    req_headers = {"x-api-key": API_KEY}
    if body is not None:
        req_headers["Content-Type"] = "application/json"
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: HTTP {exc.code}: {detail}") from exc


def put_file(url, path, content_type):
    with open(path, "rb") as f:
        data = f.read()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": content_type}, method="PUT")
    with urllib.request.urlopen(req, timeout=90) as res:
        return res.status


def make_music(path, seconds=31, sample_rate=44100):
    n = int(seconds * sample_rate)
    t = np.arange(n, dtype=np.float32) / sample_rate
    drone = 0.24 * np.sin(2 * np.pi * 46.25 * t)
    low = 0.18 * np.sin(2 * np.pi * 69.3 * t)
    pulse = 0.12 * np.sin(2 * np.pi * 92.5 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.65 * t))
    shimmer = 0.025 * np.sin(2 * np.pi * 740 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.13 * t))
    hits = np.zeros_like(t)
    for beat in np.arange(0.0, seconds, 2.0):
        start = int(beat * sample_rate)
        length = min(int(0.28 * sample_rate), n - start)
        if length > 0:
            env = np.exp(-np.linspace(0, 6.5, length))
            tt = np.arange(length, dtype=np.float32) / sample_rate
            hits[start:start + length] += 0.46 * env * np.sin(2 * np.pi * 72 * tt)
    fade = np.minimum(1, t / 1.5) * np.minimum(1, (seconds - t) / 2.0)
    audio = (drone + low + pulse + shimmer + hits) * fade * 0.30
    peak = float(np.max(np.abs(audio))) or 1.0
    audio = audio / max(1, peak / 0.92)
    pcm = (audio * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())


def upload_music():
    wav_path = os.path.join(TEMP, "molasses_cinematic_music.wav")
    make_music(wav_path)
    size = os.path.getsize(wav_path)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"molasses_cinematic_music_{stamp}.wav"
    try:
        upload = request_json(
            "POST",
            f"{API_BASE}/media/file",
            {
                "name": name,
                "contentType": "audio/wav",
                "size": size,
                "folder": "temp",
            },
        )
        put_file(upload["uploadUrl"], wav_path, "audio/wav")
        return upload["fileUrl"]
    except Exception as exc:
        print(f"Music upload skipped: {exc}")
        return None


def html_for_video():
    return scene_html("THE MOLASSES WAVE", "BOSTON, 1919")


def scene_html(title, caption):
    return f"""
<div class="screen">
  <div class="top">FORGOTTEN HISTORY</div>
  <div class="title">{title}</div>
  <div class="tank">
    <div class="rim"></div>
    <div class="crack"></div>
  </div>
  <div class="wave"></div>
  <div class="map"></div>
  <div class="captionBox">{caption}</div>
  <div class="footer">A REAL DISASTER FEW PEOPLE REMEMBER</div>
</div>
<style>
html, body {{ margin:0; width:1080px; height:1920px; overflow:hidden; background:#050302; }}
.screen {{
  position:relative; width:1080px; height:1920px; overflow:hidden;
  font-family: Impact, Arial Black, Arial, sans-serif; color:#f5efe2;
  background:
    radial-gradient(circle at 50% 55%, rgba(128,74,36,.42), transparent 36%),
    linear-gradient(180deg, #030201 0%, #120806 48%, #030201 100%);
}}
.top {{ position:absolute; top:120px; left:70px; color:#d39a4c; font-size:54px; letter-spacing:3px; }}
.title {{ position:absolute; top:205px; left:70px; width:860px; font-size:102px; line-height:.95; letter-spacing:2px; }}
.tank {{ position:absolute; left:250px; top:540px; width:560px; height:500px; border-radius:46px 46px 16px 16px;
  border:8px solid rgba(214,149,73,.78); background:linear-gradient(90deg, #1b120f, #4c2b1c 50%, #140a08);
  box-shadow:0 0 80px rgba(0,0,0,.9), inset 0 0 80px rgba(0,0,0,.7);
}}
.rim {{ position:absolute; top:38px; left:42px; width:476px; height:72px; border:7px solid rgba(245,210,140,.38); border-radius:50%; }}
.crack {{ position:absolute; left:330px; top:60px; width:12px; height:380px; background:#0a0302;
  clip-path:polygon(40% 0,100% 18%,55% 34%,90% 52%,35% 70%,70% 100%,22% 72%,58% 52%,20% 33%,50% 14%);
  box-shadow:0 0 28px rgba(255,202,107,.25);
}}
.wave {{ position:absolute; left:-170px; top:1050px; width:1420px; height:360px; border-radius:50% 50% 0 0;
  background:linear-gradient(180deg, rgba(37,13,6,.98), rgba(6,2,1,.98));
  box-shadow:0 -25px 60px rgba(120,58,20,.28);
  animation: waveMove 30s ease-in-out both;
}}
.map {{ position:absolute; inset:0; opacity:.17;
  background:
    linear-gradient(28deg, transparent 0 48%, rgba(236,178,90,.7) 49% 50%, transparent 51%),
    linear-gradient(142deg, transparent 0 48%, rgba(236,178,90,.45) 49% 50%, transparent 51%);
  background-size:210px 210px;
}}
.captionBox {{ position:absolute; left:90px; right:90px; top:1140px; height:390px; display:flex; align-items:center; justify-content:center; text-align:center;
  font-size:82px; line-height:1.02; letter-spacing:2px;
  text-shadow:5px 5px 0 #000, 0 0 36px rgba(0,0,0,.85);
}}
.footer {{ position:absolute; bottom:110px; left:70px; right:70px; font:700 34px Arial; color:#d39a4c; letter-spacing:5px; text-align:center; }}
</style>
"""


def build_movie(music_url=None):
    movie_elements = [
        {
            "type": "voice",
            "text": SCRIPT,
            "model": "azure",
            "voice": "en-US-GuyNeural",
            "start": 0.2,
            "volume": 1.1,
            "z-index": 3,
        },
    ]
    if music_url:
        movie_elements.insert(
            0,
            {
                "type": "audio",
                "src": music_url,
                "duration": -2,
                "loop": -1,
                "volume": 0.24,
                "fade-in": 1.2,
                "fade-out": 2.0,
                "z-index": 1,
            },
        )
    scenes = []
    for start, end, caption in CAPTIONS:
        duration = round(end - start, 2)
        scenes.append(
            {
                "duration": duration,
                "elements": [
                    {
                        "type": "html",
                        "html": scene_html("THE MOLASSES WAVE", caption),
                        "duration": -2,
                        "position": "custom",
                        "x": 0,
                        "y": 0,
                        "width": 1080,
                        "height": 1920,
                        "z-index": 0,
                        "cache": False,
                    }
                ],
            }
        )
    return {
        "resolution": "instagram-story",
        "cache": False,
        "elements": movie_elements,
        "scenes": scenes,
    }


def find_url(obj):
    if isinstance(obj, dict):
        for key in ("url", "downloadUrl", "download_url", "movieUrl", "movie_url"):
            value = obj.get(key)
            if isinstance(value, str) and value.startswith("http"):
                return value
        for value in obj.values():
            found = find_url(value)
            if found:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_url(value)
            if found:
                return found
    return None


def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "Codex JSON2Video downloader"})
    with urllib.request.urlopen(req, timeout=120) as res, open(path, "wb") as f:
        f.write(res.read())


def main():
    print("Creating background music...")
    music_url = upload_music()
    print("Submitting render job to JSON2Video...")
    payload = build_movie(music_url)
    payload_path = os.path.join(OUT, "molasses_wave_payload.json")
    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    create = request_json("POST", f"{API_BASE}/movies", payload)
    with open(os.path.join(OUT, "molasses_wave_create_response.json"), "w", encoding="utf-8") as f:
        json.dump(create, f, indent=2)
    project = create.get("project") or create.get("id") or create.get("movie", {}).get("project")
    if not project:
        raise RuntimeError(f"Could not find project id in response: {create}")
    print(f"Project created: {project}")

    movie = None
    for attempt in range(60):
        time.sleep(6)
        status = request_json("GET", f"{API_BASE}/movies?project={urllib.parse.quote(str(project))}")
        movie = status.get("movie", status)
        state = movie.get("status") or movie.get("state") or "unknown"
        print(f"Render status: {state}")
        with open(os.path.join(OUT, "molasses_wave_status_response.json"), "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2)
        if state in ("done", "error", "timeout"):
            break
    if not movie:
        raise RuntimeError("No status response returned")
    if (movie.get("status") or movie.get("state")) != "done":
        raise RuntimeError(f"Render did not finish successfully: {movie}")
    url = find_url(movie)
    if not url:
        raise RuntimeError(f"Could not find movie URL in final response: {movie}")
    out_path = os.path.join(OUT, "molasses_wave_boston_1919_json2video.mp4")
    print("Downloading MP4...")
    download(url, out_path)
    caption_path = os.path.join(OUT, "molasses_wave_caption.txt")
    with open(caption_path, "w", encoding="utf-8") as f:
        f.write("In 1919, Boston was hit by a wave of molasses.\n\n#history #weirdhistory #boston #shorts")
    print(json.dumps({"ok": True, "video": out_path, "caption": caption_path, "project": project}, indent=2))


if __name__ == "__main__":
    main()
