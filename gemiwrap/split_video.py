import ffmpeg
from custom_logger import logger_config
import os
from .utils import generate_random_string, video_duration


def split(video_path, parts=3):
    logger_config.info(f"Attempting to split video: {video_path} into {parts} parts.")
    _, ext = os.path.splitext(video_path)
    all_files = []
    temp_dir = os.getenv("TEMP_OUTPUT", "tempOutput")
    os.makedirs(temp_dir, exist_ok=True)

    duration = video_duration(video_path)
    if duration is None or duration <= 0:
        logger_config.error("Could not determine video duration or duration is zero.")
        return []
    each_dur = duration / parts
    logger_config.info(f"Total duration: {duration}s. Each part approx: {each_dur:.2f}s")

    output_vcodec = 'libx264'
    output_crf = 22
    output_preset = 'medium'
    output_acodec = 'copy'

    for i in range(parts):
        output_filename = f'{generate_random_string()}_split_video_{i + 1}{ext}'
        output_path = os.path.join(temp_dir, output_filename)
        start_time = i * each_dur

        stream = ffmpeg.input(video_path, ss=start_time)
        output_args = {
            'acodec': output_acodec,
            'vcodec': output_vcodec,
            'crf': output_crf,
            'preset': output_preset,
            'map_metadata': -1,
            'avoid_negative_ts': 'make_zero'
        }

        if i < parts - 1:
            stream = ffmpeg.output(stream, output_path, t=each_dur, **output_args)
        else:
            stream = ffmpeg.output(stream, output_path, **output_args)

        logger_config.info(f"Running FFmpeg for part {i+1}: Start={start_time:.2f}" + (f", Duration={each_dur:.2f}" if i < parts-1 else ", Duration=ToEnd"))
        stream.run()
        logger_config.success(f'Successfully created Part {i + 1} :: {output_path}')
        all_files.append(output_path)

    if len(all_files) == parts:
        logger_config.success(f"Video split successfully into {parts} parts!")
    else:
        logger_config.warning(f"Video splitting finished, but only {len(all_files)} out of {parts} parts were created.")

    return all_files