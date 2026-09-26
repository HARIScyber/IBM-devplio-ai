from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DEMO_DIR = BASE_DIR / "demo" / "sample-repository"
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "backend" / "storage"))).resolve()
MAX_REPOSITORY_MB = int(os.getenv("MAX_REPOSITORY_MB", "30"))
MAX_FILE_BYTES = 512_000
MAX_FILES = 1500
IGNORED_DIRS = {".git", "node_modules", "__pycache__", "dist", "build", ".venv", "venv", "coverage", ".next", "vendor"}
TEXT_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".c", ".h", ".cpp", ".cs",
    ".rb", ".php", ".swift", ".kt", ".scala", ".sql", ".sh", ".yml", ".yaml", ".toml", ".json",
    ".md", ".mdx", ".txt", ".html", ".css", ".scss", ".xml", ".ini", ".cfg", ".env.example",
    ".dockerfile", ".gitignore", ".lock", ".tf", ".proto",
}
