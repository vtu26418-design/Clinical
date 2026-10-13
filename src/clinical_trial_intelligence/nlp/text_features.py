import re

def text_complexity(text: str) -> dict:
    text = text or ""
    words = re.findall(r"\b\w+\b", text)
    sentences = max(1, len(re.findall(r"[.!?]+", text)))
    return {
        "word_count": len(words),
        "sentence_count": sentences,
        "avg_sentence_words": round(len(words) / sentences, 2),
    }
