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
OUT = os.path.join(ROOT, "output", "prototypes")
TEMP = os.path.join(ROOT, "output", "prototype_temp")
os.makedirs(OUT, exist_ok=True)
os.makedirs(TEMP, exist_ok=True)

WIDTH = 720
HEIGHT = 1280
FPS = 30
SAMPLE_RATE = 44100

PROTOTYPES = [
    {
        "slug": "ai_history",
        "title": "AI HISTORY MINI-STORY",
        "caption": "The empire did not fall in one day.",
        "script": "The empire did not fall in one day. First, the money weakened. Then the army stopped believing. Then one betrayal opened the gate. History usually ends quietly before the world notices.",
        "hashtags": "#history #empire #shorts #story",
        "palette": ((18, 12, 8), (208, 148, 62), (232, 214, 178)),
    },
    {
        "slug": "luxury_money",
        "title": "MONEY MINDSET LOOP",
        "caption": "Poor people buy to impress.",
        "script": "Poor people buy to impress. Rich people buy to control time. The difference is not the car, the watch, or the view. It is whether the money is buying attention, or buying freedom.",
        "hashtags": "#money #luxury #mindset #shorts",
        "palette": ((5, 8, 13), (220, 183, 89), (236, 238, 230)),
    },
    {
        "slug": "mystery_fact",
        "title": "THIS SHOULD NOT EXIST",
        "caption": "This place should not exist.",
        "script": "This place should not exist. The stones are too heavy. The cuts are too clean. And the oldest story about it says nobody built it. They found it already waiting.",
        "hashtags": "#mystery #ancient #facts #shorts",
        "palette": ((7, 10, 14), (69, 196, 177), (230, 235, 225)),
    },
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


FONT_TITLE = font(38, True)
FONT_TEXT = font(56, True)
FONT_SMALL = font(26, False)


def run_tts(text, wav_path):
    if os.path.exists(wav_path):
        os.remove(wav_path)
    ps_path = os.path.join(TEMP, "prototype_tts.ps1")
    txt_path = os.path.join(TEMP, "prototype_script.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    with open(ps_path, "w", encoding="utf-8") as f:
        f.write(
            "param([string]$InputTextPath,[string]$OutputWavPath)\n"
            "$text = Get-Content -Raw -LiteralPath $InputTextPath\n"
            "$voice = New-Object -ComObject SAPI.SpVoice\n"
            "$preferred = @($voice.GetVoices()) | Where-Object { $_.GetDescription() -match 'David' } | Select-Object -First 1\n"
            "if ($preferred) { $voice.Voice = $preferred }\n"
            "$stream = New-Object -ComObject SAPI.SpFileStream\n"
            "$stream.Open($OutputWavPath, 3)\n"
            "$voice.AudioOutputStream = $stream\n"
            "$voice.Rate = 0\n"
            "$voice.Volume = 100\n"
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
    if len(data) == 0:
        raise RuntimeError("Voice file has no audio samples")
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    if rate != SAMPLE_RATE:
        old_x = np.linspace(0, 1, len(data))
        new_len = int(len(data) * SAMPLE_RATE / rate)
        new_x = np.linspace(0, 1, new_len)
        data = np.interp(new_x, old_x, data).astype(np.float32)
    return data


def make_music(seconds, kind):
    n = int(seconds * SAMPLE_RATE)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    if kind == "ai_history":
        base = 0.22 * np.sin(2 * np.pi * 55 * t) + 0.14 * np.sin(2 * np.pi * 82.4 * t)
        pulse = 0.16 * np.sin(2 * np.pi * 110 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.7 * t))
    elif kind == "luxury_money":
        base = 0.20 * np.sin(2 * np.pi * 65.4 * t) + 0.12 * np.sin(2 * np.pi * 196 * t)
        pulse = 0.18 * np.sin(2 * np.pi * 130.8 * t) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 1.6 * t)))
    else:
        base = 0.24 * np.sin(2 * np.pi * 46.2 * t) + 0.10 * np.sin(2 * np.pi * 185 * t)
        pulse = 0.10 * np.sin(2 * np.pi * 370 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.35 * t))
    hits = np.zeros_like(t)
    for beat in np.arange(0, seconds, 1.5):
        pos = int(beat * SAMPLE_RATE)
        length = min(int(0.18 * SAMPLE_RATE), len(hits) - pos)
        if length > 0:
            env = np.exp(-np.linspace(0, 5.5, length))
            tt = np.arange(length, dtype=np.float32) / SAMPLE_RATE
            hits[pos:pos + length] += 0.35 * env * np.sin(2 * np.pi * 74 * tt)
    fade = np.minimum(1, t / 1.2) * np.minimum(1, (seconds - t) / 1.4)
    return (base + pulse + hits) * fade * 0.34


def mix_audio(tts_path, seconds, kind):
    voice = read_wav_mono(tts_path)
    total = int(seconds * SAMPLE_RATE)
    audio = make_music(seconds, kind)
    if len(audio) < total:
        audio = np.pad(audio, (0, total - len(audio)))
    start = int(0.8 * SAMPLE_RATE)
    end = min(total, start + len(voice))
    if end > start:
        duck = np.ones(total, dtype=np.float32)
        duck[start:end] = 0.48
        audio *= duck
        audio[start:end] += voice[:end - start] * 1.0
    peak = np.max(np.abs(audio)) if len(audio) else 1
    if peak > 0.95:
        audio = audio / peak * 0.95
    return audio


def write_wav(path, audio):
    pcm = (np.clip(audio, -0.95, 0.95) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
    return pcm.tobytes()


def chunks_for(script, seconds):
    sentences = [s.strip() for s in script.replace("?", ".").replace("!", ".").split(".") if s.strip()]
    chunks = []
    cursor = 0.8
    usable = seconds - 1.4
    for sentence in sentences:
        words = sentence.split()
        for i in range(0, len(words), 4):
            chunks.append(" ".join(words[i:i + 4]).upper())
    step = usable / max(1, len(chunks))
    return [(cursor + i * step, cursor + (i + 1) * step, text) for i, text in enumerate(chunks)]


def draw_center(draw, text, y, fill):
    lines = []
    words = text.split()
    line = ""
    for word in words:
        test = (line + " " + word).strip()
        if draw.textbbox((0, 0), test, font=FONT_TEXT)[2] < 610:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    heights = [draw.textbbox((0, 0), line, font=FONT_TEXT)[3] for line in lines]
    cursor = y - (sum(heights) + 12 * (len(lines) - 1)) // 2
    for line, h in zip(lines, heights):
        box = draw.textbbox((0, 0), line, font=FONT_TEXT)
        x = (WIDTH - (box[2] - box[0])) // 2
        for dx, dy in ((4, 4), (-2, 2), (2, -2)):
            draw.text((x + dx, cursor + dy), line, font=FONT_TEXT, fill=(0, 0, 0))
        draw.text((x, cursor), line, font=FONT_TEXT, fill=fill)
        cursor += h + 12


def active_caption(t, chunks):
    for start, end, text in chunks:
        if start <= t < end:
            return text
    return ""


def frame_for(item, i, total, seconds, chunks):
    bg, accent, text_color = item["palette"]
    img = Image.new("RGB", (WIDTH, HEIGHT), bg)
    draw = ImageDraw.Draw(img)
    t = i / FPS

    if item["slug"] == "ai_history":
        for x in range(-80, WIDTH, 120):
            draw.line((x + int(t * 10) % 120, 300, x + 260, 960), fill=(64, 43, 25), width=3)
        draw.ellipse((90, 420, 630, 910), outline=(125, 79, 39), width=6)
        draw.line((160, 780, 560, 520), fill=accent, width=8)
        draw.polygon([(548, 520), (518, 506), (528, 544)], fill=accent)
        draw.rectangle((105, 910, 615, 985), fill=(35, 22, 13))
        draw.text((145, 930), "EMPIRE MAP", font=FONT_SMALL, fill=accent)
    elif item["slug"] == "luxury_money":
        for n, x in enumerate(range(40, WIDTH, 86)):
            h = 230 + ((n * 47) % 260)
            draw.rectangle((x, 880 - h, x + 48, 880), fill=(22, 31, 42))
            draw.rectangle((x + 8, 880 - h + 30, x + 16, 870), fill=(58, 64, 74))
        draw.line((60, 890, 660, 620), fill=accent, width=9)
        draw.ellipse((250, 520, 470, 740), outline=accent, width=10)
        draw.text((305, 584), "$", font=font(96, True), fill=accent)
        draw.rounded_rectangle((120, 940, 600, 1035), radius=28, outline=accent, width=5)
    else:
        for r in range(90, 440, 70):
            draw.ellipse((WIDTH // 2 - r, 640 - r, WIDTH // 2 + r, 640 + r), outline=(18, 70, 66), width=3)
        draw.polygon([(360, 345), (520, 875), (200, 875)], outline=accent, fill=(10, 28, 30))
        draw.ellipse((278, 570, 442, 734), outline=accent, width=7)
        draw.ellipse((335, 625, 385, 675), fill=accent)
        draw.text((180, 910), "UNKNOWN ORIGIN", font=FONT_SMALL, fill=accent)

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0, 0, WIDTH, 290), fill=(0, 0, 0, 180))
    od.rectangle((0, 970, WIDTH, HEIGHT), fill=(0, 0, 0, 210))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.text((48, 70), item["title"], font=FONT_TITLE, fill=accent)
    caption = active_caption(t, chunks)
    if caption:
        draw_center(draw, caption, 1048, text_color)
    progress = int((i + 1) / total * (WIDTH - 96))
    draw.rounded_rectangle((48, 1210, WIDTH - 48, 1222), radius=6, fill=(62, 58, 55))
    draw.rounded_rectangle((48, 1210, 48 + progress, 1222), radius=6, fill=accent)
    return img.filter(ImageFilter.GaussianBlur(0.0))


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
        aud = pcm_audio[audio_pos:audio_pos + audio_per_frame]
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
        [ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-y", "-i", avi_path, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", mp4_path],
        check=True,
    )


def make_one(item):
    print(f"Creating {item['title']}...")
    voice_path = os.path.join(TEMP, f"{item['slug']}_voice.wav")
    audio_path = os.path.join(TEMP, f"{item['slug']}_audio.wav")
    avi_path = os.path.join(TEMP, f"{item['slug']}.avi")
    mp4_path = os.path.join(OUT, f"{item['slug']}_prototype.mp4")
    run_tts(item["script"], voice_path)
    voice_seconds = len(read_wav_mono(voice_path)) / SAMPLE_RATE
    seconds = max(16, min(22, math.ceil(voice_seconds + 2.2)))
    pcm = write_wav(audio_path, mix_audio(voice_path, seconds, item["slug"]))
    total = int(seconds * FPS)
    chunks = chunks_for(item["script"], seconds)
    frames = [jpeg_bytes(frame_for(item, i, total, seconds, chunks)) for i in range(total)]
    write_avi(avi_path, frames, pcm)
    convert_to_mp4(avi_path, mp4_path)
    return {"topic": item["title"], "video": mp4_path, "caption": item["caption"], "hashtags": item["hashtags"]}


def main():
    results = [make_one(item) for item in PROTOTYPES]
    summary = {
        "createdAt": datetime.now().isoformat(),
        "note": "Three no-person prototype directions for choosing the channel topic.",
        "prototypes": results,
    }
    with open(os.path.join(OUT, "prototype_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
