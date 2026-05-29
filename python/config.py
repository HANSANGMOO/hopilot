# config.py
# Configuration settings for Hopilot Backend

import os

# Example config variable
API_KEY = os.getenv("API_KEY", "")
PORT = int(os.getenv("PORT", 8000))
