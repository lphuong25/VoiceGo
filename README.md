

# VoiceGo 🎙️

**VoiceGo is a Japanese audio learning tool that turns spoken Japanese into study material.**

Upload a short Japanese audio clip and VoiceGo:

1. Transcribes the audio with **OpenAI Whisper Large V3 Turbo through Groq**
2. Translates the Japanese transcript into English with **DeepL API Free**
3. Tokenizes the Japanese text with **fugashi**
4. Matches words against a bundled **JLPT vocabulary SQLite database**
5. Groups vocabulary by **JLPT N5–N1**
6. Lets the user review the extracted words as **interactive flashcards**
7. Allows authenticated users to save analysis results with **Supabase**

This project is intentionally lightweight: the web server does **not** download or run Whisper locally. That keeps deployment practical on free hosting.

## Architecture

```text
                         ┌──────────────────────┐
                         │      VoiceGo UI      │
                         │   HTML / CSS / JS    │
                         └──────────┬───────────┘
                                    │
                              FastAPI backend
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
             ▼                      ▼                      ▼
      Groq Whisper             DeepL API             Local SQLite
   Japanese transcription    Japanese → English      JLPT vocabulary
             │                      │                      │
             └──────────────────────┼──────────────────────┘
                                    ▼
                            Results / Flashcards
                                    │
                                    ▼
                              Supabase Auth
                            + saved_data table
```

### Why Whisper is not inside Supabase

Supabase is being used as the application's **database and authentication layer**. A database service is not intended to host a Python Whisper model.

The updated version sends the uploaded audio directly from the FastAPI server to Groq's hosted Whisper endpoint. This removes the large local model and makes the backend small enough for a free web host.

Groq currently provides `whisper-large-v3-turbo`, a multilingual Whisper model with direct audio uploads. The speech-to-text endpoint accepts common formats such as MP3, WAV, M4A, OGG, and WEBM. The application limits uploads to 25 MB to stay within the free-tier upload limit. See the [Groq Speech-to-Text documentation](https://console.groq.com/docs/speech-to-text).

## Main technologies

| Area | Technology |
|---|---|
| Backend | Python, FastAPI |
| Speech recognition | Groq API + Whisper Large V3 Turbo |
| Translation | DeepL API Free |
| Japanese NLP | fugashi |
| Vocabulary data | SQLite + JLPT vocabulary dataset |
| Authentication | Supabase Auth |
| User data | Supabase PostgreSQL |
| Frontend | HTML, CSS, JavaScript |
| Deployment | Render Free Web Service |
| Testing / development | Python + Uvicorn |

## Project structure

```text
VoiceGo/
├── main.py                  # FastAPI application and API routes
├── transcription.py         # Groq Whisper integration
├── translation.py           # DeepL translation
├── vocabulary.py            # Japanese tokenization + JLPT lookup
├── userdata.py              # Supabase saved-data operations
├── JLPTVocabulary.db        # Bundled JLPT vocabulary database
├── requirements.txt
├── render.yaml              # Render deployment configuration
├── .env.example
├── supabase/
│   └── schema.sql           # Saved-data table + RLS policies
├── templates/
│   ├── index.html           # Login + audio analysis
│   └── flashcard.html       # Vocabulary flashcards
└── static/
    └── style.css
```

## Run locally

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/VoiceGo.git
cd VoiceGo
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create environment variables

Copy `.env.example` to `.env`:

```text
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
GROQ_API_KEY=...
DEEPL_API_KEY=...
WHISPER_MODEL=whisper-large-v3-turbo
```

Do **not** commit `.env`.

### 5. Configure Supabase

Create a Supabase project and enable email/password authentication.

Then open the Supabase SQL Editor and run:

```text
supabase/schema.sql
```

The table uses Row Level Security so a signed-in user can only read and insert their own saved results.

### 6. Start VoiceGo

```bash
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

Health check:

```text
http://127.0.0.1:8000/health
```

## Free deployment

### Recommended setup for a resume demo

Use:

- **Render Free** for the FastAPI web application
- **Groq** for hosted Whisper transcription
- **Supabase Free** for authentication and saved results
- **DeepL API Free** for translation

This avoids paying for a GPU or trying to fit a Whisper model into a tiny free server.

Render's free web service has limited CPU/RAM and sleeps after inactivity, so the first request after a period of inactivity can be slow. That is acceptable for a portfolio demonstration.

Render deployment:

1. Push this repository to GitHub.
2. Create a new **Web Service** in Render.
3. Connect the GitHub repository.
4. Select the **Free** plan.
5. Use:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add the environment variables from `.env`.
7. Deploy.

`render.yaml` is included as a reference configuration.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Web application |
| GET | `/health` | Deployment health check |
| POST | `/uploads` | Transcribe and analyze Japanese audio |
| GET | `/flashcard` | Vocabulary flashcards |
| POST | `/save_user_data` | Save an analysis for the signed-in user |
| GET | `/get_user_data/{user_id}` | Retrieve the user's saved analyses |

## Design decisions

### Hosted Whisper instead of local Whisper

The original version loaded:

```python
whisper.load_model("base")
```

inside the web server. This made deployment difficult because the model and its runtime dependencies require substantially more resources than a small free web service provides.

The updated project keeps the same user-facing feature while moving inference to a hosted Whisper endpoint.

### Local vocabulary database instead of one API request per word

The original version queried Supabase separately for every extracted word.

The updated version uses the included `JLPTVocabulary.db` SQLite database. This:

- removes many network requests
- makes vocabulary extraction faster
- reduces Supabase usage
- makes the project easier to reproduce
- keeps the vocabulary dataset available even if Supabase is temporarily unavailable

Supabase is still used where it adds real value: authentication and user-specific saved data.

### No permanent audio storage

VoiceGo sends audio to the transcription service for processing and does not need to keep uploaded recordings on the server.

This also avoids depending on the ephemeral filesystem of free hosting.

## Limitations

- Audio uploads are limited to 25 MB.
- Free hosted services can have cold starts.
- Groq and DeepL API usage is subject to their current free-tier limits.
- JLPT vocabulary coverage depends on the bundled dataset.
- JLPT levels are used as a learning aid; they should not be treated as an official proficiency assessment.
- Japanese speech containing names, slang, dialects, or heavy background noise may produce transcription errors.


## License

MIT License. See `LICENSE` if included in the repository.
