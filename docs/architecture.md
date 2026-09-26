# DevPilot AI architecture

```text
Developer
   |
DevPilot React dashboard
   |
FastAPI API ------------------------- GitHub API (optional token)
   |
Orchestrator
   +-- Repository agent --> safe file ingestion --> metadata/index
   +-- Bug/security agents --> evidence-backed local static rules
   +-- Test agent --> reviewable test draft
   +-- Planner agent --> repository-aware implementation plan
   +-- Documentation/review workflows --> previewable outputs
   |
Lexical retrieval --> cited excerpts --> LLM provider adapter (optional)
   |                                     +-- IBM watsonx.ai
   |                                     +-- Gemini
   |                                     +-- Ollama
   |                                     +-- transparent demo retrieval fallback
   |
SQLite repository/activity/chat metadata
```

## Request flow

1. A user loads the bundled Northstar Tasks sample or supplies a GitHub URL/ZIP file.
2. The repository engine validates archive paths, excludes generated and binary files, and enforces upload/file-count limits.
3. It detects languages, likely frameworks, entry points, configuration, README, route decorators, tests, and repository structure.
4. The analyzer emits findings only when a configured source pattern is present and includes the exact file and line as evidence.
5. Repository chat retrieves lexical matches from indexed lines and cites the source location. A selected live provider receives only the retrieved excerpts. Without a provider, a clearly labeled deterministic retrieval answer is returned.
6. SQLite persists repository metadata, activity, and chat history. Source files remain in local storage.

## Trust boundaries

- GitHub credentials stay in the backend environment and are never returned in responses.
- Only HTTPS URLs on `github.com` are accepted for archive fetches.
- ZIP extraction ignores traversal paths, symlinks, known generated folders, binaries, oversized files, and oversized archives.
- The scanner is heuristic, not a security certification. Findings are labeled as potential issues and should be reviewed.
- Generated docs/tests/plans are previews; the MVP never applies changes to a user's repository.
- Lexical retrieval is deliberately replaceable by an embedding/vector store when deployment needs justify the additional service and dependency.
