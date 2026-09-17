"""VoiceGo FastAPI application."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

load_dotenv()

from transcription import transcribe_audio
from translation import translate
from vocabulary import tokenize_word, vocabulary_extraction
from userdata import save_user_data, get_user_data


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".webm", ".mp4", ".mpeg", ".mpga"}

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", os.getenv("SUPABASE_API_KEY", ""))
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "").strip()

app = FastAPI(title="VoiceGo", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "SUPABASE_URL": SUPABASE_URL,
            "SUPABASE_ANON_KEY": SUPABASE_ANON_KEY,
            "supabase_configured": bool(SUPABASE_URL and SUPABASE_ANON_KEY),
        },
    )


@app.post("/uploads")
async def upload_audio(file: UploadFile = File(...)):
    """Process audio in guest mode; no account is required."""

    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported audio format. "
                "Use MP3, WAV, M4A, WEBM, or another supported format."
            ),
        )

    file_bytes = await file.read()

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Audio file must be 25 MB or smaller."
        )

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded audio file is empty."
        )

    try:
        transcription = transcribe_audio(
            file_bytes,
            file.filename or "audio.mp3"
        )

        translation = translate(transcription)

        tokenized_words = tokenize_word(transcription)

        print("Tokenized words:", tokenized_words)

        vocabulary_list = vocabulary_extraction(
            tokenized_words
        )

        print("Vocabulary:", vocabulary_list)

        return {
            "filename": file.filename,
            "transcription": transcription,
            "translation": translation,
            "vocabulary_list": vocabulary_list,
            "word_count": sum(
                len(words)
                for words in vocabulary_list.values()
            ),
        }

    except Exception as e:
        import traceback

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@app.get("/flashcard")
def flashcard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="flashcard.html",
        context={"request": request},
    )


# ----------------------------
# Optional account-backed history
# ----------------------------
class UserDataModel(BaseModel):
    user_id: str
    transcription: str
    translation: str
    vocabulary_list: Dict[str, List[Dict[str, Any]]]


def optional_user_id(authorization: Optional[str] = Header(default=None)):
    """Return the Supabase user ID when a valid bearer token is supplied."""
    if not authorization or not SUPABASE_JWT_SECRET:
        return None

    try:
        scheme, token = authorization.split(maxsplit=1)
        if scheme.lower() != "bearer":
            return None
        decoded = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"])
        return decoded.get("sub")
    except Exception:
        return None


@app.post("/save_user_data")
async def save_user_data_endpoint(
    user_data: UserDataModel,
    token_user_id: Optional[str] = Depends(optional_user_id),
):
    if not token_user_id:
        return {"saved": False, "message": "Sign in to save your learning history."}

    if token_user_id != user_data.user_id:
        raise HTTPException(status_code=403, detail="Unauthorized user")

    try:
        await save_user_data(
            user_data.user_id,
            user_data.transcription,
            user_data.translation,
            user_data.vocabulary_list,
        )
        return {"saved": True, "message": "Learning session saved."}
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"saved": False, "error": f"Failed to save user data: {str(exc)}"},
        )


@app.get("/get_user_data/{user_id}")
async def get_user_data_endpoint(
    user_id: str,
    token_user_id: Optional[str] = Depends(optional_user_id),
):
    if not token_user_id:
        raise HTTPException(status_code=401, detail="Sign in to view saved history.")
    if user_id != token_user_id:
        raise HTTPException(status_code=403, detail="Unauthorized user")

    try:
        return {"user_data": await get_user_data(user_id)}
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get user data: {str(exc)}"},
        )
