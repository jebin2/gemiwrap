import os
from dotenv import load_dotenv
import string
import secrets
import ffmpeg

def load_dotenv_if_exists():
	if os.path.exists(".env"):
		load_dotenv()
		return True
	return False

def generate_random_string(length=10):
    characters = string.ascii_letters
    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return random_string

def video_duration(file_path):
	if not os.path.isfile(file_path):
		return 0

	probe = ffmpeg.probe(file_path)
	duration = int(float(probe['format']['duration'])) # seconds
	return duration