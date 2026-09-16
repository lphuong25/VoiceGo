import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from transcription import transcribe_audio
from translation import translate
from vocabulary import tokenize_word, vocabulary_extraction
from userdata import save_user_data, get_user_data

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
MAX_AUDIO_SIZE = 25 * 1024 * 1024  # Groq free-tier upload limit

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

app = FastAPI(title="VoiceGo", version="1.0.0")

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def verify_token(authorization: str = Header(...)) -> dict:
    """Verify a Supabase access token and return the user's UUID."""
    try:
        scheme, token = authorization.split(maxsplit=1)
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authentication scheme")

        response = requests.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}",
            },
            timeout=10,
        )
        if response.status_code != 200:
            raise ValueError("Supabase rejected the access token")

        user = response.json()
        return {"user_id": user["id"], "token": token}
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "SUPABASE_URL": SUPABASE_URL,
            "SUPABASE_ANON_KEY": SUPABASE_ANON_KEY,
        },
    )


@app.get("/health")
def health():
    """Simple health check for Render and local deployment."""
    return {"status": "ok"}


@app.post("/uploads")
async def upload_audio(
    file: UploadFile = File(...),
    auth: dict = Depends(verify_token),
):
    del auth  # Authentication is required; results are not persisted here.

    allowed_types = {
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/mp4",
        "audio/x-m4a",
        "audio/ogg",
        "audio/webm",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Unsupported audio format. Use MP3, WAV, M4A, OGG, or WEBM.",
        )

    audio_bytes = await file.read()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Audio file is too large. Please keep it under 25 MB.",
        )

    try:
        transcription = transcribe_audio(
            audio_bytes,
            file.filename or "audio.mp3",
            language="ja",
        )
        translation = translate(transcription)
        tokenized_words = tokenize_word(transcription)
        vocabulary_list = vocabulary_extraction(tokenized_words)

        return {
            "filename": file.filename,
            "transcription": transcription,
            "translation": translation,
            "vocabulary_list": vocabulary_list,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Audio processing failed: {exc}",
        ) from exc


@app.get("/flashcard")
def flashcard(request: Request):
    return templates.TemplateResponse(
        "flashcard.html",
        {"request": request},
    )


class UserDataModel(BaseModel):
    user_id: str
    transcription: str
    translation: str
    vocabulary_list: dict[str, list[dict[str, Any]]]


@app.post("/save_user_data")
async def save_user_data_endpoint(
    user_data: UserDataModel,
    auth: dict = Depends(verify_token),
):
    if auth["user_id"] != user_data.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized user")

    try:
        await save_user_data(
            user_data.user_id,
            user_data.transcription,
            user_data.translation,
            user_data.vocabulary_list,
            access_token=auth["token"],
        )
        return {"message": "User data saved successfully"}
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to save user data: {exc}",
        ) from exc


@app.get("/get_user_data/{user_id}")
async def get_user_data_endpoint(
    user_id: str,
    auth: dict = Depends(verify_token),
):
    if user_id != auth["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized user")

    try:
        user_data = await get_user_data(user_id, access_token=auth["token"])
        return {"user_data": user_data}
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to get user data: {exc}",
        ) from exc
