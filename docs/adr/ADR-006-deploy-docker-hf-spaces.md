# ADR-006 — Containerização Docker + Deploy (On-Prem e HF Spaces)

**Status:** Aceita
**Data:** 2026-06-26
**Autores:** Arquiteto

---

## Contexto

O sistema tem dois alvos de deploy: (1) ambiente industrial on-premises e (2) demo pública
para a banca avaliadora sem instalação local. Ambos exigem ambiente Python reproduzível
com dependências de sistema (tesseract, poppler para OCR/PDF).

Dependências Python são gerenciadas via Poetry (ADR-007). O Dockerfile precisa instalar
deps de sistema + deps Python de forma determinística e reproduzível.

---

## Decisão

### Containerização: Docker + Docker Compose

```dockerfile
# Dockerfile — padrão Poetry em Docker
FROM python:3.14-slim

# deps de sistema para OCR (tesseract) e PDF (poppler)
RUN apt-get update && apt-get install -y \
    tesseract-ocr tesseract-ocr-por \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Poetry sem virtualenv (contêiner já é isolado)
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=0 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN pip install poetry

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root && rm -rf $POETRY_CACHE_DIR

COPY . .
```

```yaml
# docker-compose.yml — 3 serviços
services:
  api:
    build: .
    command: poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000
    ports: ["8000:8000"]
    env_file: .env
    volumes: ["./data:/app/data"]   # banco SQLite persiste no host

  streamlit:
    build: .
    command: poetry run streamlit run src/app/streamlit_app.py --server.port 8501
    ports: ["8501:8501"]
    env_file: .env
    depends_on: [api]

  telegram:
    build: .
    command: poetry run python src/bot/telegram_bot.py
    env_file: .env
    depends_on: [api]
```

### Deploy cloud: Hugging Face Spaces (Streamlit SDK)

- Perfil cloud: `LLM_PROVIDER=openrouter`, `DATABASE_URL` Supabase
- HF Spaces suporta `pyproject.toml` via Poetry nativo ou `requirements.txt` exportado
  (`poetry export -f requirements.txt --without-hashes > requirements.txt`)

---

## Alternativas Consideradas

### Vercel (rejeitado)

| Razão | Detalhe |
|---|---|
| Serverless, sem estado | Cada invocação = processo novo; modelos sklearn não persistem em memória |
| Sem suporte a Streamlit | Vercel roda Next.js/React; Streamlit exige processo Python stateful |
| Cold start | `NearestNeighbors` fit() em 166k amostras a cada request = inaceitável |
| Timeout | Funções serverless: timeout em segundos; LLM local leva 57s |

### pip + requirements.txt (rejeitado para dep management — ver ADR-007)

| Razão | Detalhe |
|---|---|
| Sem lockfile determinístico | `pip install -r requirements.txt` não garante sub-deps iguais |
| Sem grupos dev/prod | Instala ferramentas de test em produção |
| Poetry export resolve | `poetry export` gera requirements.txt para HF Spaces se necessário |

### Render / Railway

| Razão | Detalhe |
|---|---|
| Viável tecnicamente | Suportam Docker + Poetry |
| Menos visível | HF Spaces tem descoberta orgânica para projetos de ML |

### HF Spaces (escolhido para demo)

| Vantagem | Detalhe |
|---|---|
| Streamlit nativo | SDK Streamlit suportado de fábrica |
| Gratuito | Tier CPU gratuito suficiente com OpenRouter |
| Visibilidade | Comunidade ML; link público profissional |
| Secrets | Chaves via interface HF (não ficam no repo) |

---

## Consequências

**Positivas:**
- `docker compose up` = ambiente completo em 1 comando (diferencial avaliado)
- Poetry lock + Dockerfile reproduzível: qualquer avaliador obtém o mesmo ambiente
- Volume `./data` persiste banco SQLite entre restarts do contêiner on-prem
- Mesmo Dockerfile para on-prem e (se necessário) cloud — só muda env vars

**Negativas / Trade-offs:**
- HF Spaces gratuito reinicia contêiner → banco SQLite perdido; usar Supabase para persistência
- HF Spaces não roda Ollama → demo usa OpenRouter (aceito: dados sintéticos)
- `poetry install` na build pode ser lento na primeira vez; mitigado por cache de layer Docker
  (copiar `pyproject.toml` + `poetry.lock` antes do `COPY . .`)
