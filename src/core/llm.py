"""Abstracao do LLM: backend plugavel (local Ollama ou API externa).

A solucao final deve rodar em estacao com 32GB RAM / GPU 16GB (enunciado, sec.5).
Default = Ollama local (cabe quantizado). API e opcional para desenvolvimento.
"""
from __future__ import annotations
from .config import LLM_BACKEND, LLM_MODEL, OLLAMA_HOST


def llm_generate(prompt: str, system: str | None = None) -> str:
    """Gera texto. Troca de backend so por variavel de ambiente LLM_BACKEND."""
    if LLM_BACKEND == "ollama":
        return _ollama(prompt, system)
    if LLM_BACKEND == "api":
        return _api(prompt, system)
    raise ValueError(f"LLM_BACKEND invalido: {LLM_BACKEND}")


def _ollama(prompt: str, system: str | None) -> str:
    import requests
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    r = requests.post(f"{OLLAMA_HOST}/api/chat",
                      json={"model": LLM_MODEL, "messages": msgs, "stream": False},
                      timeout=120)
    r.raise_for_status()
    return r.json()["message"]["content"]


def _api(prompt: str, system: str | None) -> str:
    """TODO(opcional): backend API (OpenAI/Anthropic/Gemini). Mesma assinatura."""
    raise NotImplementedError("Configurar backend API se desejar.")
