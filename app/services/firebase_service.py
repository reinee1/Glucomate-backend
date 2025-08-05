import firebase_admin
from firebase_admin import credentials, auth
import os

# Load credentials path from .env
cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "firebase/firebase-adminsdk.json")

# Initialize Firebase Admin only once
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    print("✅ Firebase Admin initialized successfully.")

# Token verification function
def verify_id_token(token):
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception:
        return None
