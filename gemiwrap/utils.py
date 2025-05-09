import os
import string
import secrets
import ffmpeg
import mimetypes

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

def optimize_image(input_path):
    temp_dir = os.getenv("TEMP_OUTPUT", "tempOutput")
    os.makedirs(temp_dir, exist_ok=True)
    output_filename = f'{generate_random_string()}_optimize_image_{input_path.split(".")[-1]}'
    output_path = os.path.join(temp_dir, output_filename)
    from PIL import Image
    image = Image.open(input_path)

    # Convert RGBA to RGB if necessary
    if image.mode == "RGBA":
        image = image.convert("RGB")

    # Remove EXIF metadata if present
    if "exif" in image.info:
        print("EXIF metadata found and removed.")
        image.save(output_path, "JPEG", optimize=True, progressive=True)
        import piexif
        piexif.remove(output_path)
    else:
        image.save(output_path, "JPEG", optimize=True, progressive=True)

    return output_path