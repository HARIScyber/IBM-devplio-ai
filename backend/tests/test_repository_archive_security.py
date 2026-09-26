from __future__ import annotations

import io
import zipfile

import pytest

from app import repository


def _zip(entries: list[tuple[str, bytes]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return output.getvalue()


def test_extract_zip_rejects_parent_traversal_and_cleans_staging(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "STORAGE_DIR", tmp_path)
    with pytest.raises(ValueError, match="unsafe"):
        repository.extract_zip(_zip([("repo/../../escaped.py", b"x")]), "upload.zip")
    assert not (tmp_path.parent / "escaped.py").exists()
    assert not list(tmp_path.glob("*-extract"))


def test_extract_zip_rejects_duplicate_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "STORAGE_DIR", tmp_path)
    with pytest.raises(ValueError, match="duplicate"):
        repository.extract_zip(_zip([("repo/app.py", b"first"), ("repo/app.py", b"second")]), "upload.zip")


def test_extract_zip_enforces_supported_file_count(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(repository, "MAX_FILES", 1)
    with pytest.raises(ValueError, match="supported files"):
        repository.extract_zip(_zip([("repo/one.py", b"1"), ("repo/two.py", b"2")]), "upload.zip")


def test_extract_zip_ignores_secret_files(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "STORAGE_DIR", tmp_path)
    repo_id, root = repository.extract_zip(
        _zip([("repo/.env", b"secret=should-not-index"), ("repo/app.py", b"print('ok')")]), "upload.zip"
    )
    assert (root / "app.py").is_file()
    assert not (root / ".env").exists()
