"""Japanese tokenization and JLPT vocabulary lookup.

Uses the bundled SQLite vocabulary database, which is faster, 
cheaper, and easier to deploy. Supabase is still used for 
authentication and saved user data.
"""

import sqlite3
from pathlib import Path
import fugashi

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "JLPTVocabulary.db"

TAGGER = fugashi.Tagger()
PUNCTUATION = {"、", "。", "！", "？", "!", "?", "「", "」", "『", "』", ",", "."}
SKIP_POS = {"助詞", "助動詞", "感動詞"}


def hiragana_char(char: str) -> bool:
    return "\u3040" <= char <= "\u309f"


def tokenize_word(text: str) -> list[str]:
    raw_tokens = []

    for word in TAGGER(text):
        if word.surface in PUNCTUATION:
            continue
        if word.feature.pos1 in SKIP_POS:
            continue

        lemma = word.feature.lemma if word.feature.lemma != "*" else word.surface
        if len(lemma) == 1 and hiragana_char(lemma):
            continue

        raw_tokens.append(lemma)

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(raw_tokens))


def vocabulary_extraction(word_list: list[str]) -> dict:
    vocabulary_list = {level: [] for level in ("N5", "N4", "N3", "N2", "N1")}

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Vocabulary database not found: {DB_PATH}")

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()

        for word in word_list:
            cursor.execute(
                """
                SELECT Kanji, Hiragana, English, level
                FROM JLPTVocabulary
                WHERE Kanji = ? OR Hiragana = ?
                LIMIT 1
                """,
                (word, word),
            )
            result = cursor.fetchone()

            if not result:
                continue

            level = (result["level"] or "").upper()
            if level not in vocabulary_list:
                continue

            kanji = result["Kanji"] or ""
            hiragana = result["Hiragana"] or ""
            english = result["English"] or ""

            vocabulary_list[level].append(
                {
                    "Word": kanji if kanji else hiragana,
                    "Pronunciation": hiragana,
                    "Meaning": english,
                }
            )
    finally:
        connection.close()

    return vocabulary_list
