import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
DB_NAME = "asksafe"

# World ID verification
WORLD_APP_ID = os.getenv("WORLD_APP_ID", "")
WORLD_ACTION = os.getenv("WORLD_ACTION", "verify-human")
WORLD_RP_ID = os.getenv("WORLD_RP_ID", "")
WORLD_RP_SIGNING_KEY = os.getenv("WORLD_RP_SIGNING_KEY", "")

# Resend email
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
