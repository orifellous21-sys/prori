import os
import wave

import numpy as np


ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "ready_videos")
os.makedirs(OUT, exist_ok=True)

SAMPLE_RATE = 44100
DURATION = 42


def envelope(length, attack=0.08, release=0.22):
    env = np.ones(length, dtype=np.float32)
    a = max(1, int(length * attack))
    r = max(1, int(length * release))
    env[:a] = np.linspace(0, 1, a)
    env[-r:] = np.linspace(1, 0, r)
    return env


def tone(freq, seconds, volume=0.25, vibrato=0.0):
    n = int(seconds * SAMPLE_RATE)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    vib = vibrato * np.sin(2 * np.pi * 5.2 * t)
    return np.sin(2 * np.pi * (freq + vib) * t) * envelope(n) * volume


def add_note(track, start, freq, seconds, volume=0.25, vibrato=0.0):
    data = tone(freq, seconds, volume, vibrato)
    pos = int(start * SAMPLE_RATE)
    end = min(len(track), pos + len(data))
    if end > pos:
        track[pos:end] += data[: end - pos]


def make_track():
    total = int(DURATION * SAMPLE_RATE)
    track = np.zeros(total, dtype=np.float32)
    melody = [
        (0.0, 220.00, 1.6), (1.8, 246.94, 1.2), (3.1, 261.63, 1.7),
        (5.1, 246.94, 1.4), (6.7, 220.00, 2.1), (9.4, 196.00, 1.5),
        (11.1, 220.00, 1.8), (13.2, 174.61, 2.6), (17.0, 220.00, 1.5),
        (18.7, 293.66, 1.3), (20.3, 329.63, 1.9), (22.6, 293.66, 1.4),
        (24.2, 261.63, 2.4), (27.5, 246.94, 1.5), (29.2, 220.00, 2.0),
        (31.7, 196.00, 2.8), (35.6, 174.61, 1.5), (37.4, 196.00, 1.5),
        (39.2, 220.00, 2.2),
    ]
    for start, freq, seconds in melody:
        add_note(track, start, freq, seconds, 0.22, 1.6)
        add_note(track, start, freq * 2, seconds * 0.96, 0.055, 1.1)
    for start in np.arange(0, DURATION, 4.0):
        add_note(track, float(start), 55.0, 4.8, 0.16, 0.15)
        add_note(track, float(start), 82.41, 4.4, 0.10, 0.10)
        add_note(track, float(start), 110.0, 3.8, 0.07, 0.05)
    for start in np.arange(0.7, DURATION, 1.8):
        n = int(0.16 * SAMPLE_RATE)
        t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
        hit = np.sin(2 * np.pi * 74 * t) * np.exp(-np.linspace(0, 6, n)) * 0.11
        pos = int(start * SAMPLE_RATE)
        end = min(len(track), pos + n)
        track[pos:end] += hit[: end - pos]
    rng = np.random.default_rng(7)
    noise = rng.normal(0, 0.006, total).astype(np.float32)
    fade = np.minimum(1, np.arange(total) / (SAMPLE_RATE * 3)) * np.minimum(1, (total - np.arange(total)) / (SAMPLE_RATE * 4))
    return np.clip((track + noise) * fade, -0.92, 0.92)


def main():
    out = os.path.join(OUT, "dark_is_the_night_style_original_prototype.wav")
    pcm = (make_track() * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
    print(out)


if __name__ == "__main__":
    main()
