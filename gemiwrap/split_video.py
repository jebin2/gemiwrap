import ffmpeg
from custom_logger import logger_config
import os
from .utils import generate_random_string, video_duration

def split(video_path, parts=3):
	_, ext = os.path.splitext(video_path)
	duration = video_duration(video_path)
	each_dur = duration // parts

	all_files = []

	for i in range(parts):
		output_path = f'{os.environ["TEMP_OUTPUT"]}/{generate_random_string()}_split_video_{i + 1}{ext}'
		start_time = i * each_dur
		if i + 1 == parts:  # Last part
			ffmpeg.input(video_path, ss=start_time).output(output_path,
						acodec='copy',
						vcodec='copy').run()
		else:
			ffmpeg.input(video_path, ss=start_time, t=each_dur).output(output_path,
						acodec='copy',
						vcodec='copy').run()

		all_files.append(output_path)
		logger_config.success(f'Part {i + 1} :: {output_path}')

	logger_config.success("Video split successfully!")
	return all_files


# Example usage
if __name__ == "__main__":
	split("media/movie_review/Blame 2017.mkv")
