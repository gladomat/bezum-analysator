"""Parsing utilities tests."""

from datetime import timezone

from tg_checkstats.parse import normalize_text, parse_timestamp


def test_normalize_text_list():
    assert normalize_text(["a", {"text": "b"}, 5]) == "ab"


def test_parse_timestamp_iso():
    dt, assumed = parse_timestamp("2024-01-02T03:04:05Z")
    assert dt.tzinfo is not None
    assert dt.tzinfo == timezone.utc
    assert assumed is False
