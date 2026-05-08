#!/usr/bin/env bash
set -euo pipefail

GRAPHDB_URL="${GRAPHDB_URL:-http://localhost:7200}"
REPO_ID="${REPO_ID:-eventour}"
QUERY_TIMEOUT_SEC="${QUERY_TIMEOUT_SEC:-120}"
CONNECT_TIMEOUT_SEC="${CONNECT_TIMEOUT_SEC:-10}"
LOCK_FILE="${LOCK_FILE:-/tmp/eventour-graphdb-query.lock}"
LOCK_WAIT_SEC="${LOCK_WAIT_SEC:-300}"
ACCEPT_HEADER="${ACCEPT_HEADER:-application/sparql-results+json}"

if [ "$#" -ne 1 ]; then
  echo "Uso: $0 query.rq" >&2
  exit 1
fi

QUERY_FILE="$1"
if [ ! -f "$QUERY_FILE" ]; then
  echo "File query non trovato: $QUERY_FILE" >&2
  exit 1
fi

# Evita burst concorrenti sullo stesso host (utile in deploy e batch CI).
if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK_FILE"
  if ! flock -w "$LOCK_WAIT_SEC" 9; then
    echo "Timeout in attesa lock query (${LOCK_WAIT_SEC}s): $LOCK_FILE" >&2
    exit 1
  fi
fi

curl \
  --silent --show-error \
  --connect-timeout "$CONNECT_TIMEOUT_SEC" \
  --max-time "$QUERY_TIMEOUT_SEC" \
  --fail-with-body \
  -H "Accept: ${ACCEPT_HEADER}" \
  --data-urlencode "query@${QUERY_FILE}" \
  "${GRAPHDB_URL}/repositories/${REPO_ID}"
