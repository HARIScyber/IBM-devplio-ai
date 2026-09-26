from __future__ import annotations

import logging
from typing import Any

from .analysis import make_plan, make_tests
from .providers import get_provider, MockProvider
from .retrieval import retrieve


logger = logging.getLogger("devpilot.agents")


class RepositoryAgent:
    def __init__(self, repo: dict[str, Any]):
        self.repo = repo

    def context(self, query: str) -> list[dict[str, Any]]:
        return retrieve(self.repo, query)


class PlannerAgent:
    def run(self, requirement: str, repo: dict[str, Any]) -> list[dict[str, str]]:
        return make_plan(requirement, repo)


class TestAgent:
    def run(self, repo: dict[str, Any], target: str, request: str) -> dict[str, str]:
        return make_tests(repo, target, request)


class OrchestratorAgent:
    """Small dispatcher; specialist methods stay deterministic and inspectable."""

    def __init__(self, repo: dict[str, Any]):
        self.repo = repo
        self.repository = RepositoryAgent(repo)
        self.planner = PlannerAgent()
        self.test_agent = TestAgent()

    async def answer(self, question: str) -> dict[str, Any]:
        evidence = self.repository.context(question)
        provider_error = False
        try:
            provider = get_provider()
        except ValueError:
            logger.warning("provider_configuration_invalid", extra={"agent": "chat", "operation": "provider_select", "error": "UnsupportedProvider"})
            provider = MockProvider()
            provider_error = True
        if not isinstance(provider, MockProvider):
            prompt = "Answer the developer using ONLY the repository excerpts below. Cite paths and line ranges. If the evidence is insufficient, say so. Do not reveal private chain-of-thought; provide a concise engineering explanation.\n\nQuestion: " + question + "\n\nExcerpts:\n" + "\n".join(f"{item['file']}:{item['line_start']}-{item['line_end']} ({item.get('symbol') or 'file'}): {item['excerpt']}" for item in evidence)
            try:
                answer = await provider.complete(prompt, system="You are a careful software repository assistant. Cite only provided paths and line numbers.")
                mode = provider.name
            except Exception as exc:
                logger.warning("provider_request_failed", extra={"agent": "chat", "operation": "provider_complete", "provider": provider.name, "error": type(exc).__name__})
                answer = self._fallback_answer(question, evidence)
                mode = f"retrieval fallback ({provider.name} unavailable)"
        else:
            answer = self._fallback_answer(question, evidence)
            mode = "retrieval fallback (invalid provider configuration)" if provider_error else "demo retrieval"
        return {"answer": answer, "sources": [{key: e.get(key) for key in ("file", "line", "line_start", "line_end", "symbol", "language", "chunk_type", "excerpt")} for e in evidence],
                "reasoning_summary": "Matched the question against indexed repository lines and used the cited excerpts as evidence.",
                "suggested_actions": [f"Open {evidence[0]['file']}" if evidence else "Add or index relevant source files", "Verify this behavior with a focused test"],
                "mode": mode}

    @staticmethod
    def _fallback_answer(question: str, evidence: list[dict[str, Any]]) -> str:
        if not evidence:
            return "I could not find matching source lines in the indexed text files. Try a more specific symbol, filename, or concept, or add the relevant files to the repository."
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in evidence[:5]:
            grouped.setdefault(item["file"], []).append(item)
        parts = [f"I found repository evidence related to **{question[:100]}**:"]
        for path, rows in grouped.items():
            lines = ", ".join(str(r["line_start"]) if r["line_start"] == r["line_end"] else f"{r['line_start']}-{r['line_end']}" for r in rows)
            excerpt = " · ".join(r["excerpt"] for r in rows[:2])
            symbols = ", ".join(dict.fromkeys(r.get("symbol", "") for r in rows if r.get("symbol")))
            label = f" ({symbols})" if symbols else ""
            parts.append(f"- `{path}:{lines}`{label} — {excerpt}")
        parts.append("This answer uses local retrieval rather than a configured live model. Review the cited lines before changing code.")
        return "\n".join(parts)
