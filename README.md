# gemiwrap

**gemiwrap** is a simple wrapper for interacting with Google's Gemini API. It supports file uploads, video compression, and efficient API key management.

## Features
- Easy interaction with Google's Gemini API
- Automatic API key switching on quota exhaustion
- File and video handling with compression and splitting
- Logging support for debugging

## Installation

To install **gemiwrap**, use:
```sh
pip install git+https://github.com/jebin2/gemiwrap.git
```

## Dependencies
This package requires the following dependencies:
- `google-generativeai`
- `pymediainfo`
- `python-dotenv`
- `ffmpeg-python`
- `custom_logger`

## Usage

### Initialize the Wrapper
```python
from gemiwrap import GeminiWrapper

gemini = GeminiWrapper()
gemini.send_message("Hello, Gemini!")
```

### Sending Messages with File Attachments
```python
gemini.send_message("Analyze this video", file_path="path/to/video.mp4")
```

### Video Compression
```python
from gemiwrap.compress_video import compress_video

compressed_path = compress_video("input.mp4", target_size_mb=400, height=480)
```

### Video Splitting
```python
from gemiwrap.split_video import split

split_files = split("input.mp4", parts=3)
```

## Environment Variables
To use API keys, add them to a `.env` file:
```
GEMINI_API_KEYS=your_api_key1,your_api_key2
TEMP_OUTPUT=./temp
```