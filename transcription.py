import os
from groq import Groq

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3-turbo")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not configured.")

client = Groq(api_key=GROQ_API_KEY)


def transcribe_audio(file_bytes: bytes, filename: str, language: str = "ja") -> str:
    """Transcribe Japanese audio using Groq-hosted Whisper."""
    result = client.audio.transcriptions.create(
        file=(filename, file_bytes),
        model=MODEL,
        language=language,
        response_format="json",
        temperature=0.0,
    )
    return result.text.strip()
