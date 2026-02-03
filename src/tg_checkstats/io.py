"""Output helpers for tg-checkstats."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, List, Mapping


def write_csv(path: Path, rows: Iterable[Mapping[str, object]], fieldnames: List[str]) -> None:
    """Write CSV deterministically with UTF-8 and \n newlines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, payload: Mapping[str, object]) -> None:
    """Write JSON deterministically with sorted keys and UTF-8."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
