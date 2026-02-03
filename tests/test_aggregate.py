"""Aggregation utilities tests."""

from datetime import date

from tg_checkstats.aggregate import build_iso_week_series, build_weekday_hour_matrix


def test_zero_fill_weekday_hour():
    rows = build_weekday_hour_matrix({})
    assert len(rows) == 168
    assert rows[0]["hour"] == 0


def test_iso_week_range():
    rows = build_iso_week_series(date(2024, 1, 1), date(2024, 1, 10), {})
    assert len(rows) >= 2
