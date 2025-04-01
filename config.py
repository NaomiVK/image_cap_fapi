import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# API endpoints
LM_STUDIO_API_URL = "http://localhost:1234/v1/chat/completions"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Application settings
HOST = "0.0.0.0"
PORT = 8000
DEBUG = True

# Check if required environment variables are set
def check_env_vars():
    missing_vars = []
    
    if not OPENROUTER_API_KEY:
        missing_vars.append("OPENROUTER_API_KEY")
    
    if missing_vars:
        print(f"Warning: The following environment variables are missing: {', '.join(missing_vars)}")
        print("Some functionality may not work correctly.")
        print("Please create a .env file with these variables or set them in your environment.")
    
    return len(missing_vars) == 0

# Call this function when importing the module
check_env_vars()