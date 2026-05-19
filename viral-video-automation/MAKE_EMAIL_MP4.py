import argparse
import glob
import os
import subprocess
import sys
import site


def find_ffmpeg():
    for folder in [site.getusersitepackages(), *site.getsitepackages()]:
        for candidate in glob.glob(os.path.join(folder, "imageio_ffmpeg", "binaries", "ffmpeg*.exe")):
            if os.path.exists(candidate):
                return candidate

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass

    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", "imageio-ffmpeg"], check=True)
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as error:
        raise RuntimeError(f"Could not install or locate ffmpeg: {error}")


def convert(input_path, output_path):
    ffmpeg = find_ffmpeg()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        input_path,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
        output_path,
    ]
    subprocess.run(command, check=True)
    print(output_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    convert(args.input, args.output)


if __name__ == "__main__":
    main()
