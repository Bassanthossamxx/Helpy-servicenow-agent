import os

from dotenv import load_dotenv

load_dotenv()

SERVICENOW_INSTANCE_URL = os.getenv("SERVICENOW_INSTANCE_URL", "").rstrip("/")
SERVICENOW_USERNAME = os.getenv("SERVICENOW_USERNAME")
SERVICENOW_PASSWORD = os.getenv("SERVICENOW_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not all([SERVICENOW_INSTANCE_URL, SERVICENOW_USERNAME, SERVICENOW_PASSWORD, GEMINI_API_KEY]):
    raise RuntimeError("Missing env variables. Copy .env.example to .env and fill it in")