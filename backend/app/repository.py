from __future__ import annotations

import hashlib
import ast
import io
import json
import re
import shutil
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

import httpx

from .config import DEMO_DIR, IGNORED_DIRS, MAX_FILES, MAX_FILE_BYTES, MAX_REPOSITORY_MB, STORAGE_DIR


LANGUAGES = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".java": "Java", ".go": "Go", ".rs": "Rust", ".c": "C", ".cpp": "C++", ".cs": "C#",
    ".rb": "Ruby", ".php": "PHP", ".sql": "SQL", ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
    ".vue": "Vue", ".svelte": "Svelte", ".kt": "Kotlin", ".swift": "Swift",
}
MAX_TOTAL_BYTES = MAX_REPOSITORY_MB * 1024 * 1024
MAX_ARCHIVE_ENTRIES = MAX_FILES * 4
IGNORED_FILE_NAMES = {
    ".env", ".env.local", ".env.production", "id_rsa", "id_ed25519",
    "credentials", "credentials.json", "secrets.json",
}


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-.")[:70] or "repository"


def extract_github_slug(url: str) -> tuple[str, str]:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"github.com", "www.github.com"}:
        raise ValueError("Only public GitHub HTTPS repository URLs are supported.")
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2 or parts[0].startswith(".") or parts[1].startswith("."):
        raise ValueError("Enter a repository URL such as https://github.com/owner/repository.")
    owner, name = parts[:2]
    name = name.removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", name):
        raise ValueError("The GitHub URL contains an invalid owner or repository name.")
    return owner, name


async def download_github(url: str, token: str = "") -> tuple[str, bytes]:
    owner, name = extract_github_slug(str(url))
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "DevPilot-AI"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    api = f"https://api.github.com/repos/{owner}/{name}"
    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
        response = await client.get(api, headers=headers)
        if response.status_code == 404:
            raise ValueError("Repository not found or not accessible. Check the URL and GitHub token.")
        response.raise_for_status()
        repo = response.json()
        branch = repo.get("default_branch") or "main"
        archive = await client.get(f"https://api.github.com/repos/{owner}/{name}/zipball/{branch}", headers=headers)
        archive.raise_for_status()
        if len(archive.content) > MAX_TOTAL_BYTES:
            raise ValueError(f"Repository archive is larger than the {MAX_REPOSITORY_MB} MB limit.")
    return str(repo.get("full_name") or f"{owner}/{name}"), archive.content


def _copy_filtered(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    count = 0
    total = 0
    for file in source.rglob("*"):
        if not file.is_file():
            continue
        relative = file.relative_to(source)
        if (any(part in IGNORED_DIRS for part in relative.parts)
                or any(part.lower() in IGNORED_FILE_NAMES for part in relative.parts)
                or file.is_symlink()):
            continue
        if file.stat().st_size > MAX_FILE_BYTES or count >= MAX_FILES or total + file.stat().st_size > MAX_TOTAL_BYTES:
            continue
        # Keep only text-like content. Reject NUL bytes and undecodable/binary blobs.
        try:
            sample = file.read_bytes()
            if b"\x00" in sample[:4096]:
                continue
            sample.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(sample)
        count += 1
        total += len(sample)


def copy_demo() -> tuple[str, Path, str]:
    repo_id = "demo-devpilot"
    root = STORAGE_DIR / repo_id
    if root.exists():
        shutil.rmtree(root)
    _copy_filtered(DEMO_DIR, root)
    return repo_id, root, "demo/sample-repository"


def extract_zip(payload: bytes, display_name: str) -> tuple[str, Path]:
    if len(payload) > MAX_TOTAL_BYTES:
        raise ValueError(f"ZIP archive is larger than the {MAX_REPOSITORY_MB} MB limit.")
    repo_id = hashlib.sha256(payload).hexdigest()[:12]
    root = STORAGE_DIR / repo_id
    staging = STORAGE_DIR / f"{repo_id}-extract"
    if root.exists():
        shutil.rmtree(root)
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    written = 0
    file_count = 0
    extracted_paths: set[str] = set()
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ARCHIVE_ENTRIES:
                raise ValueError(f"ZIP archive contains more than {MAX_ARCHIVE_ENTRIES} entries.")
            for entry in entries:
                path = PurePosixPath(entry.filename)
                # ZIP paths use '/', but reject Windows separators and drive prefixes too.
                if (path.is_absolute() or ".." in path.parts or "\\" in entry.filename
                        or re.match(r"^[A-Za-z]:", entry.filename)):
                    raise ValueError("ZIP contains an unsafe absolute or parent-relative path.")
                if entry.is_dir():
                    continue
                clean_parts = path.parts[1:] if len(path.parts) > 1 else path.parts
                if not clean_parts or any(part in IGNORED_DIRS for part in clean_parts):
                    continue
                if any(part.lower() in IGNORED_FILE_NAMES for part in clean_parts):
                    continue
                if entry.flag_bits & 0x1:
                    raise ValueError("Encrypted ZIP entries are not supported.")
                unix_mode = entry.external_attr >> 16
                if unix_mode & 0o170000 == 0o120000:
                    raise ValueError("ZIP symbolic links are not supported.")
                if entry.file_size < 0 or entry.file_size > MAX_FILE_BYTES or entry.file_size > MAX_TOTAL_BYTES - written:
                    raise ValueError("ZIP exceeds the per-file or total extracted size limit.")
                if file_count >= MAX_FILES:
                    raise ValueError(f"ZIP contains more than {MAX_FILES} supported files.")
                clean_name = "/".join(clean_parts)
                if clean_name in extracted_paths:
                    raise ValueError("ZIP contains duplicate file paths.")
                extracted_paths.add(clean_name)
                target = staging.joinpath(*clean_parts).resolve()
                if staging.resolve() not in target.parents:
                    raise ValueError("ZIP entry resolves outside the extraction directory.")
                target.parent.mkdir(parents=True, exist_ok=True)
                # Bound actual decompressed bytes as well as trusting the ZIP header size.
                with archive.open(entry) as source:
                    data = source.read(MAX_FILE_BYTES + 1)
                    if len(data) > MAX_FILE_BYTES or source.read(1):
                        raise ValueError("ZIP entry exceeds the per-file size limit.")
                if len(data) > MAX_TOTAL_BYTES - written:
                    raise ValueError("ZIP exceeds the total extracted size limit.")
                if b"\x00" in data[:4096]:
                    continue
                try:
                    data.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                target.write_bytes(data)
                written += len(data)
                file_count += 1
        if not any(staging.rglob("*")):
            raise ValueError("No supported text files were found in that ZIP.")
        root.parent.mkdir(parents=True, exist_ok=True)
        staging.rename(root)
    except (zipfile.BadZipFile, RuntimeError) as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise ValueError("The upload is not a readable ZIP archive.") from exc
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return repo_id, root


def _detect_framework(all_text: str, filenames: list[str]) -> list[str]:
    checks = [
        ("FastAPI", r"from\s+fastapi\s+import|FastAPI\("), ("Flask", r"from\s+flask\s+import|Flask\("),
        ("Django", r"django\."), ("React", r'"react"\s*:'), ("Next.js", r'"next"\s*:'),
        ("Vue", r'"vue"\s*:'), ("Express", r'"express"\s*:'), ("Node.js", r'"node"\s*:'),
        ("Docker", r"FROM\s+\w+"), ("pytest", r"pytest|unittest"),
    ]
    found = [name for name, pattern in checks if re.search(pattern, all_text, re.I)]
    if not found and any(name == "package.json" for name in filenames):
        found.append("Node.js")
    return found


def _symbol_metadata(path: str, content: str, language: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract source-aware chunks where the language parser can identify symbols."""
    lines = content.splitlines()
    imports: list[dict[str, Any]] = []
    symbols: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    module = str(PurePosixPath(path).with_suffix("")).replace("/", ".")
    if language == "Python":
        try:
            tree = ast.parse(content)
        except SyntaxError:
            tree = None
        if tree:
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend({"module": alias.name, "name": "", "alias": alias.asname or "", "line": node.lineno} for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.extend({"module": node.module or "", "name": alias.name, "alias": alias.asname or "", "line": node.lineno} for alias in node.names)
            classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
            for node in sorted([*classes, *functions], key=lambda item: (item.lineno, item.col_offset)):
                parent_class = next((cls for cls in classes if cls.lineno < node.lineno <= getattr(cls, "end_lineno", cls.lineno)), None)
                symbol = f"{parent_class.name}.{node.name}" if parent_class and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else node.name
                start = min([node.lineno, *(decorator.lineno for decorator in getattr(node, "decorator_list", []))])
                end = getattr(node, "end_lineno", node.lineno)
                row = {"name": symbol, "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                       "line_start": start, "line_end": end}
                symbols.append(row)
                chunks.append({"file_path": path, "language": language, "module": module,
                               "class": parent_class.name if parent_class else "",
                               "function": node.name if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "",
                               "symbol": symbol, "line_start": start, "line_end": end,
                               "chunk_type": "class" if isinstance(node, ast.ClassDef) else ("test" if node.name.startswith("test_") else "function"),
                               "content": "\n".join(lines[start - 1:end])[:12000]})
    elif language in {"JavaScript", "TypeScript"}:
        for match in re.finditer(r"^\s*(?:(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function|class)\s+(\w+)|(?:export\s+)?(?:const|let)\s+(\w+)\s*=)", content, re.M):
            name = match.group(1) or match.group(2)
            line_no = content.count("\n", 0, match.start()) + 1
            row = {"name": name, "kind": "class" if "class " in match.group(0) else "function", "line_start": line_no, "line_end": line_no}
            symbols.append(row)
            chunks.append({"file_path": path, "language": language, "module": module, "class": "",
                           "function": name if row["kind"] == "function" else "", "symbol": name,
                           "line_start": line_no, "line_end": line_no, "chunk_type": "symbol_signature",
                           "content": lines[line_no - 1][:12000] if line_no <= len(lines) else name})
        for line_no, line in enumerate(lines, 1):
            if re.match(r"\s*import\s+", line):
                imports.append({"module": line.strip(), "name": "", "alias": "", "line": line_no})
    if not chunks and content.strip():
        chunks.append({"file_path": path, "language": language, "module": module, "class": "",
                       "function": "", "symbol": "", "line_start": 1,
                       "line_end": max(1, len(lines)), "chunk_type": "file", "content": content[:12000]})
    return symbols, imports, chunks


def analyze_path(root: Path, name: str, source: str, repo_id: str) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    loc = 0
    snippets: list[str] = []
    chunks: list[dict[str, Any]] = []
    dependencies: list[dict[str, str]] = []
    all_text = ""
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(root).as_posix()
        suffix = path.suffix.lower()
        language = LANGUAGES.get(suffix, "Text" if suffix in {".md", ".txt", ".yaml", ".yml", ".json", ".toml"} or path.name in {"Dockerfile", "Makefile", ".gitignore"} else "Other")
        if language in LANGUAGES.values():
            counts[language] = counts.get(language, 0) + 1
        lines = content.splitlines()
        loc += sum(bool(line.strip()) for line in lines)
        symbols, imports, file_chunks = _symbol_metadata(rel, content, language)
        record = {"path": rel, "language": language, "bytes": len(content.encode("utf-8")), "lines": len(lines),
                  "symbols": symbols, "imports": imports}
        files.append(record)
        chunks.extend(file_chunks)
        all_text += f"\n{rel}\n{content[:120000]}"
        if suffix in {".py", ".js", ".jsx", ".ts", ".tsx", ".md", ".json", ".yml", ".yaml", ".sql"}:
            for index, line in enumerate(lines, 1):
                if len(line.strip()) > 12:
                    snippets.append(f"{rel}:{index}: {line[:400]}")
    languages = sorted(counts.items(), key=lambda row: (-row[1], row[0]))
    primary = languages[0][0] if languages else "Unknown"
    filenames = [f["path"].split("/")[-1] for f in files]
    tree = [f["path"] for f in files[:500]]
    entry_points = [f["path"] for f in files if Path(f["path"]).name.lower() in {"main.py", "app.py", "index.ts", "index.js", "server.py", "manage.py", "package.json", "docker-compose.yml"}]
    tests = [f["path"] for f in files if "test" in f["path"].lower() or "spec" in f["path"].lower()]
    configs = [f["path"] for f in files if Path(f["path"]).name in {"package.json", "pyproject.toml", "requirements.txt", "Dockerfile", "docker-compose.yml", "vite.config.ts", "tsconfig.json"}]
    for file in files:
        if Path(file["path"]).name == "requirements.txt":
            try:
                for line in (root / file["path"]).read_text(encoding="utf-8").splitlines():
                    value = line.strip()
                    if value and not value.startswith("#"):
                        dependencies.append({"file": file["path"], "name": re.split(r"[<=>~!\[]", value, maxsplit=1)[0].strip(), "ecosystem": "python"})
            except OSError:
                pass
        elif Path(file["path"]).name == "package.json":
            try:
                manifest = json.loads((root / file["path"]).read_text(encoding="utf-8"))
                for ecosystem, key in (("npm", "dependencies"), ("npm-dev", "devDependencies")):
                    dependencies.extend({"file": file["path"], "name": name, "ecosystem": ecosystem}
                                        for name in manifest.get(key, {}))
            except (OSError, json.JSONDecodeError):
                pass
    apis = sorted(set(re.findall(r"@(?:app|router)\.(?:get|post|put|delete|patch)\(['\"]([^'\"]+)", all_text)))[:80]
    readme = next((Path(f["path"]).name for f in files if Path(f["path"]).name.lower() == "readme.md"), None)
    readme_content = ""
    if readme:
        for file in files:
            if Path(file["path"]).name.lower() == "readme.md":
                try:
                    readme_content = (root / file["path"]).read_text(encoding="utf-8")[:6000]
                except OSError:
                    pass
                break
    components = sorted({f["path"].split("/")[0] for f in files if "/" in f["path"]})
    return {
        "id": repo_id, "name": name, "source": source, "file_count": len(files), "loc": loc,
        "languages": [{"name": lang, "files": n} for lang, n in languages], "primary_language": primary,
        "frameworks": _detect_framework(all_text, filenames), "tree": tree, "files": files,
        "entry_points": entry_points, "test_files": tests, "config_files": configs,
        "api_endpoints": apis, "components": components, "readme": readme_content,
        "chunks": chunks[:MAX_FILES * 12], "dependencies": dependencies[:2000],
        "has_tests": bool(tests), "has_docs": bool(readme),
        "snippet_index": snippets[:15000],
    }


def read_repo_file(repo: dict[str, Any], relative: str) -> str:
    root = Path(repo["root"]).resolve()
    target = (root / relative).resolve()
    if root != target and root not in target.parents:
        raise ValueError("Path is outside the repository.")
    if not target.is_file():
        raise ValueError("File was not found in this repository.")
    return target.read_text(encoding="utf-8")[:120_000]
