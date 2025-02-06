import ffmpeg
import os
from math import floor
from .utils import generate_random_string
from custom_logger import logger_config

def get_video_info(input_path):
	"""Get video duration and bitrate information."""
	logger_config.debug(f"Getting video info for: {input_path}")
	probe = ffmpeg.probe(input_path)
	video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
	duration = float(probe['format']['duration'])
	logger_config.debug(f"Video duration: {duration} seconds")
	return video_info, duration

def calculate_bitrate(target_size_mb, duration, audio_bitrate_kb=128):
	"""Calculate video bitrate based on target size."""
	logger_config.debug(f"Calculating bitrate for target size: {target_size_mb}MB, duration: {duration}s")
	target_size_bytes = target_size_mb * 1024 * 1024
	audio_size_bytes = (audio_bitrate_kb * 1024 * duration) / 8
	video_size_bytes = target_size_bytes - audio_size_bytes
	video_bitrate_kb = floor((video_size_bytes * 8) / (duration * 1024))
	final_bitrate = max(video_bitrate_kb, 100)
	logger_config.debug(f"Calculated video bitrate: {final_bitrate}kb/s")
	return final_bitrate

def compress_video(input_path, target_size_mb=400, output_path=None, height=480):
	"""
	Compress a video to target size while maintaining quality.
	
	Args:
		input_path (str): Path to input video file
		target_size_mb (int): Target size in MB (default 400)
		output_path (str, optional): Path for output video
		height (int): Target height in pixels (default 480)
	
	Returns:
		str: Path to the compressed video file
	"""
	logger_config.info(f"Starting video compression for: {input_path}")
	logger_config.info(f"Target size: {target_size_mb}MB, Target height: {height}p")
	
	try:
		# Get video information
		logger_config.debug("Retrieving video information...")
		video_info, duration = get_video_info(input_path)
		width = int(video_info['width'])
		input_height = int(video_info['height'])
		
		# Calculate new width to maintain aspect ratio
		aspect_ratio = width / input_height
		target_width = int(height * aspect_ratio)
		target_width = target_width - (target_width % 2)
		logger_config.debug(f"New dimensions: {target_width}x{height}")
		
		# Calculate required bitrate for target size
		video_bitrate_kb = calculate_bitrate(target_size_mb, duration)
		
		# Generate output path if not provided
		if output_path is None:
			_, ext = os.path.splitext(input_path)
			output_path = f'{os.getenv("TEMP_OUTPUT", "tempOutput")}/{generate_random_string()}_compress_video{ext}'
			logger_config.debug(f"Generated output path: {output_path}")
		
		# Set up FFmpeg stream
		logger_config.debug("Setting up FFmpeg stream...")
		stream = ffmpeg.input(input_path)
		
		# Apply the compression
		logger_config.info("Starting compression process...")
		stream = ffmpeg.output(stream, output_path,
							 **{
								 'vf': f'scale={target_width}:{height}',
								 'c:v': 'libx264',
								 'b:v': f'{video_bitrate_kb}k',
								 'maxrate': f'{video_bitrate_kb * 1.5}k',
								 'bufsize': f'{video_bitrate_kb * 3}k',
								 'crf': 18,
								 'preset': 'slow',
								 'c:a': 'aac',
								 'b:a': '128k'
							 })
		
		# Run the compression
		ffmpeg.run(stream, overwrite_output=True)
		
		# Verify final size
		final_size_mb = os.path.getsize(output_path) / (1024 * 1024)
		logger_config.info(f"Compression completed. Final video size: {final_size_mb:.2f} MB")
		
		return output_path
		
	except ffmpeg.Error as e:
		error_message = e.stderr.decode() if hasattr(e, 'stderr') else str(e)
		logger_config.error(f"FFmpeg error occurred: {error_message}")
		raise
	except Exception as e:
		logger_config.error(f"Unexpected error occurred: {str(e)}", exc_info=True)
		raise

# Example usage
if __name__ == "__main__":
	try:
		input_video = "media/movie_review/Blame 2017.mkv"
		logger_config.info(f"Starting compression process for: {input_video}")
		
		compressed_video = compress_video(
			input_video,
			target_size_mb=400,
			height=480
		)
		logger_config.info(f"Video compression successful. Output file: {compressed_video}")
	except Exception as e:
		logger_config.error(f"Compression process failed: {str(e)}", exc_info=True)