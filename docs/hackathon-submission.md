# Hackathon submission draft

## Title

DevPilot AI

## Short description

An evidence-first AI software engineering workspace that maps repositories, answers code questions with citations, surfaces potential bugs and security risks, and drafts plans, tests, and docs.

## Long description

Developers working in unfamiliar repositories need more than a chatbot: they need answers grounded in actual files, actionable findings, and a way to turn requirements into work they can review. DevPilot AI indexes a repository, summarizes its structure, and retrieves relevant source lines for repository questions. Static checks surface potential security and runtime issues with file-and-line evidence. The workspace also drafts implementation plans, tests, documentation, and pull request reviews. Its bundled fictional repository makes the demo available without external model credentials. When a provider is configured, DevPilot sends only retrieved excerpts; otherwise it clearly identifies its deterministic retrieval fallback. Generated code and documentation remain previews for human review. DevPilot is designed around the development lifecycle: understand, plan, implement, verify, and communicate.

## Technologies

React, TypeScript, Vite, FastAPI, Python, SQLite, httpx, GitHub REST API (optional), IBM watsonx.ai/Gemini/Ollama provider adapters (optional), Docker Compose.

## Links to complete before submission

- Live demo URL: deploy and verify before entering the URL.
- Public source repository: push this project and add verified Bob session exports if the official current rules require them.
- Demo video and pitch deck: prepare from `docs/demo-script.md`.
- Tracks: select from the current event page once announced.
