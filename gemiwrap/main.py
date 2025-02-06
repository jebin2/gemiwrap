import google.generativeai as genai
from .utils import load_dotenv_if_exists, video_duration
from custom_logger import logger_config
import os
import mimetypes
from google.api_core.exceptions import ResourceExhausted

class GeminiWrapper:
	DEFAULT_GENERATION_CONFIG = {
		"temperature": 1,
		"top_p": 0.95,
		"top_k": 40,
		"max_output_tokens": 8192,
		"response_schema": None,
		"response_mime_type": "application/json"
	}

	def __init__(self, model_name="gemini-2.0-flash", generation_config=None, system_instruction=None, history=None, delete_files=False):
		load_dotenv_if_exists()

		self._model_name = model_name
		self.generation_config = generation_config or self.DEFAULT_GENERATION_CONFIG
		self.system_instruction = system_instruction
		self.history = history or []

		self.used_keys = set()
		self.current_key = None

		self._initialize_api()

		if delete_files:
			self.delete_file_paths()

	def _initialize_api(self):
		try:
			self._set_current_key()
			genai.configure(api_key=self.current_key)
			
			self.model = genai.GenerativeModel(
				model_name=self._model_name,
				generation_config=self.generation_config,
				system_instruction=self.system_instruction,
			)
		except Exception as e:
			logger_config.error(f"API initialization failed: {e}")
			raise

	def _set_current_key(self):
		keys = os.getenv("GEMINI_API_KEY", "").split(",")
		keys = [key.strip() for key in keys if key.strip()]
		
		if not keys:
			raise ValueError("No Gemini API keys available")

		# Rotate keys more efficiently
		for key in keys:
			if key not in self.used_keys:
				self.current_key = key
				self.used_keys.add(key)
				return

		# Reset if all keys used
		self.used_keys.clear()
		self.current_key = keys[0]
		self.used_keys.add(self.current_key)

	def _get_mime_type(self, file):
		return mimetypes.guess_type(file)[0] or "application/octet-stream"

	def _upload_to_gemini(self, path):
		file = genai.upload_file(path, mime_type=self._get_mime_type())
		logger_config.debug(f"Uploaded file '{file.display_name}' as: {file.uri}")
		return file

	def delete_file_paths(self):
		for file in genai.list_files():
			genai.delete_file(file.name)
			logger_config.success(f"Deleted file '{file.name}'")

	def _wait_for_files_active(self, files):
		logger_config.debug("Waiting for file processing...")
		for name in (file.name for file in files):
			file = genai.get_file(name)
			while file.state.name == "PROCESSING":
				logger_config.debug("", seconds=10)
				file = genai.get_file(name)

			if file.state.name != "ACTIVE":
				raise Exception(f"File {file.name} failed to process")

		logger_config.success("...all files ready")

	def _validate_video_tokens(self, video_path):
		video_token_per_second = 263
		model_info = genai.get_model(self._model_name)
		total_video_token = (video_token_per_second * video_duration(video_path))
		logger_config.info(f"Video Token :: {total_video_token}")
		logger_config.info(f"Accepted Token :: {model_info.input_token_limit}")
		if total_video_token > model_info.input_token_limit:
			logger_config.warning(f"Extra Token :: {total_video_token - model_info.input_token_limit}")
			return False

		return True

	def send_message(self, user_prompt="", file_path=None):
		file_paths = [file_path] if file_path else [None]

		if file_path and not self._validate_video_tokens(file_path):
			from . import split_video
			file_paths = split_video.split(file_path)

		chat_session = None
		index = 0
		while True:
			file = file_paths[index]
			try:
				if file and os.path.getsize(file) > (1024 * 1024 * 1024):
					from . import compress_video
					file = compress_video.compress_video(
						file,
						target_size_mb=500,
						height=720
					)

				if not chat_session or len(file_paths) > 1:
					logger_config.info("Starting a new chat session due to exceed limit")
					self.delete_file_paths()
					self.history.clear()
					chat_session = self.model.start_chat(history=self.history)

				text = user_prompt
				if len(file_paths) > 1:
					text = f'{user_prompt} Part {index+1} of {len(file_paths)}'

				logger_config.debug(f"user_prompt: {text}")
				self.history.append({
					"role": "user",
					"parts": [
						{"text": text}
					]
				})
				if file:
					uploaded_file = self._upload_to_gemini(file)
					self._wait_for_files_active([uploaded_file])
					self.history[-1]["parts"].append(uploaded_file)

				response = chat_session.send_message(content=self.history[-1])
				self.history.append({"role": "model", "parts": [response.text]})
				logger_config.debug(f"Google AI studio response: {response.text}")
				index += 1

				if not file or len(file_paths) == index:
					break

			except ResourceExhausted:
				logger_config.warning("Quota exceeded, switching API key...")
				del self.history[-1:]
				chat_session = None
				self._initialize_api()

		return response.text

	def get_history(self):
		return self.history