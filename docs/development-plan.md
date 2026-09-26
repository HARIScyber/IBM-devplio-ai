# Development plan

## Scope

Deliver a hackathon-ready, locally runnable DevPilot AI MVP. The first release prioritizes a trustworthy demo path, evidence-backed repository analysis, and clear boundaries around optional model-backed features.

## Phases

1. **Project skeleton:** React/TypeScript/Vite dashboard, FastAPI service, configuration, Docker, and a small fictional sample repository.
2. **Repository engine:** safely ingest GitHub archives and ZIP uploads; filter generated/binary/oversized files; derive language, framework, structure, symbols, dependencies, routes, and approximate LOC.
3. **Analysis and retrieval:** evidence-bearing static security/bug checks, lexical repository retrieval with line metadata, and repository-grounded chat.
4. **Agent workflows:** plan, test generation, documentation generation, PR diff review, and GitHub issue/PR reads behind an optional token.
5. **Persistence and resilience:** SQLite records for repositories and activity, bounded upload/clone handling, fallback behavior, validation, and API errors.
6. **Frontend product pass:** polished dark dashboard, repository onboarding, findings/chat/plans/testing/docs/review views, loading/error/empty states, and honest demo labels.
7. **Hackathon handoff:** README, architecture, demo script, submission copy, Bob usage log template, env example, and run/deploy instructions.
8. **Validation:** run pytest, production frontend build, API health and demo-flow checks; fix discovered issues.

## MVP boundaries

- Demo mode uses a bundled fictional repository and deterministic analysis; these results are labelled as demo data.
- Repository chat uses retrieved excerpts and citation metadata. Without a configured provider it returns a transparent deterministic answer from those excerpts, not a claimed live model response.
- The first version uses lexical retrieval and static rules to avoid heavy model/vector dependencies; provider and retriever interfaces leave room for embeddings later.
- GitHub issue/PR reads require `GITHUB_TOKEN`; OAuth, hosted multi-user auth, automatic code modification, and CI merge gates are out of scope.
- IBM Bob is documented as the tool used during actual development only after those workflows are performed; no Bob activity is invented.
