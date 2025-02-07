import os
from dotenv import load_dotenv
import string
import secrets

def load_dotenv_if_exists():
	"""Loads environment variables from a .env file if it exists."""
	if os.path.exists(".env"):
		load_dotenv()
		return True
	return False

def generate_random_string(length=10):
    characters = string.ascii_letters
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return random_string

def video_duration(file_path):
	from pymediainfo import MediaInfo
	media_info = MediaInfo.parse(file_path)
	for track in media_info.tracks:
		if track.track_type == "Video":
			return int(float(track.duration)) // 1000

	return 0