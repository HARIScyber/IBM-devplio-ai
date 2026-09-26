# Development log

## Scope

DevPilot AI is a local-first repository assistant. Work follows the hackathon brief's issue-to-verified-fix flow while preserving the existing FastAPI, SQLite, React, and Vite application.

## Implemented

- Repository indexing now extracts Python AST symbols and imports plus lightweight JavaScript/TypeScript signatures. Retrieval returns file, symbol, and line range evidence.
- Finding records expose structured location, impact, recommendation, and confidence metadata.
- A persisted workflow tracks issue, investigation, plan, patch, test, approval, verification, and final review.
- The sample email lookup issue has a deterministic patch proposal and regression test. Verification first demonstrates failure, then passes after patching a temporary copy.
- GitHub issue records include body and labels for investigation handoff.
- A labeled retrieval benchmark computes file hit, symbol hit, and citation line validity directly from retrieval output.
- Request logs include a generated request ID, operation, duration, status, and timestamp; credentials and request bodies are excluded.
- Docker Compose separates persistent data from application code and serves the built frontend with nginx.

## Verification record (2026-09-25)

- `python -m pytest -q tests` from `backend`: 6 passed; one Starlette/httpx deprecation warning.
- `python -m compileall -q backend`: passed.
- `npm run build` from `frontend`: passed.
- `npm test -- --run` from `frontend`: 2 passed.
- `docker compose config`: passed. Image build and container run were unavailable because the local Docker daemon is not running.
- Browser walkthrough on the running local app: sample repository loaded; issue investigated, plan and patch generated, regression test drafted, explicit verification approved, baseline failed and patched copy passed, final review reached `READY_FOR_HUMAN_REVIEW`.
- Live labeled benchmark: 10/10 expected file hits at top 5, 5/5 expected symbol hits across the five symbol-labeled cases, and 10/10 returned citation line ranges valid. These scores measure only the bundled demo retrieval benchmark.

## Known scope limits

Patch generation and execution are intentionally restricted to the bundled sample issue. Imported repository issues can be investigated, but patch generation and arbitrary code execution are not enabled. Static checks and retrieval require human review.
