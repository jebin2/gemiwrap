from gemiwrap import GeminiWrapper

geminiWrapper = GeminiWrapper()
geminiWrapper.send_message("Tell me about LLM in short")

history = geminiWrapper.get_history()

geminiWrapper = GeminiWrapper(history=history)
geminiWrapper.send_message("send me the exact previous user message that i sent to you.")

geminiWrapper = GeminiWrapper(delete_files=True)
geminiWrapper.send_message("Describe this image", file_path="tempOutput/P00010.jpg")

geminiWrapper = GeminiWrapper(delete_files=True)
geminiWrapper.send_message("Describe this Video", file_path="tempOutput/dragon_ball_z_-_001.mp4")