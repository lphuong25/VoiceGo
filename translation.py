import os
import deepl

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")


def translate(text: str) -> str:
    """Translate Japanese text to US English using DeepL API Free."""
    if not text:
        return ""

    if not DEEPL_API_KEY:
        return "Translation unavailable: DEEPL_API_KEY is not configured."

    translator = deepl.Translator(DEEPL_API_KEY)
    result = translator.translate_text(
        text,
        source_lang="JA",
        target_lang="EN-US",
    )
    return result.text
