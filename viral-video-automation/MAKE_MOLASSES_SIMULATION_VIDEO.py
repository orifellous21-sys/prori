import json
import math
import os
import shutil
import struct
import subprocess
import wave
from datetime import datetime
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "output", "molasses_simulation")
TEMP = os.path.join(ROOT, "output", "molasses_simulation_temp")
os.makedirs(OUT, exist_ok=True)
os.makedirs(TEMP, exist_ok=True)

WIDTH = 1080
HEIGHT = 1920
FPS = 30
SAMPLE_RATE = 44100
DURATION = 31.0

SCRIPT = (
    "Boston, 1919. A giant tank holding more than two million gallons of molasses suddenly split open. "
    "Witnesses heard a roar like a train. Then a dark wave rushed through the street, smashing buildings and lifting debris. "
    "People ran, but the syrup was too heavy and too fast. This was not a myth. It was one of America's strangest disasters."
)

CAPTIONS = [
    (0.4, 3.2, "BOSTON, 1919"),
    (3.2, 6.5, "A GIANT MOLASSES TANK SPLIT OPEN"),
    (6.5, 9.8, "WITNESSES HEARD A ROAR LIKE A TRAIN"),
    (9.8, 14.2, "A DARK WAVE RUSHED THROUGH THE STREET"),
    (14.2, 18.4, "BUILDINGS CRACKED. DEBRIS MOVED."),
    (18.4, 23.4, "PEOPLE RAN, BUT THE SYRUP WAS TOO HEAVY"),
    (23.4, 28.4, "THIS WAS REAL HISTORY"),
    (28.4, 31.0, "THE GREAT MOLASSES FLOOD"),
]


def ffmpeg_path():
    local = os.environ.get("LOCALAPPDATA", "")
    candidate = os.path.join(
        local,
        "Microsoft",
        "WinGet",
        "Packages",
        "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
        "ffmpeg-8.1.1-full_build",
        "bin",
        "ffmpeg.exe",
    )
    if os.path.exists(candidate):
        return candidate
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise RuntimeError("ffmpeg was not found")


def font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/impact.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


FONT_TOP = font(44, True)
FONT_CAPTION = font(72, True)
FONT_SMALL = font(30, True)


def run_tts(text, wav_path):
    if os.path.exists(wav_path):
        os.remove(wav_path)
    ps_path = os.path.join(TEMP, "molasses_tts.ps1")
    txt_path = os.path.join(TEMP, "molasses_script.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    with open(ps_path, "w", encoding="utf-8") as f:
        f.write(
            "param([string]$InputTextPath,[string]$OutputWavPath)\n"
            "$text = Get-Content -Raw -LiteralPath $InputTextPath\n"
            "$voice = New-Object -ComObject SAPI.SpVoice\n"
            "$preferred = @($voice.GetVoices()) | Where-Object { $_.GetDescription() -match 'David|Mark|Guy' } | Select-Object -First 1\n"
            "if ($preferred) { $voice.Voice = $preferred }\n"
            "$voice.Rate = -1\n"
            "$voice.Volume = 100\n"
            "$stream = New-Object -ComObject SAPI.SpFileStream\n"
            "$stream.Open($OutputWavPath, 3)\n"
            "$voice.AudioOutputStream = $stream\n"
            "$voice.Speak($text) | Out-Null\n"
            "$stream.Close()\n"
        )
    powershell = os.path.join(os.environ.get("SystemRoot", "C:/Windows"), "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
    subprocess.run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_path, "-InputTextPath", txt_path, "-OutputWavPath", wav_path],
        check=True,
        capture_output=True,
        text=True,
    )
    if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 1000:
        raise RuntimeError("Windows text-to-speech created an empty voice file")


def read_wav_mono(path):
    with wave.open(path, "rb") as w:
        channels = w.getnchannels()
        rate = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    if rate != SAMPLE_RATE:
        old_x = np.linspace(0, 1, len(data))
        new_len = int(len(data) * SAMPLE_RATE / rate)
        data = np.interp(np.linspace(0, 1, new_len), old_x, data).astype(np.float32)
    return data


def make_music(seconds):
    n = int(seconds * SAMPLE_RATE)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    drone = 0.24 * np.sin(2 * np.pi * 46.25 * t)
    pressure = 0.16 * np.sin(2 * np.pi * 58.27 * t) * (0.4 + 0.6 * np.sin(2 * np.pi * 0.42 * t) ** 2)
    pulse = 0.14 * np.sin(2 * np.pi * 92.5 * t) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 1.35 * t)))
    rumble = np.random.default_rng(1919).normal(0, 0.06, n).astype(np.float32)
    rumble = np.convolve(rumble, np.ones(480) / 480, mode="same")
    hits = np.zeros_like(t)
    for beat in [0.0, 3.3, 6.5, 9.8, 14.2, 18.4, 23.4, 28.4]:
        start = int(beat * SAMPLE_RATE)
        length = min(int(0.36 * SAMPLE_RATE), n - start)
        if length > 0:
            env = np.exp(-np.linspace(0, 6.0, length))
            tt = np.arange(length, dtype=np.float32) / SAMPLE_RATE
            hits[start:start + length] += 0.58 * env * np.sin(2 * np.pi * 72 * tt)
    fade = np.minimum(1, t / 1.2) * np.minimum(1, (seconds - t) / 1.6)
    return (drone + pressure + pulse + rumble + hits) * fade * 0.38


def mix_audio(voice_path, seconds):
    total = int(seconds * SAMPLE_RATE)
    audio = make_music(seconds)
    voice = read_wav_mono(voice_path)
    start = int(0.35 * SAMPLE_RATE)
    end = min(total, start + len(voice))
    duck = np.ones(total, dtype=np.float32)
    duck[start:end] = 0.38
    audio *= duck
    audio[start:end] += voice[: end - start] * 1.05
    peak = float(np.max(np.abs(audio))) or 1.0
    if peak > 0.96:
        audio = audio / peak * 0.96
    return audio


def write_wav(path, audio):
    pcm = (np.clip(audio, -0.96, 0.96) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
    return pcm.tobytes()


def active_caption(t):
    for start, end, text in CAPTIONS:
        if start <= t < end:
            return text
    return ""


def draw_wrapped_center(draw, text, y, max_width=880):
    words = text.split()
    lines = []
    line = ""
    for word in words:
        test = (line + " " + word).strip()
        if draw.textbbox((0, 0), test, font=FONT_CAPTION)[2] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    heights = [draw.textbbox((0, 0), line, font=FONT_CAPTION)[3] for line in lines]
    cursor = y - (sum(heights) + 14 * (len(lines) - 1)) // 2
    for line, h in zip(lines, heights):
        box = draw.textbbox((0, 0), line, font=FONT_CAPTION)
        x = (WIDTH - (box[2] - box[0])) // 2
        for dx, dy in ((5, 5), (-3, 3), (3, -3)):
            draw.text((x + dx, cursor + dy), line, font=FONT_CAPTION, fill=(0, 0, 0))
        draw.text((x, cursor), line, font=FONT_CAPTION, fill=(250, 241, 224))
        cursor += h + 14


def draw_person(draw, x, y, scale=1.0, phase=0.0, fill=(22, 16, 12)):
    r = int(12 * scale)
    draw.ellipse((x - r, y - int(58 * scale), x + r, y - int(34 * scale)), fill=fill)
    draw.line((x, y - int(34 * scale), x - int(8 * scale), y + int(12 * scale)), fill=fill, width=max(3, int(7 * scale)))
    leg = math.sin(phase) * 18 * scale
    draw.line((x - int(8 * scale), y + int(10 * scale), x - int(32 * scale + leg), y + int(52 * scale)), fill=fill, width=max(3, int(7 * scale)))
    draw.line((x - int(8 * scale), y + int(10 * scale), x + int(22 * scale - leg), y + int(50 * scale)), fill=fill, width=max(3, int(7 * scale)))
    draw.line((x - int(3 * scale), y - int(18 * scale), x + int(34 * scale), y - int(38 * scale)), fill=fill, width=max(3, int(6 * scale)))


def draw_frame(index, total):
    t = index / FPS
    progress = t / DURATION
    img = Image.new("RGB", (WIDTH, HEIGHT), (8, 6, 5))
    draw = ImageDraw.Draw(img)

    for y in range(HEIGHT):
        shade = int(10 + 26 * (y / HEIGHT))
        draw.line((0, y, WIDTH, y), fill=(shade, max(5, shade - 9), max(4, shade - 14)))

    sun = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sun)
    sd.ellipse((210, 190, 900, 880), fill=(120, 71, 28, 38))
    img = Image.alpha_composite(img.convert("RGBA"), sun).convert("RGB")
    draw = ImageDraw.Draw(img)

    horizon = 770
    street_top = 820
    street_bottom = 1500
    draw.polygon([(0, street_top), (WIDTH, street_top), (WIDTH, street_bottom), (0, street_bottom)], fill=(42, 35, 31))
    for k in range(8):
        y = street_top + k * 85
        draw.line((0, y, WIDTH, y + 55), fill=(62, 52, 44), width=3)

    # Industrial buildings.
    for x, w, h, color in [
        (40, 210, 410, (43, 35, 30)),
        (260, 170, 315, (55, 42, 34)),
        (715, 270, 360, (40, 34, 31)),
        (840, 190, 480, (48, 37, 31)),
    ]:
        draw.rectangle((x, horizon - h, x + w, horizon), fill=color)
        for wx in range(x + 28, x + w - 20, 52):
            for wy in range(horizon - h + 42, horizon - 35, 80):
                lit = (157, 111, 61) if (wx + wy + index) % 3 == 0 else (18, 16, 15)
                draw.rectangle((wx, wy, wx + 26, wy + 34), fill=lit)

    # Tank rupture.
    tank_x = 452
    tank_y = 260
    tank_w = 310
    tank_h = 575
    shake = int(7 * math.sin(t * 28)) if 4.2 < t < 8.8 else 0
    draw.rounded_rectangle((tank_x + shake, tank_y, tank_x + tank_w + shake, tank_y + tank_h), radius=26, fill=(68, 38, 22), outline=(198, 130, 61), width=8)
    draw.ellipse((tank_x + 20 + shake, tank_y + 38, tank_x + tank_w - 20 + shake, tank_y + 105), outline=(220, 161, 83), width=5)
    crack_open = max(0.0, min(1.0, (t - 4.0) / 3.0))
    crack = [
        (tank_x + 185 + shake, tank_y + 90),
        (tank_x + 214 + shake, tank_y + 175),
        (tank_x + 176 + shake, tank_y + 270),
        (tank_x + 230 + shake, tank_y + 360),
        (tank_x + 196 + shake, tank_y + 505),
    ]
    draw.line(crack, fill=(6, 2, 1), width=6 + int(11 * crack_open))
    if crack_open > 0.1:
        draw.polygon(
            [
                (tank_x + 174, tank_y + 205),
                (tank_x + 238 + int(55 * crack_open), tank_y + 265),
                (tank_x + 210, tank_y + 420),
                (tank_x + 164, tank_y + 350),
            ],
            fill=(24, 8, 3),
        )

    # Molasses wave grows and moves across the street.
    wave_phase = max(0.0, min(1.0, (t - 6.0) / 14.0))
    wave_front = -260 + wave_phase * 1380
    wave_height = 120 + 360 * min(1.0, wave_phase * 1.4)
    wave = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    wd = ImageDraw.Draw(wave)
    points = [(0, street_bottom), (0, street_bottom - 40)]
    for x in range(-80, WIDTH + 160, 40):
        dist = max(0, 1 - abs(x - wave_front) / 510)
        crest = street_bottom - 60 - wave_height * dist - 34 * math.sin((x * 0.025) + t * 5)
        points.append((x, int(crest)))
    points += [(WIDTH, street_bottom), (0, street_bottom)]
    wd.polygon(points, fill=(32, 10, 4, 235))
    wd.line([(max(0, wave_front - 70), int(street_bottom - wave_height - 70)), (min(WIDTH, wave_front + 80), int(street_bottom - wave_height + 10))], fill=(116, 58, 28, 190), width=16)
    for x in range(0, WIDTH, 85):
        if x < wave_front + 130:
            y = street_bottom - 90 - 70 * math.sin(t * 1.3 + x)
            wd.ellipse((x, y, x + 70, y + 24), fill=(61, 24, 10, 155))
    img = Image.alpha_composite(img.convert("RGBA"), wave).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Running silhouettes and debris.
    for n, base in enumerate([980, 1120, 1245, 1350]):
        run_start = 8.0 + n * 1.1
        x = 960 - max(0, t - run_start) * (145 + 20 * n)
        y = base - n * 70
        if -60 < x < WIDTH + 80 and t > 7.2:
            draw_person(draw, int(x), int(y), 1.0 - n * 0.08, t * 10 + n, fill=(16, 11, 8))
    for n in range(14):
        dstart = 10.0 + n * 0.45
        if t > dstart:
            x = (180 + n * 73 + int((t - dstart) * (80 + n * 8))) % (WIDTH + 120) - 60
            y = int(910 + (n * 41) % 410 + 35 * math.sin(t * 2 + n))
            angle = t * 4 + n
            draw.rectangle((x, y, x + 34 + n % 3 * 15, y + 18), fill=(86, 58, 38))
            draw.line((x, y, x + 28 * math.sin(angle), y - 18 * math.cos(angle)), fill=(128, 92, 57), width=4)

    # Impact cracks and dust.
    if 13.0 < t < 22.0:
        dust = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        dd = ImageDraw.Draw(dust)
        alpha = int(95 * min(1.0, (t - 13) / 3) * min(1.0, (22 - t) / 3))
        for n in range(25):
            x = int((n * 97 + t * 25) % WIDTH)
            y = int(665 + (n * 53) % 390)
            r = 22 + (n * 7) % 55
            dd.ellipse((x - r, y - r, x + r, y + r), fill=(153, 116, 78, alpha // 3))
        img = Image.alpha_composite(img.convert("RGBA"), dust).convert("RGB")
        draw = ImageDraw.Draw(img)
        draw.line((755, 540, 700, 620, 760, 710, 720, 770), fill=(8, 5, 4), width=8)

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0, 0, WIDTH, 245), fill=(0, 0, 0, 178))
    od.rectangle((0, 1450, WIDTH, HEIGHT), fill=(0, 0, 0, 205))
    od.rectangle((0, 0, 28, HEIGHT), fill=(0, 0, 0, 230))
    od.rectangle((WIDTH - 28, 0, WIDTH, HEIGHT), fill=(0, 0, 0, 230))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    draw.text((58, 78), "FORGOTTEN HISTORY", font=FONT_TOP, fill=(226, 167, 83))
    draw.text((58, 154), "A DISASTER THAT LOOKED IMPOSSIBLE", font=FONT_SMALL, fill=(235, 218, 187))
    caption = active_caption(t)
    if caption:
        draw_wrapped_center(draw, caption, 1615)
    bar_w = int((WIDTH - 116) * progress)
    draw.rounded_rectangle((58, 1815, WIDTH - 58, 1830), radius=7, fill=(69, 59, 49))
    draw.rounded_rectangle((58, 1815, 58 + bar_w, 1830), radius=7, fill=(226, 167, 83))

    return img.filter(ImageFilter.GaussianBlur(0.08))


def jpeg_bytes(img):
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=88, optimize=True)
    return buf.getvalue()


def riff_chunk(fourcc, data):
    return fourcc + struct.pack("<I", len(data)) + data + (b"\0" if len(data) % 2 else b"")


def list_chunk(kind, data):
    return b"LIST" + struct.pack("<I", len(data) + 4) + kind + data


def write_avi(path, frames, pcm_audio):
    audio_block_align = 2
    audio_avg = SAMPLE_RATE * audio_block_align
    video_max = max(len(f) for f in frames)
    total_frames = len(frames)
    avih = struct.pack("<IIIIIIIIII4I", int(1_000_000 / FPS), 0, 0, 0x10, total_frames, 0, 2, max(video_max, 8192), WIDTH, HEIGHT, 0, 0, 0, 0)
    v_strh = struct.pack("<4s4sIHHIIIIIIIIhhhh", b"vids", b"MJPG", 0, 0, 0, 0, 1, FPS, 0, total_frames, video_max, 0xFFFFFFFF, 0, 0, 0, WIDTH, HEIGHT)
    v_strf = struct.pack("<IiiHH4sIiiII", 40, WIDTH, HEIGHT, 1, 24, b"MJPG", WIDTH * HEIGHT * 3, 0, 0, 0, 0)
    a_strh = struct.pack("<4s4sIHHIIIIIIIIhhhh", b"auds", b"\0\0\0\0", 0, 0, 0, 0, audio_block_align, audio_avg, 0, len(pcm_audio) // audio_block_align, 8192, 0xFFFFFFFF, audio_block_align, 0, 0, 0, 0)
    a_strf = struct.pack("<HHIIHH", 1, 1, SAMPLE_RATE, audio_avg, audio_block_align, 16)
    hdrl = list_chunk(b"hdrl", riff_chunk(b"avih", avih) + list_chunk(b"strl", riff_chunk(b"strh", v_strh) + riff_chunk(b"strf", v_strf)) + list_chunk(b"strl", riff_chunk(b"strh", a_strh) + riff_chunk(b"strf", a_strf)))
    movi_data = bytearray()
    index = []
    audio_pos = 0
    audio_per_frame = int(SAMPLE_RATE / FPS) * audio_block_align
    for frame in frames:
        off = len(movi_data) + 4
        movi_data.extend(riff_chunk(b"00dc", frame))
        index.append((b"00dc", 0x10, off, len(frame)))
        aud = pcm_audio[audio_pos: audio_pos + audio_per_frame]
        audio_pos += len(aud)
        if aud:
            off = len(movi_data) + 4
            movi_data.extend(riff_chunk(b"01wb", aud))
            index.append((b"01wb", 0, off, len(aud)))
    movi = list_chunk(b"movi", bytes(movi_data))
    idx1 = riff_chunk(b"idx1", b"".join(struct.pack("<4sIII", *entry) for entry in index))
    body = hdrl + movi + idx1
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", len(body) + 4) + b"AVI " + body)


def convert_to_mp4(avi_path, mp4_path):
    subprocess.run(
        [
            ffmpeg_path(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            avi_path,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            mp4_path,
        ],
        check=True,
    )


def render_mp4_stream(mp4_path, audio_path, preview_path):
    command = [
        ffmpeg_path(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{WIDTH}x{HEIGHT}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-i",
        audio_path,
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        mp4_path,
    ]
    proc = subprocess.Popen(command, stdin=subprocess.PIPE)
    total = int(DURATION * FPS)
    try:
        for i in range(total):
            frame = draw_frame(i, total)
            if i == int(12 * FPS):
                frame.save(preview_path, quality=92)
            proc.stdin.write(frame.tobytes())
            if i % 90 == 0:
                print(f"Rendered frame {i}/{total}", flush=True)
        proc.stdin.close()
        return_code = proc.wait()
    finally:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
    if return_code != 0:
        raise RuntimeError(f"ffmpeg failed with exit code {return_code}")


def main():
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    voice_path = os.path.join(TEMP, "molasses_voice.wav")
    audio_path = os.path.join(TEMP, "molasses_audio.wav")
    avi_path = os.path.join(TEMP, "molasses_simulation.avi")
    mp4_path = os.path.join(OUT, "molasses_event_simulation.mp4")
    preview_path = os.path.join(OUT, "molasses_event_simulation_preview.jpg")
    caption_path = os.path.join(OUT, "molasses_event_caption.txt")
    details_path = os.path.join(OUT, "molasses_event_details.json")

    print("Creating narrator voice...", flush=True)
    run_tts(SCRIPT, voice_path)
    print("Creating cinematic music and sound bed...", flush=True)
    write_wav(audio_path, mix_audio(voice_path, DURATION))
    print("Rendering animated event simulation MP4...", flush=True)
    render_mp4_stream(mp4_path, audio_path, preview_path)

    with open(caption_path, "w", encoding="utf-8") as f:
        f.write("In 1919, Boston was hit by a wave of molasses. This is the strange true story.\n\n#history #weirdhistory #boston #shorts")
    with open(details_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "createdAt": datetime.now().isoformat(),
                "video": mp4_path,
                "preview": preview_path,
                "caption": caption_path,
                "duration": DURATION,
                "format": "1080x1920 vertical MP4",
                "note": "Animated event simulation: tank rupture, molasses wave, fleeing silhouettes, debris, captions, narrator, and music.",
            },
            f,
            indent=2,
        )
    archived = os.path.join(OUT, f"molasses_event_simulation_{stamp}.mp4")
    shutil.copy2(mp4_path, archived)
    print(json.dumps({"ok": True, "video": mp4_path, "preview": preview_path, "caption": caption_path, "archive": archived}, indent=2))


if __name__ == "__main__":
    main()
