import os
import string
import secrets
import ffmpeg
import mimetypes
import subprocess
from pathlib import Path
from custom_logger import logger_config
import math

def generate_random_string(length=10):
    characters = string.ascii_letters
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return random_string

def is_video_file(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type and mime_type.startswith("video")

def video_duration(file_path):
	if not os.path.isfile(file_path) or not is_video_file(file_path):
		return 0

	probe = ffmpeg.probe(file_path)
	duration = int(float(probe['format']['duration'])) # seconds
	return duration

def compress_image(input_path):
    logger_config.info("Compressing Image")
    temp_dir = os.getenv("TEMP_OUTPUT", "tempOutput")
    os.makedirs(temp_dir, exist_ok=True)
    output_filename = f'{generate_random_string()}_compress_image_{input_path.split(".")[-1]}'
    output_path = os.path.join(temp_dir, output_filename)
    from PIL import Image
    image = Image.open(input_path)

    # Convert RGBA to RGB if necessary
    if image.mode == "RGBA":
        image = image.convert("RGB")

    # Remove EXIF metadata if present
    if "exif" in image.info:
        logger_config.info("EXIF metadata found and removed.")
        image.save(output_path, "JPEG", optimize=True, progressive=True)
        import piexif
        piexif.remove(output_path)
    else:
        image.save(output_path, "JPEG", optimize=True, progressive=True)

    return output_path

def compress_video(input_path, output_path=None, crf=23, resolution="640x360", fps=10, audio_bitrate="64k", preset="medium"):
    """
    Compress a video optimized for LLM processing.

    Parameters:
    - input_path: Path to the input video file
    - output_path: Path for the output file (default: input filename + "_compressed.mp4")
    - crf: Constant Rate Factor (18-28 recommended, 23 is default, lower = better quality)
    - resolution: Output resolution (default: 640x360)
    - fps: Frames per second (default: 10, sufficient for most content analysis)
    - audio_bitrate: Audio bitrate (default: 64k)
    - preset: FFmpeg preset (faster = less compression, slower = more compression)
    
    Returns:
    - Path to the compressed video file
    """
    path = Path(input_path)
    name = path.stem
    ext = path.suffix
    temp_dir = Path(os.getenv("TEMP_OUTPUT", "tempOutput")) / name
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(temp_dir / f"{name}_compressed{ext}")

    if not Path(output_path).exists():
        # Build FFmpeg command
        cmd = [
            "ffmpeg", "-i", input_path,
            "-c:v", "libx264",           # H.264 video codec
            "-crf", str(crf),            # Quality setting
            "-preset", preset,           # Compression preset
            "-vf", f"scale={resolution}", # Resolution
            "-r", str(fps),              # Frame rate
            "-c:a", "aac",               # AAC audio codec
            "-b:a", audio_bitrate,       # Audio bitrate
            "-movflags", "+faststart",   # Optimize for web streaming
            "-y",                        # Overwrite output file if it exists
            output_path
        ]

        # Execute FFmpeg command
        process = subprocess.run(cmd)

        if process.returncode != 0:
            return input_path

    return output_path

def validate_video_tokens(video_path):
    duration_minutes = video_duration(video_path) // 60
    max_chunk = 40

    if duration_minutes <= max_chunk:
        return -1  # no split needed

    # Determine the smallest number of equal chunks not exceeding max_chunk
    for parts in range(2, duration_minutes + 1):
        chunk_size = math.ceil(duration_minutes / parts)
        if chunk_size <= max_chunk:
            return parts  # number of parts to split into

    return -1  # fallback