from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import BASE_DIR, DEMO_DIR
from .repository import analyze_path
from .retrieval import retrieve


def run_benchmark() -> dict[str, Any]:
    benchmark = json.loads((BASE_DIR / "evaluation" / "benchmark.json").read_text(encoding="utf-8"))
    repo = analyze_path(DEMO_DIR, "DevPilot Demo", "demo/sample-repository", "evaluation-demo")
    cutoff = int(benchmark.get("cutoff", 5))
    rows = []
    for case in benchmark["cases"]:
        results = retrieve(repo, case["query"], limit=cutoff)
        file_hit = any(item["file"] == case["expected_file"] for item in results)
        symbol = case.get("expected_symbol", "")
        symbol_hit = any(item.get("symbol") == symbol for item in results) if symbol else None
        rows.append({"id": case["id"], "query": case["query"], "expected_file": case["expected_file"],
                     "expected_symbol": symbol or None, "retrieved_files": list(dict.fromkeys(item["file"] for item in results)),
                     "file_hit": file_hit, "symbol_hit": symbol_hit,
                     "citations_valid": all(item.get("line_start", 0) > 0 and item.get("line_end", 0) >= item.get("line_start", 0) and item.get("file") for item in results)})
    total = len(rows) or 1
    symbol_rows = [row for row in rows if row["expected_symbol"]]
    return {"benchmark": benchmark["name"], "cutoff": cutoff, "case_count": len(rows),
            "metrics": {"expected_file_hit_rate": round(sum(row["file_hit"] for row in rows) / total, 4),
                        "expected_symbol_hit_rate": round(sum(bool(row["symbol_hit"]) for row in symbol_rows) / max(1, len(symbol_rows)), 4),
                        "labeled_symbol_cases": len(symbol_rows),
                        "citation_line_validity": round(sum(row["citations_valid"] for row in rows) / total, 4)},
            "cases": rows, "limitations": "Measures retrieval against bundled expected file and symbol labels; it does not grade generated answer correctness."}
