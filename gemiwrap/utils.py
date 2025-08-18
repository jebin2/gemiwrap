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

def split_video(video_path):
    """
    Split a video file into multiple parts based on token validation, using fast subclip extraction.
    
    Args:
        video_path: Path to the input video file
        
    Returns:
        Tuple[List[Path], List[Tuple[float, float]]]:
            - List of paths to successfully created video parts
            - List of (start_sec, end_sec) ranges
    """
    parts = validate_video_tokens(video_path)
    if parts == -1:
        duration = video_duration(video_path)
        return [video_path], [(0, duration if duration else None)]

    logger_config.info(f"Attempting to split video: {video_path} into {parts} parts.")
    
    path = Path(video_path)
    name = path.stem
    ext = path.suffix
    all_files = []
    time_ranges = []
    temp_dir = Path(os.getenv("TEMP_OUTPUT", "tempOutput")) / name
    temp_dir.mkdir(parents=True, exist_ok=True)

    duration = video_duration(video_path)
    if duration is None or duration <= 0:
        logger_config.error("Could not determine video duration or duration is zero.")
        return [], []

    each_dur = int(duration / parts)
    logger_config.info(f"Total duration: {duration}s. Each part approx: {each_dur:.2f}s")

    for i in range(parts):
        start_sec = i * each_dur
        end_sec = duration if i == parts - 1 else (i + 1) * each_dur

        output_filename = f"{name}_{start_sec:.2f}_{end_sec:.2f}.mp4"
        output_path = temp_dir / output_filename

        # Skip if file already exists
        if output_path.exists():
            logger_config.info(f"Part {i+1} already exists, skipping: {output_path}")
            all_files.append(output_path)
            time_ranges.append((start_sec, end_sec))
            continue

        # Build ffmpeg command for fast subclip (no re-encoding)
        cmd = ["ffmpeg", "-y"]  # -y to overwrite existing files

        # CRITICAL FIX: Put -ss BEFORE -i for accurate seeking
        if start_sec > 0:
            cmd += ["-ss", f"{start_sec:.3f}"]
        
        # Input file first
        cmd += ["-i", str(video_path)]
        
        # Duration instead of end time for more reliable results
        duration_part = end_sec - start_sec
        cmd += ["-t", f"{duration_part}"]
        
        # Copy streams without re-encoding for speed
        cmd += ["-c", "copy"]
        
        # Avoid negative timestamps and other issues
        cmd += ["-avoid_negative_ts", "make_zero"]
        
        # Output file
        cmd += [str(output_path)]

        # Run ffmpeg
        subprocess.run(cmd, check=True)
        logger_config.success(f"Successfully created Part {i+1} :: {output_path}")

        all_files.append(output_path)
        time_ranges.append((start_sec, end_sec))

    return all_files, time_ranges


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

def compress_video(input_path, output_path=None):
    """
    Simple, optimized video compression specifically for Google Gemini Pro.
    No complex settings - just compress any video to work perfectly with Gemini Pro.
    
    Optimizations for Gemini Pro:
    - 2 FPS (perfect for LLM frame analysis)
    - 480x270 resolution (readable but compact)
    - Aggressive compression while maintaining visual clarity
    - Always produces small files suitable for LLM processing
    
    Parameters:
    - input_path: Path to input video file
    - output_path: Optional output path (auto-generated if None)
    
    Returns:
    - Path to compressed video file
    """
    
    path = Path(input_path)
    name = path.stem
    
    # Create output directory
    temp_dir = Path(os.getenv("TEMP_OUTPUT", "tempOutput")) / name
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    if output_path is None:
        output_path = temp_dir / f"{name}_compressed.mp4"
    else:
        output_path = Path(output_path)
    
    # Skip if already processed
    if output_path.exists():
        existing_size = os.path.getsize(output_path) / (1024 * 1024)
        print(f"Already compressed: {existing_size:.1f}MB")
        return str(output_path)
    
    # Get input file size
    input_size_mb = os.path.getsize(input_path) / (1024 * 1024)
    
    # Temporary output file
    tmp_output = output_path.with_suffix(".tmp.mp4")
    if tmp_output.exists():
        tmp_output.unlink()
    
    print(f"Compressing for Gemini Pro: {input_size_mb:.1f}MB → optimized")
    
    # Gemini Pro optimized FFmpeg command
    cmd = [
        "ffmpeg", "-i", str(input_path),
        
        # Video: H.264 with aggressive but readable compression
        "-c:v", "libx264",
        "-crf", "32",                    # Aggressive compression, still readable
        "-preset", "veryslow",           # Best compression efficiency
        
        # Resolution and frame rate optimized for Gemini Pro
        "-vf", "scale=480:270:force_original_aspect_ratio=decrease:force_divisible_by=2,fps=2",
        
        # Audio: Minimal but present
        "-c:a", "aac",
        "-b:a", "24k",                   # Very low audio bitrate
        "-ac", "1",                      # Mono
        "-ar", "22050",                  # Lower sample rate
        
        # Optimize for small file size and streaming
        "-movflags", "+faststart",
        "-avoid_negative_ts", "make_zero",
        
        # Advanced compression settings
        "-x264-params", "keyint=120:scenecut=40:b-adapt=2:me=hex:subme=6:ref=3",
        
        "-f", "mp4",
        "-y", str(tmp_output)
    ]
    
    # Execute compression
    process = subprocess.run(cmd, text=True)
    
    if process.returncode == 0:
        # Move to final location
        tmp_output.rename(output_path)
        
        # Show results
        output_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        compression_ratio = input_size_mb / output_size_mb if output_size_mb > 0 else 0
        savings_percent = ((input_size_mb - output_size_mb) / input_size_mb * 100) if input_size_mb > 0 else 0
        
        print(f"✅ Gemini Pro ready: {output_size_mb:.1f}MB ({compression_ratio:.1f}x smaller, {savings_percent:.1f}% saved)")
        
        return str(output_path)
    else:
        # Clean up on failure
        if tmp_output.exists():
            tmp_output.unlink()
        print(f"❌ Compression failed: {process.stderr}")
        raise ValueError("Compression failed")

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