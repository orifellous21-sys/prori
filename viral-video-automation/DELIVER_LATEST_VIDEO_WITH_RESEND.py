import argparse
import glob
import os
import subprocess
import sys
from datetime import datetime


ROOT = os.path.dirname(os.path.abspath(__file__))
READY = os.path.join(ROOT, "ready_videos")


def latest_avi():
    files = glob.glob(os.path.join(READY, "jung_quote_fade_music_*.avi"))
    if not files:
        raise FileNotFoundError("No rendered quote AVI found in ready_videos.")
    return max(files, key=os.path.getmtime)


def run(args):
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quote", default=os.environ.get("QUOTE_TEXT", "Daily quote video"))
    parser.add_argument("--speaker", default=os.environ.get("QUOTE_SPEAKER", ""))
    parser.add_argument("--to", default="ori.fellous21@gmail.com")
    args = parser.parse_args()

    avi = latest_avi()
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    mp4 = os.path.join(READY, f"daily_quote_delivery_{stamp}.mp4")

    run([sys.executable, os.path.join(ROOT, "MAKE_EMAIL_MP4.py"), avi, mp4])

    body = (
        "Daily quote video attached.\n\n"
        f"Quote:\n{args.quote}\n\n"
        f"Speaker:\n{args.speaker or 'Unknown'}\n\n"
        f"Attached video file:\n{os.path.basename(mp4)}\n"
    )
    run([
        sys.executable,
        os.path.join(ROOT, "SEND_WITH_RESEND.py"),
        "--to",
        args.to,
        "--subject",
        "Daily quote video",
        "--body",
        body,
        "--attachment",
        mp4,
    ])
    print(mp4)


if __name__ == "__main__":
    main()
