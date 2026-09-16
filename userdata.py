import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")


def _headers(access_token: str) -> dict:
    """Use the signed-in user's token so Supabase RLS can enforce ownership."""
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


async def save_user_data(
    user_id,
    transcription,
    translation,
    vocabulary_list,
    access_token,
):
    url = f"{SUPABASE_URL}/rest/v1/saved_data"
    payload = {
        "user_id": user_id,
        "transcription": transcription,
        "translation": translation,
        "vocabulary_list": vocabulary_list,
    }

    response = requests.post(
        url,
        json=payload,
        headers=_headers(access_token),
        timeout=15,
    )

    if response.status_code not in (200, 201):
        raise Exception(f"Supabase insert error: {response.text}")

    return response.json()


async def get_user_data(user_id, access_token):
    url = (
        f"{SUPABASE_URL}/rest/v1/saved_data"
        f"?user_id=eq.{user_id}&order=created_at.desc"
    )

    response = requests.get(
        url,
        headers=_headers(access_token),
        timeout=15,
    )

    if response.status_code != 200:
        raise Exception(f"Supabase fetch error: {response.text}")

    return response.json()
