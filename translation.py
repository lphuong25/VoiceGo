import deepl
from dotenv import load_dotenv
import os

load_dotenv()
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
translator = deepl.Translator(DEEPL_API_KEY)

def translate(text: str) -> str:
    result = translator.translate_text(text, source_lang='JA', target_lang='EN-US')
    return result.text
