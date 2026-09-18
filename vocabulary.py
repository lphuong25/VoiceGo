"""Japanese tokenization and JLPT vocabulary lookup using Supabase."""

import os

import fugashi
from supabase import create_client


# --------------------------------------------------
# Supabase
# --------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv(
    "SUPABASE_ANON_KEY",
    os.getenv("SUPABASE_API_KEY", "")
).strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_ANON_KEY must be set in your .env file."
    )

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# --------------------------------------------------
# Japanese helpers
# --------------------------------------------------

def hiragana_char(char: str) -> bool:
    """Return True if char is a hiragana character."""
    if not char:
        return False

    return "\u3040" <= char <= "\u309F"


def tokenize_word(text: str):
    """Extract unique useful Japanese lemmas from a transcript."""

    tagger = fugashi.Tagger()

    raw_tokens = []

    for word in tagger(text):

        # Ignore punctuation
        if word.surface in {
            "、", "。", "！", "？",
            ",", ".", "!", "?"
        }:
            continue

        # Ignore particles, auxiliary verbs, interjections
        if word.feature.pos1 in [
            "助詞",
            "助動詞",
            "感動詞"
        ]:
            continue

        # Fugashi may return None for lemma.
        lemma = word.feature.lemma

        if not lemma or lemma == "*":
            lemma = word.surface

        # Safety check
        if not lemma:
            continue

        raw_tokens.append(lemma)

    # Remove duplicates and useless one-character hiragana
    seen = set()
    tokens = []

    for word in raw_tokens:

        if not word:
            continue

        if len(word) == 1 and hiragana_char(word):
            continue

        if word in seen:
            continue

        seen.add(word)
        tokens.append(word)

    return tokens


# --------------------------------------------------
# Supabase vocabulary lookup
# --------------------------------------------------

def vocabulary_extraction(word_list):
    """
    Match extracted Japanese words against the
    Supabase vocabulary table.
    """

    vocabulary_list = {
        "N5": [],
        "N4": [],
        "N3": [],
        "N2": [],
        "N1": []
    }

    for word in word_list:

        if not word:
            continue

        try:
            # Search by kanji
            result = (
                supabase
                .table("vocabulary")
                .select("kanji, hiragana, english, level")
                .eq("kanji", word)
                .limit(1)
                .execute()
            )

            rows = result.data

            # If no kanji match, search hiragana
            if not rows:
                result = (
                    supabase
                    .table("vocabulary")
                    .select("kanji, hiragana, english, level")
                    .eq("hiragana", word)
                    .limit(1)
                    .execute()
                )

                rows = result.data

            if not rows:
                continue

            entry = rows[0]

            if not isinstance(entry, dict):
                continue

            kanji = entry.get("kanji")
            hiragana = entry.get("hiragana")
            english = entry.get("english")
            level_value = entry.get("level")
            level = level_value.upper() if isinstance(level_value, str) else ""

            if level not in vocabulary_list:
                continue

            vocabulary_list[level].append(
                {
                    "Word": kanji or hiragana or word,
                    "Pronunciation": hiragana or "",
                    "Meaning": english or "",
                }
            )

        except Exception as exc:
            print(
                f"Vocabulary lookup failed for '{word}': {exc}"
            )

    return vocabulary_list

