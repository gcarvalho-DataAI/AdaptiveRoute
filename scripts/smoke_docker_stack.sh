#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

for _attempt in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8090/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

curl -fsS http://127.0.0.1:8090/health >/dev/null
curl -fsS http://127.0.0.1:5173 >/dev/null

response="$(curl -fsS http://127.0.0.1:8090/v1/agentic/replan \
  -H 'Content-Type: application/json' \
  -d '{"message":"Customer C3 cannot receive now."}')"

python3 - <<'PY' "$response"
import json
import sys

body = json.loads(sys.argv[1])
assert body["conversation_id"]
assert body["agentic_result"]["succeeded"] is True
assert body["context_window"]["last_event"]["payload"] == {"customer_id": "C3"}
print("API smoke ok:", body["conversation_id"])
PY

./scripts/docker_compose_cmd.sh exec -T mongo mongosh --quiet --eval '
db=db.getSiblingDB("adaptiveroute");
const counts = {
  conversations: db.conversations.countDocuments(),
  messages: db.messages.countDocuments(),
  context_windows: db.context_windows.countDocuments(),
  agent_runs: db.agent_runs.countDocuments()
};
printjson(counts);
if (counts.conversations < 1 || counts.messages < 2 || counts.context_windows < 1 || counts.agent_runs < 1) {
  quit(1);
}
'

rag_ingest="$(curl -fsS http://127.0.0.1:8090/v1/rag/ingest \
  -H 'Content-Type: application/json' \
  -d '{"paths":["README.md","docs"]}')"

python3 - <<'PY' "$rag_ingest"
import json
import sys

body = json.loads(sys.argv[1])
assert body["document_count"] >= 1
assert body["chunk_count"] >= 1
print("RAG ingest smoke ok:", body["document_count"], "documents,", body["chunk_count"], "chunks")
PY

rag_query="$(curl -fsS http://127.0.0.1:8090/v1/rag/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"How does the routing policy model work?","limit":3}')"

python3 - <<'PY' "$rag_query"
import json
import sys

body = json.loads(sys.argv[1])
assert len(body["results"]) >= 1
print("RAG query smoke ok:", len(body["results"]), "results")
PY

./scripts/docker_compose_cmd.sh exec -T postgres psql -U adaptiveroute -d adaptiveroute -tAc \
  "SELECT COUNT(*) FROM rag_document_chunks;" | awk '{ if ($1 < 1) exit 1; print "pgvector chunks:", $1 }'
