from __future__ import annotations

import asyncio

import httpx

from app import main


def test_anonymous_github_reads_never_send_server_token(monkeypatch):
    captured: dict[str, object] = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return [{"number": 7, "title": "Public issue", "body": "Details", "labels": [],
                     "state": "open", "html_url": "https://github.com/example/project/issues/7", "user": {"login": "reporter"}}]

    class Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, headers):
            captured["url"] = url
            captured["headers"] = headers
            return Response()

    monkeypatch.setenv("GITHUB_TOKEN", "server-secret-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "example/project")
    monkeypatch.setattr(httpx, "AsyncClient", Client)

    result = asyncio.run(main._github_list("issues"))

    assert result["items"][0]["number"] == 7
    assert "Authorization" not in captured["headers"]
