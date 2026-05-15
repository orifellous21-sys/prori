import json
import math
import os
import random
import shutil
import struct
import subprocess
import wave
from datetime import datetime
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")
TEMP = os.path.join(ROOT, "output", "temp_quote")
LATEST = os.path.join(ROOT, "output", "latest")
ARCHIVE = os.path.join(ROOT, "ready_videos")
BACKGROUND_IMAGE = os.path.join(ASSETS, "alexander-background-reference.png")

for folder in (TEMP, LATEST, ARCHIVE):
    os.makedirs(folder, exist_ok=True)

WIDTH = 1080
HEIGHT = 1920
FPS = 30
SAMPLE_RATE = 44100

QUOTES = [
    {
        "quote": "The man who conquers himself is stronger than the man who conquers a city.",
        "attribution": "ANCIENT WISDOM",
        "title": "CONQUER YOURSELF",
    },
    {
        "quote": "You do not rise to the level of your dreams. You fall to the level of your discipline.",
        "attribution": "DISCIPLINE",
        "title": "THE REAL TEST",
    },
    {
        "quote": "A person who cannot control his own mind will always be controlled by something else.",
        "attribution": "STOIC LESSON",
        "title": "CONTROL YOUR MIND",
    },
    {
        "quote": "The strongest people are not the loudest. They are the ones who keep moving when nobody is watching.",
        "attribution": "QUIET STRENGTH",
        "title": "NOBODY IS WATCHING",
    },
    {
        "quote": "The pain of discipline is heavy for a moment. The pain of regret follows you for years.",
        "attribution": "LIFE LESSON",
        "title": "CHOOSE YOUR PAIN",
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
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/georgiab.ttf" if bold else "C:/Windows/Fonts/georgia.ttf",
    ]
    for item in candidates:
        if os.path.exists(item):
            return ImageFont.truetype(item, size)
    return ImageFont.load_default()


FONT_HANDLE = font(34, True)
FONT_TITLE = font(50, True)
FONT_WORD = font(70, True)


def run_tts(text, wav_path):
    if os.path.exists(wav_path):
        os.remove(wav_path)
    ps_path = os.path.join(TEMP, "quote_tts.ps1")
    txt_path = os.path.join(TEMP, "quote_script.txt")
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
            "$voice.Rate = -1\n"
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
    if (not os.path.exists(wav_path)) or os.path.getsize(wav_path) < 1000:
        with open(ps_path, "w", encoding="utf-8") as f:
            f.write(
                "param([string]$InputTextPath,[string]$OutputWavPath)\n"
                "$text = Get-Content -Raw -LiteralPath $InputTextPath\n"
                "$voice = New-Object -ComObject SAPI.SpVoice\n"
                "$preferred = @($voice.GetVoices()) | Where-Object { $_.GetDescription() -match 'Zira' } | Select-Object -First 1\n"
                "if ($preferred) { $voice.Voice = $preferred }\n"
                "$stream = New-Object -ComObject SAPI.SpFileStream\n"
                "$stream.Open($OutputWavPath, 3)\n"
                "$voice.AudioOutputStream = $stream\n"
                "$voice.Rate = -1\n"
                "$voice.Volume = 100\n"
                "$voice.Speak($text) | Out-Null\n"
                "$stream.Close()\n"
            )
        subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                ps_path,
                "-InputTextPath",
                txt_path,
                "-OutputWavPath",
                wav_path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    if (not os.path.exists(wav_path)) or os.path.getsize(wav_path) < 1000:
        raise RuntimeError("Windows text-to-speech created an empty voice file")


def read_wav_mono(path):
    with wave.open(path, "rb") as w:
        channels = w.getnchannels()
        rate = w.getframerate()
        frames = w.readframes(w.getnframes())
        data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if len(data) == 0:
        raise RuntimeError("Voice WAV contains no audio samples")
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    if rate != SAMPLE_RATE:
        old_x = np.linspace(0, 1, len(data))
        new_len = int(len(data) * SAMPLE_RATE / rate)
        new_x = np.linspace(0, 1, new_len)
        data = np.interp(new_x, old_x, data).astype(np.float32)
    return data


def write_wav(path, audio):
    audio = np.clip(audio, -0.96, 0.96)
    pcm = (audio * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
    return pcm.tobytes()


def make_music(seconds):
    n = int(seconds * SAMPLE_RATE)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    root = 55.0
    pad = (
        0.28 * np.sin(2 * np.pi * root * t)
        + 0.20 * np.sin(2 * np.pi * root * 1.5 * t)
        + 0.12 * np.sin(2 * np.pi * root * 2.0 * t)
        + 0.06 * np.sin(2 * np.pi * root * 4.0 * t)
    )
    pulse = 0.12 * np.sin(2 * np.pi * 110 * t) * (0.55 + 0.45 * np.sin(2 * np.pi * 0.8 * t))
    shimmer = 0.025 * np.sin(2 * np.pi * 660 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.16 * t))
    hit = np.zeros_like(t)
    for beat in np.arange(0.0, seconds, 1.7):
        start = int(beat * SAMPLE_RATE)
        length = min(int(0.24 * SAMPLE_RATE), len(hit) - start)
        if length > 0:
            env = np.exp(-np.linspace(0, 6.0, length))
            tt = np.arange(length, dtype=np.float32) / SAMPLE_RATE
            hit[start:start + length] += 0.50 * env * np.sin(2 * np.pi * 82 * tt)
    fade = np.minimum(1, t / 1.5) * np.minimum(1, (seconds - t) / 2.0)
    return (pad + pulse + shimmer + hit) * fade * 0.40


def mix_audio(tts_path, seconds):
    voice = read_wav_mono(tts_path)
    total = int(seconds * SAMPLE_RATE)
    audio = make_music(seconds)[:total]
    if len(audio) < total:
        audio = np.pad(audio, (0, total - len(audio)))
    start = int(1.0 * SAMPLE_RATE)
    end = min(total, start + len(voice))
    if end > start:
        duck = np.ones(total, dtype=np.float32)
        duck[start:end] = 0.44
        audio *= duck
        audio[start:end] += voice[:end - start] * 1.05
    peak = np.max(np.abs(audio)) if len(audio) else 1
    if peak > 0.96:
        audio = audio / peak * 0.96
    return audio


def split_quote(quote):
    words = quote.split()
    chunks = []
    for i in range(0, len(words), 3):
        chunks.append(" ".join(words[i:i + 3]).upper())
    return chunks


def timed_chunks(quote, voice_seconds):
    chunks = split_quote(quote)
    start = 1.0
    usable = max(8.0, voice_seconds - 0.4)
    weights = [max(2, len(c.split())) for c in chunks]
    total = sum(weights)
    cursor = start
    result = []
    for index, chunk in enumerate(chunks):
        end = cursor + max(1.25, usable * weights[index] / total)
        result.append((cursor, end, chunk))
        cursor = end
    return result


def wrap_text(draw, text, fnt, max_width):
    words = text.split()
    lines, line = [], ""
    for word in words:
        test = (line + " " + word).strip()
        if draw.textbbox((0, 0), test, font=fnt)[2] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_center(draw, text, y, fnt, fill, max_width):
    lines = wrap_text(draw, text, fnt, max_width)
    heights = [draw.textbbox((0, 0), line, font=fnt)[3] for line in lines]
    total = sum(heights) + 16 * (len(lines) - 1)
    cursor = y - total // 2
    for line, height in zip(lines, heights):
        box = draw.textbbox((0, 0), line, font=fnt)
        x = (WIDTH - (box[2] - box[0])) // 2
        for dx, dy in ((4, 4), (-2, 3), (2, -2)):
            draw.text((x + dx, cursor + dy), line, font=fnt, fill=(0, 0, 0))
        draw.text((x, cursor), line, font=fnt, fill=fill)
        cursor += height + 16


def caption_for_time(t, chunks):
    for start, end, text in chunks:
        if start <= t < end:
            return text
    return ""


def background_source():
    if os.path.exists(BACKGROUND_IMAGE):
        return Image.open(BACKGROUND_IMAGE).convert("RGB")
    return Image.new("RGB", (WIDTH, HEIGHT), (12, 13, 17))


def background_frame(src, frame_index, total_frames, duration, item, chunks):
    t = frame_index / FPS
    img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))

    # Use the statue/architecture side of the asset and avoid the baked-in quote text.
    crop_right = min(src.width, 430)
    scene_src = src.crop((0, 0, crop_right, src.height))
    band_h = 1000
    zoom = 1.0 + 0.030 * (frame_index / max(1, total_frames - 1))
    scale = max(WIDTH / scene_src.width, band_h / scene_src.height) * zoom
    scene = scene_src.resize((int(scene_src.width * scale), int(scene_src.height * scale)), Image.Resampling.LANCZOS)
    left = int((scene.width - WIDTH) * 0.22)
    top = int((scene.height - band_h) * 0.42)
    band = scene.crop((left, top, left + WIDTH, top + band_h)).filter(ImageFilter.GaussianBlur(0.20))
    band_overlay = Image.new("RGBA", (WIDTH, band_h), (0, 0, 0, 118))
    band = Image.alpha_composite(band.convert("RGBA"), band_overlay).convert("RGB")
    img.paste(band, (0, 500))

    draw = ImageDraw.Draw(img)
    draw.text((WIDTH - 388, 600), "@WISDOM_REBORN", font=FONT_HANDLE, fill=(225, 225, 225))
    draw.text((88, 170), item["title"], font=FONT_TITLE, fill=(224, 168, 80))
    caption = caption_for_time(t, chunks)
    if caption:
        draw_center(draw, caption, 1030, FONT_WORD, (255, 255, 255), 660)
    progress = int((frame_index + 1) / total_frames * (WIDTH - 176))
    draw.rounded_rectangle((88, 1770, WIDTH - 88, 1785), radius=8, fill=(55, 50, 48))
    draw.rounded_rectangle((88, 1770, 88 + progress, 1785), radius=8, fill=(224, 168, 80))
    return img


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
    if audio_pos < len(pcm_audio):
        aud = pcm_audio[audio_pos:]
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


def main():
    item = random.choice(QUOTES)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    raw_voice = os.path.join(TEMP, "quote_voice.wav")
    final_audio = os.path.join(TEMP, "quote_audio.wav")
    avi = os.path.join(TEMP, "quote_video.avi")
    mp4 = os.path.join(LATEST, "video.mp4")
    caption_path = os.path.join(LATEST, "caption.txt")
    meta_path = os.path.join(LATEST, "details.json")
    print("Creating better narrator voice...")
    run_tts(f"{item['quote']} {item['attribution'].title()}.", raw_voice)
    voice_seconds = len(read_wav_mono(raw_voice)) / SAMPLE_RATE
    duration = max(22, min(36, int(math.ceil(voice_seconds + 4.0))))
    chunks = timed_chunks(item["quote"], voice_seconds)
    print("Creating cinematic background music...")
    pcm = write_wav(final_audio, mix_audio(raw_voice, duration))
    print("Creating quote-style frames...")
    src = background_source()
    total_frames = int(duration * FPS)
    frames = [jpeg_bytes(background_frame(src, i, total_frames, duration, item, chunks)) for i in range(total_frames)]
    write_avi(avi, frames, pcm)
    print("Rendering MP4...")
    convert_to_mp4(avi, mp4)
    caption = f"{item['quote']}\n\n#{item['title'].replace(' ', '')} #motivation #quotes #shorts"
    with open(caption_path, "w", encoding="utf-8") as f:
        f.write(caption)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({"createdAt": datetime.now().isoformat(), "style": "dark cinematic quote video inspired by the uploaded reference", "video": mp4, "quote": item["quote"], "attribution": item["attribution"], "caption": caption, "music": "Original synthesized cinematic background music.", "voice": "Microsoft David Desktop when available"}, f, indent=2)
    archive_video = os.path.join(ARCHIVE, f"quote_video_{stamp}.mp4")
    shutil.copy2(mp4, archive_video)
    print(json.dumps({"ok": True, "video": mp4, "caption": caption_path, "archive": archive_video}, indent=2))


if __name__ == "__main__":
    main()
