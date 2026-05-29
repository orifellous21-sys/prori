import argparse
import hashlib
import os
import random
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image, ImageEnhance, ImageFilter


ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")
OUTPUT = os.path.join(ROOT, "output", "daily_quote")
TIME_ZONE = ZoneInfo("Asia/Jerusalem")
DEFAULT_TO = "ori.fellous21@gmail.com"

VISUAL_PROFILES = [
    {
        "name": "warm_gold",
        "tint": (214, 164, 92),
        "tint_strength": 0.045,
        "brightness": (0.98, 1.04),
        "contrast": (0.98, 1.05),
        "color": (1.00, 1.08),
    },
    {
        "name": "muted_blue",
        "tint": (112, 137, 158),
        "tint_strength": 0.040,
        "brightness": (0.97, 1.03),
        "contrast": (0.97, 1.04),
        "color": (0.92, 1.00),
    },
    {
        "name": "soft_olive",
        "tint": (148, 143, 92),
        "tint_strength": 0.035,
        "brightness": (0.98, 1.04),
        "contrast": (0.97, 1.04),
        "color": (0.96, 1.04),
    },
    {
        "name": "subtle_ember",
        "tint": (174, 92, 54),
        "tint_strength": 0.040,
        "brightness": (0.96, 1.02),
        "contrast": (1.00, 1.07),
        "color": (1.00, 1.08),
    },
    {
        "name": "dusty_rose",
        "tint": (164, 112, 118),
        "tint_strength": 0.035,
        "brightness": (0.98, 1.04),
        "contrast": (0.98, 1.05),
        "color": (0.96, 1.05),
    },
    {
        "name": "aged_ivory",
        "tint": (210, 198, 170),
        "tint_strength": 0.030,
        "brightness": (0.99, 1.05),
        "contrast": (0.98, 1.06),
        "color": (0.90, 0.98),
    },
]

QUOTES = [
    {
        "speaker": "Frederick Douglass",
        "text": (
            "If there is no struggle, there is no progress. Those who profess to favor freedom, "
            "and yet depreciate agitation, are men who want crops without plowing up the ground."
        ),
    },
    {
        "speaker": "Marcus Aurelius",
        "text": (
            "You have power over your mind, not outside events. Realize this, and you will find strength."
        ),
    },
    {
        "speaker": "Epictetus",
        "text": (
            "It is impossible for a man to learn what he thinks he already knows."
        ),
    },
    {
        "speaker": "Carl Jung",
        "text": (
            "Until you make the unconscious conscious, it will direct your life and you will call it fate."
        ),
    },
    {
        "speaker": "Friedrich Nietzsche",
        "text": (
            "He who has a why to live can bear almost any how."
        ),
    },
    {
        "speaker": "Maya Angelou",
        "text": (
            "There is no greater agony than bearing an untold story inside you."
        ),
    },
    {
        "speaker": "James Baldwin",
        "text": (
            "Not everything that is faced can be changed, but nothing can be changed until it is faced."
        ),
    },
    {
        "speaker": "Socrates",
        "text": (
            "The unexamined life is not worth living."
        ),
    },
]


def local_now():
    return datetime.now(TIME_ZONE)


def local_date_key(now):
    return now.strftime("%Y-%m-%d")


def choose_quote(date_key):
    digest = hashlib.sha256(date_key.encode("utf-8")).hexdigest()
    return QUOTES[int(digest[:8], 16) % len(QUOTES)]


def choose_visual_profile(date_key):
    digest = hashlib.sha256(f"visual:{date_key}".encode("utf-8")).hexdigest()
    return VISUAL_PROFILES[int(digest[:8], 16) % len(VISUAL_PROFILES)]


def make_background_variant(date_key):
    source = os.path.join(ASSETS, "fresco-background-no-text.png")
    if not os.path.exists(source):
        raise FileNotFoundError(source)

    os.makedirs(OUTPUT, exist_ok=True)
    rng = random.Random(date_key)
    profile = choose_visual_profile(date_key)
    img = Image.open(source).convert("RGB")

    zoom = 1.015 + rng.random() * 0.055
    resized = img.resize((int(img.width * zoom), int(img.height * zoom)), Image.Resampling.LANCZOS)
    max_left = max(0, resized.width - img.width)
    max_top = max(0, resized.height - img.height)
    left = rng.randint(0, max_left) if max_left else 0
    top = rng.randint(0, max_top) if max_top else 0
    img = resized.crop((left, top, left + img.width, top + img.height))

    tint = Image.new("RGB", img.size, profile["tint"])
    img = Image.blend(img, tint, profile["tint_strength"])
    img = ImageEnhance.Contrast(img).enhance(rng.uniform(*profile["contrast"]))
    img = ImageEnhance.Brightness(img).enhance(rng.uniform(*profile["brightness"]))
    img = ImageEnhance.Color(img).enhance(rng.uniform(*profile["color"]))
    if rng.random() > 0.5:
        img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=65, threshold=4))

    path = os.path.join(OUTPUT, f"background_{date_key}.png")
    img.save(path, "PNG")
    return path, profile["name"]


def run(command, env):
    subprocess.run(command, check=True, env=env)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", default=os.environ.get("DAILY_QUOTE_TO_EMAIL", DEFAULT_TO))
    parser.add_argument("--force-send", action="store_true", default=os.environ.get("FORCE_SEND") == "1")
    args = parser.parse_args()

    now = local_now()
    if not args.force_send and now.hour < 16:
        print(f"Skipping: it is {now:%H:%M} in Asia/Jerusalem, before the 16:00 send window.")
        return

    date_key = local_date_key(now)
    state_path = os.path.join(ROOT, "youtube_uploads", f"{date_key}.json")
    if not args.force_send and os.path.exists(state_path):
        print(f"Skipping: YouTube upload state already exists for {date_key}.")
        return

    quote = choose_quote(date_key)
    background, visual_profile = make_background_variant(date_key)
    output_path = os.path.join(OUTPUT, f"daily_quote_youtube_{date_key}.mp4")

    env = os.environ.copy()
    env["QUOTE_TEXT"] = quote["text"]
    env["QUOTE_SPEAKER"] = quote["speaker"]
    env["VIDEO_VISUAL_PROFILE"] = visual_profile
    run(
        [
            sys.executable,
            os.path.join(ROOT, "MAKE_YOUTUBE_MP4.py"),
            "--background",
            background,
            "--output",
            output_path,
        ],
        env,
    )

    body = (
        "Daily quote video attached.\n\n"
        f"Date: {date_key}\n"
        f"Quote: {quote['text']}\n"
        f"Speaker: {quote['speaker']}\n\n"
        "Format: YouTube-ready MP4, 1080x1920, H.264 video, AAC audio, 13.1 seconds."
    )
    env["RESEND_IDEMPOTENCY_KEY"] = f"daily-quote-video:{date_key}"
    run(
        [
            sys.executable,
            os.path.join(ROOT, "SEND_WITH_RESEND.py"),
            "--to",
            args.to,
            "--subject",
            f"Daily quote video - {date_key}",
            "--body",
            body,
            "--attachment",
            output_path,
        ],
        env,
    )

    print(output_path)


if __name__ == "__main__":
    main()
