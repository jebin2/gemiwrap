from .utils import video_duration, compress_image, compress_video as compress_video_util
from custom_logger import logger_config
import os
import concurrent.futures
from google import genai
from google.genai import types
import httpx

class GeminiWrapper:

	def __init__(self, model_name="gemini-2.0-flash", system_instruction=None, history=None, delete_files=False, tools=None, thinking_config=None, schema=None, response_mime_type="application/json"):
		self._model_name = model_name
		self.system_instruction = system_instruction
		self.history = history or []
		self.schema = schema
		self.response_mime_type = response_mime_type
		self.tools = tools
		self.thinking_config = thinking_config

		self.used_keys = set()
		self.current_key = None

		self.__initialize_api(self.history)

		if delete_files:
			self.__delete_file_paths()

	def __initialize_api(self, history=None):
		try:
			self.__set_new_current_key()
			self.client = genai.Client(api_key=self.current_key)
			self.chat = self.client.chats.create(model=self._model_name, history=history)

			logger_config.debug(f"system_instruction:: {self.system_instruction}")
			logger_config.debug(f"history:: {self.history}")
			self.chat_session = None
		except Exception as e:
			logger_config.error(f"API initialization failed: {e}")
			raise

	def __set_new_current_key(self):
		keys = os.getenv("GEMINI_API_KEYS", "").split(",")
		keys = [key.strip() for key in keys if key.strip()]
		
		if not keys:
			raise ValueError("No Gemini API keys available")

		for key in keys:
			if key not in self.used_keys:
				self.current_key = key
				self.used_keys.add(key)
				return

		self.used_keys.clear()
		self.current_key = keys[0]
		self.used_keys.add(self.current_key)

	def __upload_to_gemini(self, path):
		file = self.client.files.upload(file=path)
		logger_config.debug(f"Uploaded file '{file.display_name}' as: {file.uri}")
		return file

	def __delete_file_paths(self):
		try:
			for file in self.client.files.list():
				self.client.files.delete(name=file.name)
				logger_config.success(f"Deleted file '{file.name}'")
		except:
			pass

	def __wait_for_files_active(self, files):
		logger_config.debug("Waiting for file processing...")
		for name in (file.name for file in files):
			file = self.client.files.get(name=name)
			while file.state.name == "PROCESSING":
				logger_config.debug("", seconds=10)
				file = self.client.files.get(name=name)

			if file.state.name != "ACTIVE":
				raise Exception(f"File {file.name} failed to process")

		logger_config.success("...all files ready")

	def __validate_video_tokens(self, video_path):
		split_count = -1
		duration = video_duration(video_path) // 60
		# 40 reason a 1M context window can fit slightly less than an hour of video
		if duration > 40:
			import math
			split_count = math.ceil(duration / 40)

		return split_count

	def __get_config(self):
		return types.GenerateContentConfig(
			system_instruction=self.system_instruction,
			temperature=1,
			top_p=0.95,
			top_k=40,
			max_output_tokens=8192,
			response_mime_type=self.response_mime_type,
			response_schema=self.schema,
			tools=self.tools,
			thinking_config=self.thinking_config
		)

	def __send_message_with_timeout(self, user_prompt, config, timeout=300):
		executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
		future = executor.submit(lambda: self.chat.send_message(user_prompt, config))
		try:
			return future.result(timeout=timeout)
		except concurrent.futures.TimeoutError:
			logger_config.error("Request timed out")
			# Not using context manager so we can shut down more aggressively
			executor.shutdown(wait=False)
			return None

	def send_message(self, user_prompt="", file_path=None, system_instruction=None, schema=None, response_mime_type=None):
		if not user_prompt:
			user_prompt = ""

		original_text = user_prompt
		file_paths = [file_path] if file_path else [None]

		if system_instruction:
			self.system_instruction = system_instruction

		if schema:
			self.schema = schema

		if response_mime_type:
			self.response_mime_type=response_mime_type

		if file_path:
			if file_path.endswith((".jpg", ".png", ".jpeg")):
				file_path = compress_image(file_path)
			else:
				file_path = compress_video_util(file_path)
			split_count = self.__validate_video_tokens(file_path)
			if split_count > -1:
				from . import split_video
				file_paths = split_video.split(file_path, parts=split_count)

		index = 0
		unavaiable_retry_done = False
		model_responses = []
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

				if not self.chat or len(file_paths) > 1:
					logger_config.info("Starting a new chat session.")
					self.__initialize_api()
					if len(file_paths) > 1:
						self.__delete_file_paths()

				if len(file_paths) > 1:
					user_prompt = f'{original_text} Part {index+1} of {len(file_paths)}'

				logger_config.debug(f"user_prompt: {user_prompt}")
				uploaded_file = None
				if file:
					uploaded_file = self.__upload_to_gemini(file)
					self.__wait_for_files_active([uploaded_file])

				response = self.__send_message_with_timeout([user_prompt, uploaded_file] if uploaded_file else [user_prompt], self.__get_config())
				result = response.text

				model_responses.append(result)
				logger_config.debug(f"Google AI studio response: {result}")
				index += 1

				if not file or index >= len(file_paths):
					break

			except Exception as e:
				error_message = str(e)
				if "RESOURCE_EXHAUSTED" in error_message:
					logger_config.warning("Quota exceeded, switching API key...")
					self.__initialize_api()
				elif not unavaiable_retry_done and "503 UNAVAILABLE" in error_message:
					unavaiable_retry_done = True
					logger_config.warning("Service unavailable, waiting for 50 seconds before retrying...", seconds=50)
				else:
					raise

		return model_responses

	def get_history(self):
		return self.chat.get_history()

	def get_schema(self):
		return self.schema