"""Small Supabase REST helper for optional authenticated history."""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_API_KEY = os.getenv("SUPABASE_ANON_KEY", os.getenv("SUPABASE_API_KEY", ""))


def _headers():
    return {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json",
    }


async def save_user_data(user_id, transcription, translation, vocabulary_list):
    if not SUPABASE_URL or not SUPABASE_API_KEY:
        raise RuntimeError("Supabase is not configured.")

    url = f"{SUPABASE_URL}/rest/v1/saved_data"
    payload = {
        "user_id": user_id,
        "transcription": transcription,
        "translation": translation,
        "vocabulary_list": vocabulary_list,
    }
    response = requests.post(url, json=payload, headers=_headers(), timeout=15)
    if response.status_code not in (200, 201):
        raise RuntimeError(f"Supabase insert error: {response.text}")
    return response.json()


async def get_user_data(user_id):
    if not SUPABASE_URL or not SUPABASE_API_KEY:
        raise RuntimeError("Supabase is not configured.")

    url = f"{SUPABASE_URL}/rest/v1/saved_data?user_id=eq.{user_id}&order=created_at.desc"
    response = requests.get(url, headers=_headers(), timeout=15)
    if response.status_code != 200:
        raise RuntimeError(f"Supabase fetch error: {response.text}")
    return response.json()
