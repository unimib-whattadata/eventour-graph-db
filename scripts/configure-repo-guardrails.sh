#!/usr/bin/env bash
set -euo pipefail

GRAPHDB_URL="${GRAPHDB_URL:-http://localhost:7200}"
REPO_ID="${REPO_ID:-eventour}"
QUERY_TIMEOUT_SEC="${QUERY_TIMEOUT_SEC:-90}"
THROW_ON_TIMEOUT="${THROW_ON_TIMEOUT:-true}"
QUERY_LIMIT_RESULTS="${QUERY_LIMIT_RESULTS:-5000}"

if ! command -v jq >/dev/null 2>&1; then
  echo "Errore: 'jq' non trovato. Installa jq per modificare il JSON della repository." >&2
  exit 1
fi

tmp_in="$(mktemp)"
tmp_out="$(mktemp)"
trap 'rm -f "$tmp_in" "$tmp_out"' EXIT

echo "Leggo configurazione repository '${REPO_ID}' da ${GRAPHDB_URL}..."
curl --silent --show-error --fail \
  "${GRAPHDB_URL}/rest/repositories/${REPO_ID}" >"$tmp_in"

cat "$tmp_in" | jq \
  --arg timeout "${QUERY_TIMEOUT_SEC}" \
  --arg throw "${THROW_ON_TIMEOUT}" \
  --arg limit "${QUERY_LIMIT_RESULTS}" \
  '
  .params.queryTimeout.value = $timeout
  | .params.throwQueryEvaluationExceptionOnTimeout.value = $throw
  | .params.queryLimitResults.value = $limit
  ' >"$tmp_out"

echo "Applico guardrail:"
echo "  - queryTimeout=${QUERY_TIMEOUT_SEC}s"
echo "  - throwQueryEvaluationExceptionOnTimeout=${THROW_ON_TIMEOUT}"
echo "  - queryLimitResults=${QUERY_LIMIT_RESULTS}"

curl --silent --show-error --fail \
  -X PUT \
  -H "Content-Type: application/json" \
  --data-binary "@${tmp_out}" \
  "${GRAPHDB_URL}/rest/repositories/${REPO_ID}" >/dev/null

echo "Fatto. Verifica rapida:"
curl --silent --show-error --fail \
  "${GRAPHDB_URL}/rest/repositories/${REPO_ID}" \
  | jq '.params.queryTimeout.value, .params.throwQueryEvaluationExceptionOnTimeout.value, .params.queryLimitResults.value'
