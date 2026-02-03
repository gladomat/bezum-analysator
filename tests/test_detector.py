"""Detection rule tests."""

import pytest

from tg_checkstats.detector import find_k_tokens, find_keywords


@pytest.mark.parametrize(
    "text,expected",
    [
        ("2k", [2]),
        ("2 k", [2]),
        ("3K", [3]),
        ("3k.", [3]),
        ("20 k!", [20]),
        ("2k€", []),
        ("2k/m", []),
        ("2к", []),
        ("2K", []),
        ("abc2k", []),
    ],
)
def test_k_token_matches(text, expected):
    matches = find_k_tokens(text)
    assert matches == expected


def test_keyword_matches():
    text = "die Kontrollettis kamen"
    result = find_keywords(text)
    assert "Kontrollettis" in result
