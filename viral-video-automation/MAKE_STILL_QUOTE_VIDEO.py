import os
import struct
import wave
from datetime import datetime
from io import BytesIO

import numpy as np
from PIL import Image


ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "ready_videos")
ASSET = os.path.join(ROOT, "assets", "jung-fresco-quote-poster.png")
MUSIC = os.path.join(OUT, "dark_is_the_night_style_original_prototype.wav")

WIDTH = 540
HEIGHT = 960
FPS = 15
SAMPLE_RATE = 44100
FADE_IN = 1.35
HOLD = 7.5
FADE_OUT = 1.75
DURATION = FADE_IN + HOLD + FADE_OUT


def prepare_image(path):
    img = Image.open(path).convert("RGB")
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


def fade_alpha(t):
    if t < FADE_IN:
        return max(0.0, min(1.0, t / FADE_IN))
    if t > FADE_IN + HOLD:
        return max(0.0, min(1.0, (DURATION - t) / FADE_OUT))
    return 1.0


def jpeg_bytes(img):
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=72, optimize=True)
    return buf.getvalue()


def read_music(path):
    with wave.open(path, "rb") as w:
        channels = w.getnchannels()
        rate = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    if rate != SAMPLE_RATE:
        old_x = np.linspace(0, 1, len(data))
        new_len = int(len(data) * SAMPLE_RATE / rate)
        new_x = np.linspace(0, 1, new_len)
        data = np.interp(new_x, old_x, data).astype(np.float32)
    return data


def make_audio():
    total = int(DURATION * SAMPLE_RATE)
    music = read_music(MUSIC)
    if len(music) < total:
        music = np.pad(music, (0, total - len(music)))
    else:
        music = music[:total]
    t = np.arange(total, dtype=np.float32) / SAMPLE_RATE
    fade = np.ones(total, dtype=np.float32)
    fade *= np.minimum(1.0, t / max(0.001, FADE_IN))
    fade *= np.minimum(1.0, (DURATION - t) / max(0.001, FADE_OUT))
    audio = music * fade * 0.95
    return (np.clip(audio, -0.95, 0.95) * 32767).astype(np.int16).tobytes()


def chunk(fourcc, data):
    return fourcc + struct.pack("<I", len(data)) + data + (b"\0" if len(data) % 2 else b"")


def list_chunk(kind, data):
    return b"LIST" + struct.pack("<I", len(data) + 4) + kind + data


def write_avi(path, frames, pcm_audio):
    audio_block_align = 2
    audio_avg = SAMPLE_RATE * audio_block_align
    video_max = max(len(f) for f in frames)
    total_frames = len(frames)

    avih = struct.pack(
        "<IIIIIIIIII4I",
        int(1_000_000 / FPS),
        0,
        0,
        0x10,
        total_frames,
        0,
        2,
        max(video_max, 8192),
        WIDTH,
        HEIGHT,
        0,
        0,
        0,
        0,
    )
    v_strh = struct.pack(
        "<4s4sIHHIIIIIIIIhhhh",
        b"vids",
        b"MJPG",
        0,
        0,
        0,
        0,
        1,
        FPS,
        0,
        total_frames,
        video_max,
        0xFFFFFFFF,
        0,
        0,
        0,
        WIDTH,
        HEIGHT,
    )
    v_strf = struct.pack("<IiiHH4sIiiII", 40, WIDTH, HEIGHT, 1, 24, b"MJPG", WIDTH * HEIGHT * 3, 0, 0, 0, 0)
    a_strh = struct.pack(
        "<4s4sIHHIIIIIIIIhhhh",
        b"auds",
        b"\0\0\0\0",
        0,
        0,
        0,
        0,
        audio_block_align,
        audio_avg,
        0,
        len(pcm_audio) // audio_block_align,
        8192,
        0xFFFFFFFF,
        audio_block_align,
        0,
        0,
        0,
        0,
    )
    a_strf = struct.pack("<HHIIHH", 1, 1, SAMPLE_RATE, audio_avg, audio_block_align, 16)
    hdrl = list_chunk(
        b"hdrl",
        chunk(b"avih", avih)
        + list_chunk(b"strl", chunk(b"strh", v_strh) + chunk(b"strf", v_strf))
        + list_chunk(b"strl", chunk(b"strh", a_strh) + chunk(b"strf", a_strf)),
    )

    movi_data = bytearray()
    index = []
    audio_pos = 0
    audio_per_frame = int(SAMPLE_RATE / FPS) * audio_block_align
    for frame in frames:
        offset = len(movi_data) + 4
        movi_data.extend(chunk(b"00dc", frame))
        index.append((b"00dc", 0x10, offset, len(frame)))
        aud = pcm_audio[audio_pos : audio_pos + audio_per_frame]
        audio_pos += len(aud)
        if aud:
            offset = len(movi_data) + 4
            movi_data.extend(chunk(b"01wb", aud))
            index.append((b"01wb", 0, offset, len(aud)))
    if audio_pos < len(pcm_audio):
        aud = pcm_audio[audio_pos:]
        offset = len(movi_data) + 4
        movi_data.extend(chunk(b"01wb", aud))
        index.append((b"01wb", 0, offset, len(aud)))

    movi = list_chunk(b"movi", bytes(movi_data))
    idx1 = chunk(b"idx1", b"".join(struct.pack("<4sIII", *entry) for entry in index))
    body = hdrl + movi + idx1
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", len(body) + 4) + b"AVI " + body)


def main():
    os.makedirs(OUT, exist_ok=True)
    base = prepare_image(ASSET)
    black = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    frames = []
    total_frames = int(DURATION * FPS)
    for i in range(total_frames):
        t = i / FPS
        frames.append(jpeg_bytes(Image.blend(black, base, fade_alpha(t))))
    audio = make_audio()
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out = os.path.join(OUT, f"jung_quote_fade_music_{stamp}.avi")
    write_avi(out, frames, audio)
    print(out)


if __name__ == "__main__":
    main()
