"""Speech-to-text using Groq-hosted Whisper."""

import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3-turbo")


def transcribe_audio(file_bytes: bytes, filename: str, language: str = "ja") -> str:
    """Transcribe an audio file without loading a Whisper model locally."""
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=GROQ_API_KEY)
    result = client.audio.transcriptions.create(
        file=(filename, file_bytes),
        model=MODEL,
        language=language,
        response_format="json",
        temperature=0.0,
    )
    return result.text.strip()
