## PRD v1.2 — Telegram "k-check" Seasonality Analyzer (Local, Headless CLI)

### 0) Summary

Build a local Python CLI that (1) exports the full history (~300k messages) of
a public Telegram group via telegram-download-chat, (2) detects "check events"
using a locked, testable rule set (k-token OR keywords), (3) converts
timestamps to Europe/Berlin and derives calendar features (day/weekday/ISO
week/month/hour/week-of-month), and (4) writes audit-friendly CSVs (events +
aggregates) plus a run metadata file. Export is kept raw and immutable;
analysis is deterministic from raw+config.

---

## 1) Context & problem

A public Telegram group contains operational "check" messages. You want to
quantify when checks happen (weekday, hour, week-of-month, month/ISO-week
trends) and keep drill-down traceability from any aggregate back to the
originating messages.

---

## 2) Goals / Non-goals

### Goals

- G1 — Accurate detection (rules-first): Transparent, unit-tested detection
  rules; minimal false positives.
- G2 — Correct timezone handling: Use UTC as source of truth; derive Berlin-
  local fields correctly, including DST behavior.
- G3 — Seasonality-ready outputs: Zero-filled matrices and normalized rates
  suitable for Excel/pandas/BI.
- G4 — Auditability: Preserve raw export; emit reproducible derived artifacts
  and a metadata manifest.

### Non-goals (v1)

- Continuous scheduling / daemon mode
- Forecasting / prediction
- NLP topic/sentiment modeling

---

## 3) Primary user & use cases

Primary user: local operator (you).

Use cases

1. One-off full-history analysis: Export + analyze → CSV outputs.
2. Drill-down: Trace any aggregate cell back to matched message IDs and
   truncated text.
3. Repeatable reruns: Re-analyze a prior raw export with different detection
   settings (without re-downloading).

---

## 4) System overview

Pipeline:

1. export: call telegram-download-chat → raw JSON export + export logs
2. analyze: stream/parse raw JSON → detect events → write events.csv +
   aggregates
3. run: performs export then analyze

All outputs are written into a run directory that is immutable by default.

---

## 5) Functional requirements

### FR1 — Export full chat history (raw input)

- The system shall export the full accessible history for a specified public
  chat using telegram-download-chat.
- Raw export format shall be JSON. The tool typically produces a single JSON
  array or object; NDJSON is not expected but shall be supported if present.
- The raw export shall be stored under the run directory and treated as the
  canonical input for analysis.
- The system shall record the export command arguments, tool version, and
  timestamps in run_metadata.json.

Notes

- If the first-ever Telegram login requires a one-time interactive code, that
  step is allowed; subsequent runs must be headless using the saved session.

### FR2 — Auth & configuration (local, safe)

- Operator provides api_id and api_hash via .env (or environment variables).
- The CLI shall generate a temporary config for telegram-download-chat at
  runtime.
- The CLI shall never write .env into run outputs.
- run_metadata.json shall redact secrets:
    - store api_id_last4 (or omit)
    - store api_hash_present: true/false
    - optionally store api_hash_sha256_prefix (first 8 hex) for
      reproducibility checks

### FR3 — Input parsing & message inclusion rules

The analyzer shall parse exported messages and apply inclusion defaults:

Default INCLUDED

- Regular user/bot messages that contain text and/or caption-like fields

Default EXCLUDED

- Service messages (join/leave, pins, title/photo changes, etc.)
- Messages missing a usable timestamp
- Messages with duplicate message_id (keep first occurrence; log duplicates)

Notes

- Telegram message_ids are unique per chat. Duplicate IDs usually indicate that
  multiple exports were concatenated or a partial/duplicated export was used.
  The analyzer keeps the first occurrence to remain stream-friendly; duplicates
  are counted and logged for investigation.

Config flags

- --include-service (default false)
- --include-bots (default true; can be turned off). Note: This flag filters by
  sender type, not by forward source. A message forwarded from a bot but sent
  by a human is included unless --include-forwards=false.
- --include-forwards (default true; can be turned off)

Edits

- The analyzer shall analyze the final message text as present in the export.
- If the export includes an edit timestamp field, it may be recorded for
  matched messages (events.csv) and counted in metadata; v1 does not attempt to
  reconstruct historical pre-edit content.

### FR4 — Schema mapping (robust, explicit)

Because export schemas can vary, the analyzer shall implement a tolerant
mapping:

For each message, attempt to extract:

- message_id: required
- timestamp_utc: required (from a known date field; see below)
- text: optional (may be null or missing)
- caption: optional (may be null or missing)
- sender_id: optional
- is_service: optional (or inferred from message type fields)
- is_bot: optional (inferred from sender metadata if available)
- is_forward: optional (inferred from forward_from or forward_date fields)

Timestamp parsing contract

- Accept ISO-8601 strings with timezone offsets, or naive ISO strings (assume
  UTC and record timestamp_assumed_utc=true), or Unix epoch seconds if
  present.
- Store timestamp_utc as an ISO-8601 string with Z (UTC).
- Convert to timestamp_berlin using Europe/Berlin zone rules.

Text extraction contract

- The analyzer shall normalize `text` and `caption` into plain strings for
  matching.
- If a field is a string: use as-is.
- If a field is a list (e.g., fragments/entities): flatten by concatenating
  each element, where elements contribute text if they are:
    - strings, or
    - dicts with a string `text` key.
  Other element types are ignored.
- If `text` is any other type: treat it as empty string and increment
  messages_text_non_string.
- If `caption` is any other type: treat it as empty string and increment
  messages_caption_non_string.

Error handling

- If timestamp parsing fails for a message, exclude that message and increment
  excluded_invalid_timestamp counter in metadata.
- If the raw JSON is malformed or truncated, abort with a clear error message
  indicating the byte offset or line number of the failure.

### FR5 — Derived calendar fields (Berlin-local)

Timezone is locked to Europe/Berlin for v1 (not configurable).

For each included message:

- date_berlin (YYYY-MM-DD), weekday (Mon..Sun), weekday_idx (0=Mon..6=Sun)
- iso_year, iso_week
- month (YYYY-MM)
- time_berlin (HH:MM:SS), hour (0–23)
- week_of_month_simple = 1 + floor((day_of_month - 1)/7) → values 1..5

DST rule

- UTC is the source of truth; Berlin fields are derived. The system shall not
  attempt to "roundtrip" local times back to UTC.

### FR6 — Check event detection rules (locked for v1)

A message is a check event if either condition matches on search_text.

search_text construction:

- If both text and caption are present: normalized_text + "\n" + normalized_caption
- If only text is present: normalized_text
- If only caption is present: normalized_caption
- If neither is present: empty string (no match possible)

#### A) k-token match (ASCII k only)

- Matches numeric tokens from 1..20 followed by ASCII k/K, with optional
  whitespace between number and k.
- Must not be part of a larger word token (no preceding Unicode word
  character).
- Trailing context after `k` must be end-of-string or a delimiter character:
  whitespace or one of `. , ! ? : ; ) ] } ' " -`.
- This intentionally rejects currency/units and other suffixes such as 2k€,
  2kB, 2k/m.

Normative regex (Python `re` module)

```
(?<!\w)([1-9]|1[0-9]|20)\s*[kK](?=$|[\s\.\,\!\?\:\;\)\]\}\'\"\-])
```

Explanation:
- `(?<!\w)` — negative lookbehind: no preceding Unicode word character
- `([1-9]|1[0-9]|20)` — matches integers 1-20 exactly (no leading zeros, no 0)
- `\s*` — optional whitespace between number and k
- `[kK]` — ASCII k or K only
- `(?=$|[\s\.\,\!\?\:\;\)\]\}\'\"\-])` — lookahead requiring allowed trailing
  delimiter (or end-of-string)

This correctly rejects: 0k, 21k, 100k, 2k€, 2kB, 2k/m, abc2k, 2k_, Cyrillic к, Kelvin sign K.
This correctly matches: 1k, 2k, 2 k, 3K, 3k., 20 k!, 5k? 10k\n

Count policy

- Default: one event per message (event_count_policy=message)
- Event weight per matched message:
    - If event_count_policy=message: event_weight = 1
    - If event_count_policy=token: event_weight = k_token_hit_count if
      k_token_hit_count > 0 else 1 (keyword-only)
- Still record all k-token hits:
    - matched_k_values (unique, sorted list of integers)
    - matched_k_values_all (optional, preserves multiplicity)
    - k_token_hit_count

#### B) Keyword triggers (case-insensitive, word-boundary)

Keywords are matched using Python `re` module with `\b` word boundaries:

- \bKontrollettis\b
- \bKontrolleure\b
- \bKontis\b

Note: `\b` in Python `re` matches transitions between `\w` and `\W`
characters. By default, Python 3 regexes are Unicode-aware (`\w` includes
Unicode letters/digits/underscore). Hyphens are non-word characters, so
"Kontrollettis-Einsatz" will match "Kontrollettis".

Recorded fields

- match_type: k_token | keyword | both
- matched_keywords: list of matched canonical keywords (original casing)

### FR7 — Aggregations (zero-filled where appropriate)

The analyzer shall compute aggregates over the full Berlin-local calendar date
range from:

- dataset_start_berlin_date = min date among all messages with usable
  timestamps (after duplicate removal), regardless of include/exclude flags
- dataset_end_berlin_date = max date among all messages with usable timestamps
  (after duplicate removal), regardless of include/exclude flags

"Full calendar date range" means every calendar date from start to end
inclusive, regardless of whether any messages exist on that date.

Counting definitions

- check_message_count: number of matched messages in the group.
- check_event_count: sum of event_weight across matched messages in the group.
  (In message mode, these are equal; in token mode, check_event_count may be
  larger.)

Zero-fill requirements

- Daily series must include every date in the range, with 0 for dates without
  events.
- Heatmap matrices must include all theoretical combinations, filling missing
  with 0:
    - Weekday×Hour: all 7×24 = 168 combinations
    - Week-of-month: values 1–5 (all five, even if some never occur in data)
- ISO-week series must include every ISO week that overlaps the full calendar
  date range, zero-filled.
- Hour stats: all 24 hours (0–23)
- Weekday stats: all 7 weekdays (Mon–Sun)

Minimum outputs:

1. Daily counts: date_berlin → check_message_count, check_event_count
2. Weekday stats
    - totals per weekday (messages + events)
    - weekday_occurrences = count of calendar dates in the full date range
      that fall on that weekday
    - mean_messages_per_weekday = check_message_count / weekday_occurrences
    - mean_events_per_weekday = check_event_count / weekday_occurrences
3. Hour stats
    - totals per hour (0–23) (messages + events)
4. Weekday×Hour matrix (7×24)
    - All 168 combinations, zero-filled (messages + events)
5. Week-of-month
    - totals by week_of_month_simple (values 1–5, zero-filled) (messages + events)
6. ISO week trend
    - ISO-week series across the full date range, zero-filled
    - iso_week_start_date_berlin = Monday date for the ISO week (Berlin-local)
    - days_in_week_in_range = count of calendar dates in that ISO week that
      fall within [dataset_start, dataset_end]
    - is_partial_week = true if days_in_week_in_range < 7
7. Month normalization
    - month (YYYY-MM)
    - month_message_count (matched-message count)
    - month_event_count (sum of event_weight)
    - days_in_month_in_range = count of calendar dates within that month that
      fall within [dataset_start, dataset_end]
    - is_partial_month = true if days_in_month_in_range < calendar days in
      that month
    - messages_per_day_in_month = month_message_count / days_in_month_in_range
    - events_per_day_in_month = month_event_count / days_in_month_in_range

### FR8 — Outputs (files & columns)

Run directory layout

```
runs/<run_name>/
├── run_metadata.json
├── raw/                    # immutable inputs
│   └── <export>.json
├── logs/                   # all logs (export + analyze)
│   ├── export.log
│   └── analyze.log
└── derived/
    ├── events.csv
    └── <aggregate CSVs>
```

Note: All logs are consolidated under logs/ for consistency.

CSV: events

derived/events.csv — one row per matched message:

- message_id
- timestamp_utc
- timestamp_berlin
- date_berlin
- weekday
- weekday_idx
- iso_year
- iso_week
- month
- time_berlin
- hour
- week_of_month_simple
- match_type
- event_weight
- matched_k_values (JSON array string, e.g., [2, 20])
- matched_keywords (JSON array string, e.g., ["Kontrollettis"])
- k_token_hit_count
- text_trunc (default max 500 chars of search_text)
- text_len (length of full search_text)
- text_sha256 (SHA-256 hex digest of full search_text, for verification
  against raw export when combined with message_id)

CSV: aggregates (minimum set)

- derived/daily_counts.csv
    - date_berlin, check_message_count, check_event_count
- derived/weekday_counts.csv
    - weekday, weekday_idx, check_message_count, check_event_count,
      weekday_occurrences, mean_messages_per_weekday, mean_events_per_weekday
- derived/hour_counts.csv
    - hour, check_message_count, check_event_count
- derived/weekday_hour_counts.csv
    - weekday, weekday_idx, hour, check_message_count, check_event_count
      (all 168 rows)
- derived/week_of_month_counts.csv
    - week_of_month_simple, check_message_count, check_event_count
      (rows for 1–5)
- derived/month_week_of_month_counts.csv
    - month, week_of_month_simple, check_message_count, check_event_count
- derived/iso_week_counts.csv
    - iso_year, iso_week, iso_week_start_date_berlin, days_in_week_in_range,
      is_partial_week, check_message_count, check_event_count
- derived/month_counts_normalized.csv
    - month, month_message_count, month_event_count, days_in_month_in_range,
      is_partial_month, messages_per_day_in_month, events_per_day_in_month

Metadata: run_metadata.json

Must include:

- tool_versions:
    - telegram_download_chat: version string
    - analyzer: version string
- environment:
    - python_version
    - platform
- timestamps:
    - export_started_utc, export_completed_utc (if export ran)
    - analyze_started_utc, analyze_completed_utc
- commands:
    - tg_checkstats_argv (argv list as executed)
    - telegram_download_chat_argv (argv list; if export ran)
- input:
    - chat_identifier_raw (as provided)
    - chat_identifier_normalized
    - raw_export_path
    - raw_export_sha256
- config: (non-secret snapshot of all options)
    - timezone: "Europe/Berlin"
    - k_max: 20
    - keywords: ["Kontrollettis", "Kontrolleure", "Kontis"]
    - event_count_policy: "message"
    - include_service: false
    - include_bots: true
    - include_forwards: true
    - export_retry_count: 3
    - export_retry_delay_seconds: 5
    - text_trunc_len: 500
- auth: (redacted)
    - api_id_last4 (or omitted)
    - api_hash_present: true/false
    - api_hash_sha256_prefix (optional; first 8 hex)
- counts:
    - messages_scanned
    - messages_included
    - messages_excluded_service
    - messages_excluded_no_timestamp
    - messages_excluded_invalid_timestamp
    - messages_excluded_duplicate_id
    - messages_excluded_bot (if --include-bots=false)
    - messages_excluded_forward (if --include-forwards=false)
    - messages_text_non_string
    - messages_caption_non_string
    - events_matched_total
    - events_matched_k_token_only
    - events_matched_keyword_only
    - events_matched_both
    - events_weight_total
    - events_weight_k_token_only
    - events_weight_keyword_only
    - events_weight_both
- dataset:
    - start_berlin_date
    - end_berlin_date
    - total_days_in_range
- assumptions:
    - naive_timestamps_treated_as_utc: true/false
    - naive_timestamp_count: N

---

## 6) CLI UX

### Commands

```
tg-checkstats export --chat <id|@name|t.me/...> --out runs/<run_name> [options]
tg-checkstats analyze --input runs/<run_name>/raw/<export>.json --out runs/<run_name> [options]
tg-checkstats run --chat <id|@name|t.me/...> --out runs/<run_name> [options]
```

### Key options (defaults)

| Option | Default | Description |
|--------|---------|-------------|
| --include-service | false | Include service messages |
| --include-bots | true | Include messages from bots |
| --include-forwards | true | Include forwarded messages |
| --event-count-policy | message | `message` (each matched message counts as 1) or `token` (k-token hits count; keyword-only messages count as 1) |
| --export-retry-count | 3 | Export retry count (passed through to exporter) |
| --export-retry-delay | 5 | Seconds to wait between export retries |
| --text-trunc-len | 500 | Max characters for text_trunc field |
| --force | false | Overwrite existing run (see behavior below) |

Locked for v1 (not exposed as CLI options):

- Timezone: Europe/Berlin
- k-token range: 1–20
- Keywords: Kontrollettis, Kontrolleure, Kontis

### --force behavior

When --force is specified:

- If the run directory exists, the `derived/` and `logs/` subdirectories are
  deleted and recreated.
- The `raw/` subdirectory is NEVER deleted. If `raw/` already contains an
  export, it is preserved.
- For the `export` command with --force, if `raw/` already contains an export,
  the command aborts with an error suggesting to use a new run name or manually
  delete the raw export.
- For the `analyze` command with --force, existing derived outputs are
  overwritten.

---

## 7) Non-functional requirements

### NFR1 — Performance & memory

- Must process ~300k messages without exhausting memory.
- Implementation strategy:
    - For NDJSON: line-by-line streaming parse.
    - For JSON array: use ijson or similar incremental JSON parser to avoid
      loading entire file into memory. If incremental parsing is not feasible,
      fall back to chunked reading with memory monitoring.
- Target (guideline): analyze 300k messages in < 5 minutes and < 1.0 GB peak
  RSS on a typical laptop.
- If memory usage exceeds 1.5 GB during analysis, log a warning.

### NFR2 — Reproducibility & auditability

- Raw export preserved unchanged.
- Derived outputs deterministic from raw+config (same raw + same config =
  byte-identical derived outputs, excluding timestamps in metadata).
- To ensure byte-stability across runs, the implementation shall:
    - write all CSVs as UTF-8 with `\n` newlines and RFC4180-style quoting
    - use a stable sort order for every output (e.g., events.csv by
      timestamp_utc then message_id; aggregates by their key columns)
    - serialize JSON-in-CSV fields (matched_k_values, matched_keywords) using a
      canonical JSON format (no extra whitespace)
    - format floating-point rate columns using a fixed precision
      (recommended: 6 decimal places)
- run_metadata.json should be written with stable key ordering for diffs
  (recommended: JSON pretty-print with sort_keys=true). Metadata timestamps are
  expected to differ run-to-run.
- Every run produces a complete run_metadata.json.

### NFR3 — API reliability knobs

- Expose downloader retry/delay knobs as pass-through options:
    - --export-retry-count (default 3)
    - --export-retry-delay (default 5 seconds)
- Record these values in run_metadata.json.

### NFR4 — Security

- No secrets written to run directory.
- Logs must not print secrets (api_id, api_hash, session tokens).

### NFR5 — Error handling

- Export interruption: If export is interrupted, partial raw export may exist.
  The analyze command shall detect truncated/malformed JSON and abort with a
  clear error. The operator must re-run export or manually fix/remove the
  partial file.
- Resumability: Not supported in v1. Each export is a full re-download.

---

## 8) Testing & acceptance criteria

### Unit tests (must-have)

k-token regex:

| Input | Expected |
|-------|----------|
| "2k" | match: 2 |
| "2 k" | match: 2 |
| "3K" | match: 3 |
| "3k." | match: 3 |
| "20 k!" | match: 20 |
| "5k?" | match: 5 |
| "10k\n" | match: 10 |
| "1k" | match: 1 |
| "0k" | no match |
| "21k" | no match |
| "100k" | no match |
| "2k€" | no match |
| "2kB" | no match |
| "2k/m" | no match |
| "abc2k" | no match |
| "2k_" | no match |
| "2к" (Cyrillic) | no match |
| "2K" (Kelvin sign) | no match |
| "text 5k here" | match: 5 |
| "5k and 10k" | match: 5, 10 |

Keyword matching:

| Input | Expected |
|-------|----------|
| "Kontrollettis" | match |
| "kontrollettis" | match |
| "KONTROLLETTIS" | match |
| "die Kontrollettis kamen" | match |
| "Kontrollettis-Einsatz" | match (word boundary before hyphen) |
| "abcKontrollettis" | no match |
| "Kontrollettisxyz" | no match |

Timezone tests:

- Test messages at 23:30 UTC on day before DST transition → verify correct
  Berlin date/hour
- Test messages at 00:30 UTC on day of DST transition → verify correct Berlin
  date/hour
- Test Berlin late March (spring forward) and late October (fall back)
  transitions

### Golden fixture (must-have)

- Include a small sanitized export fixture in the repo (e.g., 100 messages with
  known matches).
- Assert deterministic outputs: running analyze twice on the same fixture
  produces identical events.csv and aggregate CSVs.

### Run-level invariants (must pass)

- sum(daily_counts.check_message_count) == row_count(events.csv)
- sum(daily_counts.check_event_count) == sum(events.csv.event_weight)
- sum(weekday_hour_counts.check_message_count) == row_count(events.csv)
- sum(weekday_hour_counts.check_event_count) == sum(events.csv.event_weight)
- sum(weekday_counts.check_message_count) == row_count(events.csv)
- sum(weekday_counts.check_event_count) == sum(events.csv.event_weight)
- sum(hour_counts.check_message_count) == row_count(events.csv)
- sum(hour_counts.check_event_count) == sum(events.csv.event_weight)
- sum(week_of_month_counts.check_message_count) == row_count(events.csv)
- sum(week_of_month_counts.check_event_count) == sum(events.csv.event_weight)
- sum(iso_week_counts.check_message_count) == row_count(events.csv)
- sum(iso_week_counts.check_event_count) == sum(events.csv.event_weight)
- sum(month_counts_normalized.month_message_count) == row_count(events.csv)
- sum(month_counts_normalized.month_event_count) == sum(events.csv.event_weight)
- All matched_k_values entries are integers in [1, 20]
- events.csv message_id values are unique
- weekday_hour_counts.csv has exactly 168 rows
- week_of_month_counts.csv has exactly 5 rows (weeks 1–5)
- hour_counts.csv has exactly 24 rows
- weekday_counts.csv has exactly 7 rows (Mon–Sun)

### Manual audit (recommended)

- Random sample of 200 matched rows: ≥ 97% true positives per your definition.

---

## 9) Milestones

- M1 Export: raw export produced and captured in run directory with metadata.
  Export logs captured. Secrets not leaked.
- M2 Analyze core: events detected correctly; events.csv correct and
  reproducible. Regex and keyword unit tests passing.
- M3 Aggregates: all aggregate CSVs generated; run-level invariants pass;
  zero-fill verified for all aggregates.
- M4 Hardening: streaming/large-file performance validated (300k messages);
  DST tests passing; error handling for malformed JSON tested.

---

## 10) Decisions locked for v1

- Timezone is Europe/Berlin (not configurable).
- k-token range is 1–20 (not configurable).
- Keywords are Kontrollettis, Kontrolleure, Kontis (not configurable).
- Caption is included in search_text.
- Keywords use case-insensitive word-boundary matching (Python `re` \b).
- events.csv stores truncated text + length + SHA-256 of search_text; raw
  export remains the full-text source of truth.
- UTC is canonical; Berlin-local fields are derived only.
- One event per message (event_count_policy=message) by default.
- Duplicate message_ids are excluded (first occurrence kept).

---

## Appendix A: Changelog from v1.1

### Fixes

1. **Regex pattern corrected**: Changed from `(20|1?\d)` (which matched 0) to
   `([1-9]|1[0-9]|20)` (matches exactly 1–20).

2. **Regex trailing context**: Changed from restrictive character class to
   an allowed-delimiter lookahead, which rejects currency/unit suffixes such as
   2k€ and 2k/m while still matching punctuation and whitespace.

3. **Streaming clarified**: Acknowledged that telegram-download-chat typically
   produces JSON array (not NDJSON). Specified ijson or similar for incremental
   parsing.

4. **search_text construction**: Clarified handling when text or caption is
   null/missing (no spurious newlines) and added a normalization contract for
   structured text fields (fragment lists).

5. **--force behavior**: Specified that raw/ is never deleted to prevent
   accidental data loss.

6. **Duplicate handling**: Added explicit duplicate message_id handling.

7. **Error handling**: Added specifications for malformed JSON and timestamp
   parse failures.

8. **Partial month flag**: Added `is_partial_month` column to
   month_counts_normalized.csv for proper interpretation.

9. **Weekday mean clarified**: Specified `weekday_occurrences` as calendar
   count in full date range.

10. **Zero-fill explicit**: Specified all combinations that must be zero-filled
    (168 weekday×hour rows, 5 week-of-month rows, 24 hours, 7 weekdays, ISO
    weeks overlapping the dataset range).

11. **Log location**: Consolidated all logs under `logs/` directory.

12. **Locked options removed from CLI**: Removed --tz, --k-max, --keywords from
    CLI options since they're locked for v1.

13. **Bot/forward interaction**: Clarified that --include-bots filters by
    sender, not forward source.

14. **SHA-256 clarified**: Noted that text_sha256 is of search_text (not raw
    text field) for verification purposes.

15. **Event weighting added**: Defined event_weight and check_event_count to
    support token-based counting without breaking drill-down (events.csv stays
    1 row per matched message).
