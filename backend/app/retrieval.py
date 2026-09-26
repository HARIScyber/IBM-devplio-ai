from __future__ import annotations

import re
from typing import Any


STOP = {"what", "where", "when", "does", "this", "that", "with", "from", "into", "about", "have", "which", "would", "could", "should", "does", "repo", "repository", "explain", "show", "find"}


def retrieve(repo: dict[str, Any], query: str, limit: int = 6) -> list[dict[str, Any]]:
    terms = [word.lower() for word in re.findall(r"[A-Za-z_][A-Za-z0-9_]{1,}", query) if word.lower() not in STOP]
    scored = []
    chunks = repo.get("chunks", [])
    for row in chunks:
        path = row.get("file_path", "")
        body = row.get("content", "")
        symbol = row.get("symbol", "")
        text = (body + " " + path + " " + symbol + " " + row.get("module", "")).lower()
        tokens = set(re.findall(r"[a-z_][a-z0-9_]{1,}", text))
        score = sum(2 if term in tokens else 0 for term in terms)
        score += sum(1 for term in terms if term in text)
        if score:
            start, end = row.get("line_start", 1), row.get("line_end", row.get("line_start", 1))
            scored.append({"file": path, "line": start, "line_start": start, "line_end": end,
                           "symbol": symbol, "language": row.get("language", ""),
                           "chunk_type": row.get("chunk_type", "file"), "excerpt": body.strip(), "score": score})
    if not chunks:
        for row in repo.get("snippet_index", []):
            path, _, line = row.partition(":")
            body = line.partition(":")[2].lower()
            tokens = set(re.findall(r"[a-z_][a-z0-9_]{1,}", body + " " + path.lower()))
            score = sum(2 if term in tokens else 0 for term in terms) + sum(1 for term in terms if term in body)
            if score:
                path, line_no, excerpt = row.split(":", 2)
                scored.append({"file": path, "line": int(line_no), "line_start": int(line_no),
                               "line_end": int(line_no), "symbol": "", "excerpt": excerpt.strip(), "score": score})
    scored.sort(key=lambda item: (-item["score"], item["file"], item["line"]))
    # Prefer a few distinct files so answers explain relationships, while retaining useful multi-line excerpts.
    result: list[dict[str, Any]] = []
    per_file: dict[str, int] = {}
    for item in scored:
        if per_file.get(item["file"], 0) >= 2:
            continue
        result.append(item)
        per_file[item["file"]] = per_file.get(item["file"], 0) + 1
        if len(result) >= limit:
            break
    return result
