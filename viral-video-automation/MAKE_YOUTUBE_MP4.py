import argparse
import glob
import os
import subprocess
import sys
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont


ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")
READY = os.path.join(ROOT, "ready_videos")
MUSIC = os.path.join(READY, "dark_is_the_night_style_original_prototype.wav")
ASSET_MUSIC = os.path.join(ASSETS, "dark_is_the_night_style_original_prototype.wav")
WIDTH = 1080
HEIGHT = 1920
FPS = 24
FADE_IN = 1.35
HOLD = 10.0
FADE_OUT = 1.75
DURATION = FADE_IN + HOLD + FADE_OUT

QUOTE = os.environ.get(
    "QUOTE_TEXT",
    "If there is no struggle, there is no progress. Those who profess to favor "
    "freedom, and yet depreciate agitation, are men who want crops without "
    "plowing up the ground.",
)
SPEAKER = os.environ.get("QUOTE_SPEAKER", "Frederick Douglass")


def font(size):
    for path in [
        r"C:\Windows\Fonts\georgia.ttf",
        r"C:\Windows\Fonts\times.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
    ]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def cover(img):
    src_ratio = img.width / img.height
    dst_ratio = WIDTH / HEIGHT
    if src_ratio > dst_ratio:
        new_h = HEIGHT
        new_w = int(new_h * src_ratio)
    else:
        new_w = WIDTH
        new_h = int(new_w / src_ratio)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - WIDTH) // 2
    top = (new_h - HEIGHT) // 2
    return img.crop((left, top, left + WIDTH, top + HEIGHT))


def wrap(draw, text, fnt, max_width):
    lines = []
    current = ""
    for word in text.split():
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=fnt)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_centered(draw, lines, y, fnt, fill, line_gap):
    for line in lines:
        box = draw.textbbox((0, 0), line, font=fnt)
        x = (WIDTH - (box[2] - box[0])) // 2
        draw.text((x, y), line, font=fnt, fill=fill)
        y += (box[3] - box[1]) + line_gap
    return y


def make_poster(background, poster):
    img = cover(Image.open(background).convert("RGB")).convert("RGBA")
    img = Image.alpha_composite(img, Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 108)))
    draw = ImageDraw.Draw(img)
    quote_font = font(66)
    speaker_font = font(40)
    lines = wrap(draw, f'"{QUOTE}"', quote_font, 835)
    y = 218
    draw_centered(draw, lines, y, quote_font, (255, 255, 255, 255), 23)

    speaker = f"- {SPEAKER}"
    box = draw.textbbox((0, 0), speaker, font=speaker_font)
    sx = (WIDTH - (box[2] - box[0])) // 2
    draw.text((sx, 1050), speaker, font=speaker_font, fill=(255, 255, 255, 255))
    img.convert("RGB").save(poster, "PNG")


def find_ffmpeg(explicit=None):
    candidates = []
    if explicit:
        candidates.append(explicit)
    try:
        import imageio_ffmpeg

        candidates.append(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        pass
    candidates.extend(glob.glob(os.path.expandvars(r"%APPDATA%\Python\Python*\site-packages\imageio_ffmpeg\binaries\ffmpeg*.exe")))
    candidates.extend(
        [
            os.environ.get("FFMPEG_EXE"),
            r"C:\Users\zivfe\AppData\Roaming\Python\Python312\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe",
        ]
    )
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", "imageio-ffmpeg"], check=True)
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    raise FileNotFoundError("FFmpeg executable was not found")


def encode(ffmpeg, poster, music, out):
    command = [
        ffmpeg,
        "-hide_banner",
        "-y",
        "-loop",
        "1",
        "-framerate",
        str(FPS),
        "-i",
        poster,
        "-i",
        music,
        "-t",
        f"{DURATION:.2f}",
        "-vf",
        f"format=yuv420p,fade=t=in:st=0:d={FADE_IN},fade=t=out:st={FADE_IN + HOLD}:d={FADE_OUT}",
        "-af",
        f"afade=t=in:st=0:d={FADE_IN},afade=t=out:st={FADE_IN + HOLD}:d={FADE_OUT}",
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        "14",
        "-maxrate",
        "24M",
        "-bufsize",
        "48M",
        "-profile:v",
        "high",
        "-level",
        "4.2",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        out,
    ]
    subprocess.run(command, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--background", default=os.path.join(ASSETS, "fresco-background-no-text.png"))
    parser.add_argument("--music", default=ASSET_MUSIC if os.path.exists(ASSET_MUSIC) else MUSIC)
    parser.add_argument("--ffmpeg")
    parser.add_argument("--output")
    args = parser.parse_args()

    if not os.path.exists(args.background):
        raise FileNotFoundError(args.background)
    if not os.path.exists(args.music):
        raise FileNotFoundError(args.music)
    os.makedirs(READY, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    poster = os.path.join(READY, f"youtube_quote_poster_1080_{stamp}.png")
    out = args.output or os.path.join(READY, f"jung_quote_youtube_1080p_{stamp}.mp4")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    make_poster(args.background, poster)
    encode(find_ffmpeg(args.ffmpeg), poster, args.music, out)
    print(out)


if __name__ == "__main__":
    main()
