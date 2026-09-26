from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

import httpx


class LLMProvider(ABC):
    name = "provider"

    @abstractmethod
    async def complete(self, prompt: str, *, system: str = "") -> str: ...


class MockProvider(LLMProvider):
    name = "demo / retrieval"

    async def complete(self, prompt: str, *, system: str = "") -> str:
        return ""


class GeminiProvider(LLMProvider):
    name = "Gemini"

    async def complete(self, prompt: str, *, system: str = "") -> str:
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        body: dict[str, Any] = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", json=body,
                                         headers={"x-goog-api-key": key})
            response.raise_for_status()
            data = response.json()
        return "".join(part.get("text", "") for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []))


class OllamaProvider(LLMProvider):
    name = "Ollama"

    async def complete(self, prompt: str, *, system: str = "") -> str:
        body = {"model": os.getenv("OLLAMA_MODEL", "llama3.2"), "stream": False, "messages": []}
        if system:
            body["messages"].append({"role": "system", "content": system})
        body["messages"].append({"role": "user", "content": prompt})
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/") + "/api/chat", json=body)
            response.raise_for_status()
        return response.json().get("message", {}).get("content", "")


class IBMProvider(LLMProvider):
    name = "IBM watsonx.ai"

    async def complete(self, prompt: str, *, system: str = "") -> str:
        key, project = os.getenv("IBM_API_KEY", ""), os.getenv("IBM_PROJECT_ID", "")
        if not key or not project:
            raise RuntimeError("IBM_API_KEY and IBM_PROJECT_ID are required for watsonx.ai.")
        async with httpx.AsyncClient(timeout=45) as client:
            token_response = await client.post("https://iam.cloud.ibm.com/identity/token", data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": key,
            }, headers={"Content-Type": "application/x-www-form-urlencoded"})
            token_response.raise_for_status()
            token = token_response.json()["access_token"]
            messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
            result = await client.post(os.getenv("IBM_URL", "https://us-south.ml.cloud.ibm.com").rstrip("/") + "/ml/v1/text/chat?version=2023-05-29", json={
                "model_id": os.getenv("IBM_MODEL_ID", "ibm/granite-3-3-8b-instruct"), "project_id": project,
                "messages": messages, "max_tokens": 1000,
            }, headers={"Authorization": f"Bearer {token}"})
            result.raise_for_status()
        return result.json()["choices"][0]["message"]["content"]


def get_provider() -> LLMProvider:
    name = os.getenv("LLM_PROVIDER", "mock").lower()
    classes = {"ibm": IBMProvider, "gemini": GeminiProvider, "ollama": OllamaProvider, "mock": MockProvider, "demo": MockProvider}
    provider = classes.get(name)
    if not provider:
        raise ValueError(f"Unsupported LLM_PROVIDER: {name}")
    return provider()
