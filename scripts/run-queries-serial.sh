#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Uso: $0 <query-dir|query1.rq [query2.rq ...]>" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUERY_RUNNER="${QUERY_RUNNER:-${SCRIPT_DIR}/query.sh}"
SLEEP_BETWEEN_SEC="${SLEEP_BETWEEN_SEC:-1}"
CONTINUE_ON_ERROR="${CONTINUE_ON_ERROR:-true}"

if [ ! -x "$QUERY_RUNNER" ]; then
  echo "Runner query non eseguibile: $QUERY_RUNNER" >&2
  exit 1
fi

declare -a files=()
if [ "$#" -eq 1 ] && [ -d "$1" ]; then
  while IFS= read -r f; do
    files+=("$f")
  done < <(find "$1" -type f -name "*.rq" | sort)
else
  for arg in "$@"; do
    files+=("$arg")
  done
fi

if [ "${#files[@]}" -eq 0 ]; then
  echo "Nessuna query .rq trovata." >&2
  exit 1
fi

echo "Eseguo ${#files[@]} query in serie (sleep ${SLEEP_BETWEEN_SEC}s)..."
fail_count=0
for f in "${files[@]}"; do
  if [ ! -f "$f" ]; then
    echo "Salto (non trovato): $f" >&2
    continue
  fi

  q_name="$(basename "$f")"
  start_ts="$(date +%s)"
  echo "-> ${q_name}"
  if "$QUERY_RUNNER" "$f" >/tmp/"${q_name}".json; then
    elapsed="$(( $(date +%s) - start_ts ))"
    echo "   OK (${elapsed}s)"
  else
    elapsed="$(( $(date +%s) - start_ts ))"
    echo "   FAIL (${elapsed}s)" >&2
    fail_count=$((fail_count + 1))
    if [ "$CONTINUE_ON_ERROR" != "true" ]; then
      break
    fi
  fi
  sleep "$SLEEP_BETWEEN_SEC"
done

echo "Completato."
if [ "$fail_count" -gt 0 ]; then
  echo "Query fallite: $fail_count" >&2
  exit 1
fi
