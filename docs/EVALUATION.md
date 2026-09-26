# Retrieval evaluation

The benchmark at `evaluation/benchmark.json` contains ten labeled questions for the bundled sample repository. `GET /api/evaluation/run` re-indexes that fixture and runs the current retrieval implementation for every case.

It reports: expected-file hit rate at the configured cutoff, expected-symbol hit rate for cases with a symbol label (cases without one count as not applicable/pass), and citation line validity for returned results. Per-case expected and retrieved files are returned for inspection.

These measurements describe retrieval behavior only. They do not measure whether a generated explanation is correct, whether every citation supports a claim, or how the system performs on other repositories. Save the live endpoint output with each release; do not copy expected results into reports as if they were measured.
