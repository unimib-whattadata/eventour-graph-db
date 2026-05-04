#!/usr/bin/env bash
set -euo pipefail

GRAPHDB_URL="${GRAPHDB_URL:-http://localhost:7200}"
REPO_ID="${REPO_ID:-eventour}"

if [ "$#" -ne 1 ]; then
  echo "Uso: $0 query.rq" >&2
  exit 1
fi

QUERY_FILE="$1"

curl \
  -H "Accept: application/sparql-results+json" \
  --data-urlencode "query@${QUERY_FILE}" \
  "${GRAPHDB_URL}/repositories/${REPO_ID}"
