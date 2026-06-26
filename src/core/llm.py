"""Gateway de LLM com provedor plugavel — o "interruptor LGPD".

LLM_PROVIDER decide onde o conteudo do manual (RAG) e processado:
  - "ollama"     -> modelo LOCAL on-prem. Nada sai da empresa. Producao/LGPD.
  - "openrouter" -> API externa (OpenAI-compatible). So DEMO com dados sinteticos.

Mesma interface (`llm_generate`) nos dois. Trocar = mudar uma variavel de ambiente.
Esta abstracao E o mecanismo de conformidade: em producao roda local; na demo,
roda na nuvem com dados de teste.
"""
from __future__ import annotations
from .config import (LLM_PROVIDER, OLLAMA_HOST, OLLAMA_MODEL,
                    OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL)


class LLMError(RuntimeError):
    pass


def provider_label() -> str:
    """Rotulo legivel do provedor ativo (p/ UI e auditoria)."""
    if LLM_PROVIDER == "ollama":
        return f"Ollama local · {OLLAMA_MODEL} (on-prem)"
    if LLM_PROVIDER == "openrouter":
        return f"OpenRouter · {OPENROUTER_MODEL} (cloud)"
    return LLM_PROVIDER


def llm_generate(prompt: str, system: str | None = None) -> str:
    if LLM_PROVIDER == "ollama":
        return _ollama(prompt, system)
    if LLM_PROVIDER == "openrouter":
        return _openrouter(prompt, system)
    raise LLMError(f"LLM_PROVIDER invalido: {LLM_PROVIDER}")


def _ollama(prompt: str, system: str | None) -> str:
    import requests
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    r = requests.post(f"{OLLAMA_HOST}/api/chat",
                      json={"model": OLLAMA_MODEL, "messages": msgs, "stream": False},
                      timeout=120)
    r.raise_for_status()
    return r.json()["message"]["content"]


def _openrouter(prompt: str, system: str | None) -> str:
    if not OPENROUTER_API_KEY:
        raise LLMError("OPENROUTER_API_KEY ausente. Configure no .env (perfil cloud).")
    from openai import OpenAI
    client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(model=OPENROUTER_MODEL, messages=msgs,
                                          temperature=0.2)
    return resp.choices[0].message.content or ""
