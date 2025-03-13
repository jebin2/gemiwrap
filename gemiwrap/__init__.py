from .main import GeminiWrapper

import os
if os.path.exists(".env"):
    from dotenv import load_dotenv
    load_dotenv()