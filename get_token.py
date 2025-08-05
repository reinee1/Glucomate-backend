import firebase_admin
from firebase_admin import credentials
import requests

# Firebase project config
api_key = "AIzaSyClr6AWE3geKUE7XsXimWZ30Z_oSc1fKjE"  # Replace this with your Web API Key from Firebase

email = "rhz06@mail.aub.edu"
password = "123123"

def get_id_token(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }

    response = requests.post(url, json=payload)
    if response.status_code == 200:
        id_token = response.json().get("idToken")
        print("✅ ID Token:", id_token)
        return id_token
    else:
        print("❌ Failed to log in:", response.json())

get_id_token(email, password)
