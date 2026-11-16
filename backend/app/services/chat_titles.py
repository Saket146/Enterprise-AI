"""Automatic chat titles, generated from the first question of a conversation."""
import re
from typing import Optional

from app.services.llm_service import llm_service

DEFAULT_TITLE = "New chat"
MAX_TITLE_CHARS = 60

_LEADING_FILLER = re.compile(
    r"^(?:hi|hello|hey|please|kindly|can you|could you|would you|will you|i want to know|i would like to know|"
    r"i'd like to know|i need to know|tell me about|tell me|show me|give me|let me know|find out|find|"
    r"what is|what's|what are|who is|who's|who are|list|explain|describe)\b[\s,:-]*",
    re.IGNORECASE,
)
_SMALL_WORDS = {"a", "an", "and", "are", "as", "at", "by", "do", "for", "in", "is", "of", "on", "or", "the", "to", "we", "with", "per"}


def is_default_title(title: Optional[str]) -> bool:
    return not title or title.strip().lower() in {"", DEFAULT_TITLE.lower(), "new session", "untitled", "t"}


def clean_title(title: str) -> str:
    """Normalise a title typed by a user or produced by a model."""
    text = re.sub(r"\s+", " ", (title or "").replace("\n", " ")).strip().strip("\"'`*#.").strip()
    if len(text) > MAX_TITLE_CHARS:
        text = text[:MAX_TITLE_CHARS].rsplit(" ", 1)[0].rstrip(",;:-") + "..."
    return text


def _heuristic_title(message: str) -> str:
    text = re.sub(r"\s+", " ", message or "").strip()
    first_sentence = re.split(r"(?<=[.?!])\s", text, maxsplit=1)[0].rstrip("?.! ")
    stripped = first_sentence
    for _ in range(3):  # "please can you tell me about ..." has several fillers in a row
        shorter = _LEADING_FILLER.sub("", stripped, count=1)
        if shorter == stripped:
            break
        stripped = shorter
    stripped = re.sub(r"^(?:the|a|an)\s+", "", stripped, flags=re.IGNORECASE)
    # Keep the original wording when stripping leaves too little to be a title
    candidate = stripped if len(stripped.split()) >= 2 else first_sentence
    words = candidate.split()[:7]
    while len(words) > 2 and words[-1].lower() in _SMALL_WORDS | {"how", "what", "that", "which", "it", "has"}:
        words.pop()                                   # do not end on a dangling connector
    titled = []
    for idx, word in enumerate(words):
        if word.isupper() or any(ch.isdigit() for ch in word) or (word[:1].isupper() and idx > 0):
            titled.append(word)                       # acronyms, codes and names stay as typed
        elif idx > 0 and word.lower() in _SMALL_WORDS:
            titled.append(word.lower())
        else:
            titled.append(word[:1].upper() + word[1:])
    return clean_title(" ".join(titled)) or DEFAULT_TITLE


def generate_title(message: str) -> str:
    """A short title for a chat that starts with `message`."""
    if llm_service.has_model:
        prompt = (
            "Write a short title (3 to 6 words, no quotes, no trailing punctuation) for a conversation "
            f"that starts with this question:\n\n{(message or '')[:500]}\n\nTitle:"
        )
        suggestion = llm_service.generate(prompt, max_tokens=20, strict=True)
        if suggestion:
            title = clean_title(suggestion.splitlines()[0])
            if 2 <= len(title) <= MAX_TITLE_CHARS + 3:
                return title
    return _heuristic_title(message)
