"""Detection and extraction rules for check events.

This module started as a minimal "k-token or keyword" detector. Real-world
messages contain more forms (ranges, keyword inflections, follow-up messages
with direction-only details, etc.). The current detector keeps backward
compatibility fields for existing CSV outputs while adding richer extraction
metadata used by newer analysis steps (e.g., stitching).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from tg_checkstats.line_universe import guess_mode, is_valid_line_id, normalize_line_id

# --- K-count extraction ----------------------------------------------------
#
# Supports:
# - exact: "3k", "3 K", "4K", "3k."
# - range: "3-5k", "3-5 k", "4/5 k"
#
# We keep the same trailing delimiter contract as the original v1 regex to
# avoid "2k€", "2k/m", "2kB", etc.
_K_NUM = r"([1-9]|1[0-9]|20)"
_K_DELIM = r"(?=$|[\s\.,!?;:\)\]\}\'\"-])"
K_TOKEN_REGEX = re.compile(
    rf"(?<!\w)(?:(?P<a>{_K_NUM})\s*[-/]\s*(?P<b>{_K_NUM})|(?P<n>{_K_NUM}))\s*[kK]{_K_DELIM}"
)

MULTIPLE_K_REGEX = re.compile(
    r"(?i)\b(?:mehrere|ein\s+paar|ein\s+haufen|haufen)\s*(?:k|ks|k's)\b"
)

APPROX_COUNT_WITH_UNIT_REGEX = re.compile(
    r"(?i)\b(?P<n>\d{1,2})\s*(?:stück|leute|kontrolleure?n?|kontrollettis|kontis|uniform(?:iert)?|uni|zivi|zivil)\b"
)

def _extract_primary_k_info(text: str, *, line_id: str | None) -> Tuple[Optional[int], Optional[int], str]:
    """Extract a primary k-count summary (k_min/k_max/qualifier) from text."""
    numeric_bounds: List[Tuple[int, int, str]] = []

    for match in K_TOKEN_REGEX.finditer(text):
        if match.group("n"):
            n = int(match.group("n"))
            numeric_bounds.append((n, n, "exact"))
        else:
            a = int(match.group("a"))
            b = int(match.group("b"))
            numeric_bounds.append((min(a, b), max(a, b), "range"))

    if numeric_bounds:
        # Prefer the first range if present; otherwise first numeric mention.
        for k_min, k_max, qualifier in numeric_bounds:
            if qualifier == "range":
                return k_min, k_max, qualifier
        k_min, k_max, qualifier = numeric_bounds[0]
        return k_min, k_max, qualifier

    if MULTIPLE_K_REGEX.search(text):
        return None, None, "multiple"

    # Approximate numeric counts without "k" can be ambiguous. Only use them
    # when there's enough transit context (line/direction/location) and the
    # number is unlikely to be the line itself.
    approx_match = APPROX_COUNT_WITH_UNIT_REGEX.search(text)
    if approx_match:
        n = int(approx_match.group("n"))
        return n, n, "approx"

    # Heuristic: leading count + "in der <line>" (e.g., "3 in der 10 ...")
    if line_id is not None:
        try:
            line_num = int(re.sub(r"\D", "", line_id) or "0")
        except ValueError:
            line_num = 0
        m = re.search(r"(?i)^\s*(?P<n>\d{1,2})\b(?=.*\b(?:in\s+der|linie|tram|bus|sev)\s+\d{1,3}\b)", text)
        if m:
            n = int(m.group("n"))
            if n != line_num:
                return n, n, "approx"

    return None, None, "unknown"


# --- Control keyword extraction --------------------------------------------

# Canonical keyword list retained for backward-compatible CSV column.
KEYWORDS = ["Kontrollettis", "Kontrolleure", "Kontis", "Kontrolle"]

CONTROL_KEYWORD_REGEX = re.compile(
    r"(?i)\b("
    r"kontrollettis"
    r"|kontis"
    r"|kontrolleur(?:\*innen|innen|e?n)?"
    r"|kontrolle(?:n)?"
    r")\b"
)

# Backwards-compat matching for canonical keywords.
KEYWORD_REGEXES = [re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE) for word in KEYWORDS]


def find_k_tokens(text: str) -> List[int]:
    """Return a list of matched k-token integers in the order they appear.

    Kept for compatibility with earlier tests/outputs.

    Range forms contribute both endpoints in encounter order (e.g., "3-5k" → [3, 5]).
    """
    return _find_k_tokens_impl(text)


def _find_k_tokens_impl(text: str) -> List[int]:
    """Internal implementation for k-token extraction."""
    matches: List[int] = []
    for match in K_TOKEN_REGEX.finditer(text):
        if match.group("n"):
            matches.append(int(match.group("n")))
        else:
            matches.append(int(match.group("a")))
            matches.append(int(match.group("b")))
    return matches


def find_keywords(text: str) -> List[str]:
    """Return a list of matched canonical keywords (case-insensitive).

    Note: This is intentionally conservative (word-boundary matching) to avoid
    matching generic compounds like "Fahrradkontrollen".
    """
    found: List[str] = []
    for keyword, regex in zip(KEYWORDS, KEYWORD_REGEXES):
        if regex.search(text):
            found.append(keyword)
    return found


def _extract_control_keyword_forms(text: str) -> List[str]:
    """Return the matched control keyword surface forms in encounter order."""
    return [m.group(0) for m in CONTROL_KEYWORD_REGEX.finditer(text)]


# --- Line/direction/location extraction ------------------------------------

LINE_EXPLICIT_REGEX = re.compile(
    r"(?i)\b(?P<label>linie|tram|straßenbahn|str|bus|sev)\s*(?P<line>[0-9]{1,3}[a-zA-Z]?|N[0-9]{1,2}|NXL)\b"
)
LINE_IN_DER_REGEX = re.compile(r"(?i)\b(?:in\s+der|in)\s+(?P<line>\d{1,3}[a-zA-Z]?)\b")

_BARE_LINE_CONTEXT = re.compile(
    r"(?i)\b(?:richtung|hbf|haltestelle|steigen|bahn|tram|bus|linie|sev|stadteinwärts|stadtauswärts|innenstadt|stadtwärts)\b"
)
BARE_LINE_REGEX = re.compile(r"\b(?P<line>\d{1,3}[A-Z]?)\b")

DIRECTION_PHRASE_REGEX = re.compile(
    r"(?i)\b(?:richtung|ri\.?|fahrtrichtung|rt)\s*[:\-–]?\s*(?P<dir>[^\n\.,;]+)"
)
DIRECTION_POLARITY_REGEX = re.compile(
    r"(?i)\b(stadteinwärts|stadtauswärts|innenstadt|stadtwärts|stadtausw)\b"
)

LOCATION_REGEX = re.compile(
    r"(?i)\b(?:am|bei|an\s+der|haltestelle|hbf)\s+(?P<loc>[^\n\.,;]+)"
)
PLATFORM_REGEX = re.compile(r"(?i)\b(?P<kind>steig|gleis)\s*(?P<p>[a-z0-9]+)\b")


def _extract_line(text: str) -> Tuple[str | None, str, bool, str]:
    """Extract (line_id, mode_guess, line_validated, line_confidence) from text."""
    explicit = LINE_EXPLICIT_REGEX.search(text)
    if explicit:
        label = explicit.group("label").lower()
        raw_line = explicit.group("line")
        line_id = normalize_line_id(raw_line)
        explicit_mode = "sev" if label == "sev" else ("bus" if label == "bus" else "tram")
        return line_id, guess_mode(line_id, explicit_mode=explicit_mode), is_valid_line_id(line_id), "explicit"

    inferred = LINE_IN_DER_REGEX.search(text)
    if inferred:
        line_id = normalize_line_id(inferred.group("line"))
        if is_valid_line_id(line_id):
            return line_id, guess_mode(line_id), True, "inferred"
        return None, "unknown", False, "none"

    # Bare tokens only if there is other transit context.
    if not _BARE_LINE_CONTEXT.search(text):
        return None, "unknown", False, "none"
    for m in BARE_LINE_REGEX.finditer(text):
        line_id = normalize_line_id(m.group("line"))
        if is_valid_line_id(line_id):
            return line_id, guess_mode(line_id), True, "inferred"
    return None, "unknown", False, "none"


def _extract_direction(text: str) -> Tuple[str | None, str]:
    """Extract (direction_text, direction_polarity) from text."""
    polarity = "unknown"
    pol = DIRECTION_POLARITY_REGEX.search(text)
    if pol:
        token = pol.group(1).lower()
        if token in {"stadteinwärts", "innenstadt", "stadtwärts"}:
            polarity = "inbound"
        elif token in {"stadtauswärts", "stadtausw"}:
            polarity = "outbound"

    direction_text: str | None = None
    m = DIRECTION_PHRASE_REGEX.search(text)
    if m:
        direction_text = m.group("dir").strip()
    elif pol:
        direction_text = pol.group(1).strip()
    return direction_text, polarity


def _extract_location_and_platform(text: str) -> Tuple[str | None, str | None]:
    """Extract (location_text, platform_text) from text."""
    location_text: str | None = None
    m = LOCATION_REGEX.search(text)
    if m:
        location_text = m.group("loc").strip()
    platform_text: str | None = None
    p = PLATFORM_REGEX.search(text)
    if p:
        kind = p.group("kind").strip().capitalize()
        platform_text = f"{kind} {p.group('p').strip()}".strip()
    return location_text, platform_text


def detect_event(search_text: str) -> dict:
    """Detect a check event and return match + extraction metadata.

    The return payload contains backward-compatible keys used by the analyzer
    (match_type, matched_k_values, matched_keywords, k_token_hit_count), plus
    richer fields useful for downstream parsing/stitching.
    """
    line_id, mode_guess_value, line_validated, line_confidence = _extract_line(search_text)
    direction_text, direction_polarity = _extract_direction(search_text)
    location_text, platform_text = _extract_location_and_platform(search_text)

    k_values_all = _find_k_tokens_impl(search_text)
    k_min, k_max, k_qualifier = _extract_primary_k_info(search_text, line_id=line_id)
    has_k = bool(k_values_all) or (k_qualifier in {"multiple", "approx"})

    control_forms = _extract_control_keyword_forms(search_text)
    keywords = find_keywords(search_text)
    has_kw = bool(control_forms) or bool(keywords)

    # Confidence scoring (deterministic).
    score = 0
    if has_k:
        score += 3
    if control_forms:
        # Treat explicit inspector nouns as strong; generic "Kontrolle(n)" as weaker.
        strong = any("kontrolleur" in f.lower() or "kontrollett" in f.lower() or f.lower() == "kontis" for f in control_forms)
        score += 3 if strong else 2
    elif keywords:
        score += 2
    if direction_text or direction_polarity != "unknown":
        score += 1
    if line_id:
        score += 1

    has_line_direction_context = bool(
        line_id
        and line_validated
        and (direction_text is not None or direction_polarity != "unknown")
    )
    if has_line_direction_context and (not has_k) and (not has_kw):
        score += 2

    is_candidate = score > 0
    is_check_event = score >= 3

    # "Detail-only" messages are candidates that provide line/direction/location but
    # do not themselves cross the check threshold.
    is_detail_only = (
        (not is_check_event)
        and is_candidate
        and (line_id is not None or direction_text is not None or direction_polarity != "unknown" or location_text is not None)
        and (not has_k)
        and (not control_forms)
    )

    if is_check_event:
        if has_k and has_kw:
            match_type = "both"
        elif has_k:
            match_type = "k_token"
        elif has_kw:
            match_type = "keyword"
        elif has_line_direction_context:
            match_type = "line_direction"
        else:
            match_type = "none"
    else:
        match_type = "none"

    matched_k_values = sorted(set(k_values_all))
    k_token_hit_count = 0
    if K_TOKEN_REGEX.search(search_text) or MULTIPLE_K_REGEX.search(search_text) or APPROX_COUNT_WITH_UNIT_REGEX.search(search_text):
        # Count k-count mentions, not endpoints. For a range "3-5k", this is 1.
        k_token_hit_count = len(list(K_TOKEN_REGEX.finditer(search_text)))
        if MULTIPLE_K_REGEX.search(search_text):
            k_token_hit_count = max(k_token_hit_count, 1)
        if APPROX_COUNT_WITH_UNIT_REGEX.search(search_text):
            k_token_hit_count = max(k_token_hit_count, 1)

    return {
        # Core match fields (v1)
        "match_type": match_type,
        "matched_k_values": matched_k_values,
        "matched_k_values_all": k_values_all,
        "k_token_hit_count": k_token_hit_count,
        "matched_keywords": keywords,
        # New contract fields
        "is_candidate": is_candidate,
        "is_check_event": is_check_event,
        "is_detail_only": is_detail_only,
        "confidence_score": score,
        "k_min": k_min,
        "k_max": k_max,
        "k_qualifier": k_qualifier,
        "control_keyword_hit": bool(control_forms),
        "control_keyword_forms": control_forms,
        "line_id": line_id,
        "mode_guess": mode_guess_value,
        "line_validated": bool(line_id and line_validated),
        "line_confidence": line_confidence,
        "direction_text": direction_text,
        "direction_polarity": direction_polarity,
        "location_text": location_text,
        "platform_text": platform_text,
    }
