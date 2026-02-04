#!/usr/bin/env bash
set -euo pipefail

CHAT_URL="${1:-}"
if [[ -z "${CHAT_URL}" ]]; then
  echo "Usage: $0 <chat-url-or-username>" >&2
  echo "Example: $0 https://t.me/freifahren_leipzig" >&2
  exit 2
fi

# Edit these defaults (or override via env vars) and re-run.
RUNS_DIR="${RUNS_DIR:-runs}"
RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)}"
EXPORT_LIMIT="${EXPORT_LIMIT:-0}" # 0 => no limit

TELEGRAM_DOWNLOAD_CHAT_BIN="${TELEGRAM_DOWNLOAD_CHAT_BIN:-./.venv/bin/telegram-download-chat}"
PYTHON_BIN="${PYTHON_BIN:-./.venv/bin/python}"

ANALYZE_FORCE_AUTO="${ANALYZE_FORCE_AUTO:-1}"

slug_from_chat() {
  local chat="$1"
  chat="${chat#https://t.me/}"
  chat="${chat#http://t.me/}"
  chat="${chat#t.me/}"
  chat="${chat#@}"
  chat="${chat%%\?*}"
  chat="${chat%%/*}"
  if [[ -z "${chat}" ]]; then
    chat="chat"
  fi
  printf "%s" "${chat}"
}

CHAT_SLUG="$(slug_from_chat "${CHAT_URL}")"
RUN_NAME="${RUN_NAME:-${CHAT_SLUG}_${RUN_ID}}"
RUN_DIR="${RUNS_DIR}/${RUN_NAME}"

mkdir -p "${RUN_DIR}/raw"

if [[ ! -x "${TELEGRAM_DOWNLOAD_CHAT_BIN}" ]]; then
  echo "ERROR: telegram-download-chat not found at: ${TELEGRAM_DOWNLOAD_CHAT_BIN}" >&2
  echo "Hint: install it into the venv: ./.venv/bin/python -m pip install telegram-download-chat" >&2
  exit 1
fi
if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "ERROR: python not found at: ${PYTHON_BIN}" >&2
  exit 1
fi

echo "run_dir=${RUN_DIR}"

limit_args=()
if [[ "${EXPORT_LIMIT}" != "0" ]]; then
  limit_args=(-l "${EXPORT_LIMIT}")
fi

export_cmd=(
  "${TELEGRAM_DOWNLOAD_CHAT_BIN}"
  "${limit_args[@]}"
  -o "${RUN_DIR}/raw/export.json"
  "${CHAT_URL}"
)

echo "+ ${export_cmd[*]}"
"${export_cmd[@]}"

analyze_args=()
if [[ "${ANALYZE_FORCE_AUTO}" == "1" ]] && [[ -d "${RUN_DIR}/derived" ]]; then
  analyze_args+=(--force)
fi

echo "+ PYTHONPATH=src ${PYTHON_BIN} -m tg_checkstats analyze --input ${RUN_DIR}/raw/export.json --out ${RUN_DIR} ${analyze_args[*]:-}"
PYTHONPATH=src "${PYTHON_BIN}" -m tg_checkstats analyze --input "${RUN_DIR}/raw/export.json" --out "${RUN_DIR}" "${analyze_args[@]}"

echo "done"
