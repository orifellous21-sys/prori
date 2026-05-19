import os
from PIL import Image, ImageDraw, ImageFont


ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")
BACKGROUND = os.environ.get("FRESCO_BACKGROUND") or os.path.join(ASSETS, "fresco-background-no-text.png")
OUT = os.path.join(ASSETS, "jung-fresco-quote-poster.png")
WIDTH = 720
HEIGHT = 1280

QUOTE = os.environ.get(
    "QUOTE_TEXT",
    "If there is no struggle, there is no progress. Those who profess to favor "
    "freedom, and yet depreciate agitation, are men who want crops without "
    "plowing up the ground.",
)
SPEAKER = os.environ.get("QUOTE_SPEAKER", "Frederick Douglass")


def font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\georgiab.ttf" if bold else r"C:\Windows\Fonts\georgia.ttf",
        r"C:\Windows\Fonts\timesbd.ttf" if bold else r"C:\Windows\Fonts\times.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
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


def main():
    if not os.path.exists(BACKGROUND):
        raise FileNotFoundError(BACKGROUND)

    img = cover(Image.open(BACKGROUND).convert("RGB")).convert("RGBA")
    shade = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 108))
    img = Image.alpha_composite(img, shade)

    draw = ImageDraw.Draw(img)
    quote_font = font(44)
    speaker_font = font(27)
    lines = wrap(draw, f'"{QUOTE}"', quote_font, 555)

    line_heights = [draw.textbbox((0, 0), line, font=quote_font)[3] for line in lines]
    total_h = sum(line_heights) + (len(lines) - 1) * 15
    y = 145 if total_h < 500 else 125
    draw_centered(draw, lines, y, quote_font, (255, 255, 255, 255), 15)

    speaker = f"- {SPEAKER}"
    box = draw.textbbox((0, 0), speaker, font=speaker_font)
    sx = (WIDTH - (box[2] - box[0])) // 2
    sy = 700
    draw.text((sx, sy), speaker, font=speaker_font, fill=(255, 255, 255, 255))

    os.makedirs(ASSETS, exist_ok=True)
    img.convert("RGB").save(OUT, "PNG")
    print(OUT)


if __name__ == "__main__":
    main()
