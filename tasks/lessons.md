# Lessons Learned

Past mistakes and the rules derived from them. Reviewed at the start of every session per global CLAUDE.md.

---
## 2026-07-16 — deepseek-r1 output is not clean JSON
- Mistake: assumed `json_mode=True` guarantees parseable JSON from Ollama/deepseek-r1. It returns fenced ```json blocks, leading newlines, sometimes trailing prose, and can burn the entire MAX_TOKENS budget on its `reasoning` field, returning empty `content`.
- Rule: always sanitize local-model output through `ai_service.extract_json_payload()` and keep MAX_TOKENS ≥ 2000 for reasoning models. Test AI paths against the live model, not just mocks.

## 2026-07-16 — Codex sandbox broken on this server
- Mistake: none, but Codex delegation failed with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` before touching files.
- Rule: if codex-companion fails with bwrap errors on nexus-services, implement small well-specified fixes directly instead of retrying; flag the sandbox issue to the user.

## 2026-07-16 — backend/.env has Windows CRLF + BOM
- Mistake: tried `source .env` in bash; CRLF line endings (Syncthing mirror from Windows) broke every value.
- Rule: load env in Python via python-dotenv (handles CRLF/BOM) or strip with `tr -d '\r'` first; never `source` this file.
