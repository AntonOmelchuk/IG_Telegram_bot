import os
import json
import base64
import firebase_admin
from firebase_admin import credentials
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# FIREBASE INITIALIZATION
FIREBASE_BASE64 = os.getenv("FIREBASE_SERVICE_ACCOUNT_BASE64")
if FIREBASE_BASE64:
    decoded_json = base64.b64decode(FIREBASE_BASE64).decode("utf-8")
    cred_dict = json.loads(decoded_json)
    cred = credentials.Certificate(cred_dict)
else:
    cred = credentials.Certificate("./serviceAccountKey.json")

firebase_admin.initialize_app(cred, {
    "databaseURL": DATABASE_URL
})

# DATABASE PATHS
MEMBERS_PATH = "iron_gates_members"
EVENTS_PATH = "regroups/events"
ALLY_IMAGE_PATH = "images/ally"
USERS_PATH = "telegram_users"

# EMOJIS
EVENT_EMOJIS = {
    "siege": "🏰", "ch": "🛡️", "mtb": "⚔️", "ctb": "🚩",
    "ebc": "🐲", "dm": "☠️", "qa": "🐜", "core": "⚙️",
    "orfen": "🕸️", "zaken": "🏴‍☠️", "tezza": "🎻",
    "baium": "👑", "antharas": "🐉", "valakas": "🔥"
}
