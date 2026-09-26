from pathlib import Path

from app.analysis import make_tests, scan_repository


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_ROOT = PROJECT_ROOT / "demo" / "sample-repository"


def test_demo_sample_contains_evidence_backed_scanner_examples():
    repo = {
        "root": str(SAMPLE_ROOT),
        "files": [{"path": "backend/demo_smells.py"}],
    }

    findings = scan_repository(repo)

    assert [(item["title"], item["line"]) for item in findings] == [
        ("Wildcard CORS origin", 4),
        ("Unresolved TODO marker", 6),
    ]


def test_test_generator_auto_selects_a_python_module_with_public_functions():
    repo = {
        "root": str(SAMPLE_ROOT),
        "files": [
            {"path": "backend/__init__.py", "language": "Python"},
            {"path": "backend/auth.py", "language": "Python"},
            {"path": "tests/test_tasks.py", "language": "Python"},
        ],
    }

    draft = make_tests(repo)

    assert draft["language"] == "Python"
    assert draft["file"] == "tests/test_auth.py"
    assert "from backend.auth import find_account, token_is_valid, normalize_email" in draft["code"]
    assert "assert callable(find_account)" in draft["code"]
    compile(draft["code"], draft["file"], "exec")
