# tg-checkstats

Local, headless CLI to export a public Telegram chat (via `telegram-download-chat`) and analyze "k-check" seasonality.

## Usage

```bash
tg-checkstats export --chat <chat> --out <run-dir>
tg-checkstats analyze --input <run-dir>/raw/export.json --out <run-dir>
tg-checkstats run --chat <chat> --out <run-dir>
```
