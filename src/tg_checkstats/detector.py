"""Detection rules for check events."""

from __future__ import annotations

import re
from typing import List

K_TOKEN_REGEX = re.compile(
    r"(?<!\w)([1-9]|1[0-9]|20)\s*[kK](?=$|[\s\.,!?;:\)\]\}\'\"-])"
)
KEYWORDS = ["Kontrollettis", "Kontrolleure", "Kontis"]
KEYWORD_REGEXES = [re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE) for word in KEYWORDS]


def find_k_tokens(text: str) -> List[int]:
    """Return a list of matched k-token integers in the order they appear."""
    matches = []
    for match in K_TOKEN_REGEX.finditer(text):
        value = int(match.group(1))
        if 1 <= value <= 20:
            matches.append(value)
    return matches


def find_keywords(text: str) -> List[str]:
    """Return a list of matched canonical keywords (case-insensitive)."""
    found = []
    for keyword, regex in zip(KEYWORDS, KEYWORD_REGEXES):
        if regex.search(text):
            found.append(keyword)
    return found


def detect_event(search_text: str) -> dict:
    """Detect a check event and return match metadata."""
    k_values = find_k_tokens(search_text)
    keywords = find_keywords(search_text)

    has_k = bool(k_values)
    has_kw = bool(keywords)
    if has_k and has_kw:
        match_type = "both"
    elif has_k:
        match_type = "k_token"
    elif has_kw:
        match_type = "keyword"
    else:
        match_type = "none"

    return {
        "match_type": match_type,
        "matched_k_values": sorted(set(k_values)),
        "matched_k_values_all": k_values,
        "k_token_hit_count": len(k_values),
        "matched_keywords": keywords,
    }
