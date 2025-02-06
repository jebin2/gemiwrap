from setuptools import setup, find_packages

setup(
	name="gemini_uploader",
	version="0.1.0",
	packages=find_packages(exclude=["tests*"]),
	install_requires=[
		"google-generativeai",
		"MediaInfo",
		"python-dotenv",
		"custom_logger @ git+https://github.com/jebin2/custom_logger",
		"ffmpeg"
	],
	author="Your Name",
	author_email="your.email@example.com",
	description="A tool for uploading files and interacting with Google's Gemini API.",
	long_description=open("README.md").read(),
	long_description_content_type="text/markdown",
	url="https://github.com/yourusername/gemini_uploader",  # Your repo URL
	classifiers=[
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: MIT License",  # Choose a license
		"Operating System :: OS Independent",
	],
	python_requires=">=3.7",  # Specify minimum Python version
)