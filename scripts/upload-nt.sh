#!/usr/bin/env bash
set -euo pipefail

GRAPHDB_URL="${GRAPHDB_URL:-http://localhost:7200}"
REPO_ID="${REPO_ID:-eventour}"

if [ "$#" -ne 1 ]; then
  echo "Uso: $0 file.nt" >&2
  exit 1
fi

NT_FILE="$1"

curl \
  -X POST \
  -H "Content-Type: application/n-triples" \
  --data-binary "@${NT_FILE}" \
  "${GRAPHDB_URL}/repositories/${REPO_ID}/statements"
