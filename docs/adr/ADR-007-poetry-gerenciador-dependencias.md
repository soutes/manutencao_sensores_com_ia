# ADR-007 — Poetry como Gerenciador de Dependências

**Status:** Aceita
**Data:** 2026-06-26
**Autores:** Arquiteto

---

## Contexto

O projeto usa Python 3.14 com dependências de ML (sklearn, pymupdf, rapidocr), web
(fastapi, streamlit, python-telegram-bot), banco (sqlalchemy) e utilitários (pandas, httpx).
Precisa de:
- Instalação reproduzível (dev, CI, Docker, avaliador) — mesmo resultado em qualquer máquina
- Separação deps de produção vs. desenvolvimento/testes
- Integração limpa com Docker (ADR-006) sem sobrecarga de binários desnecessários
- `pyproject.toml` como fonte única de metadados do projeto (nome, versão, deps, scripts)

---

## Decisão

Usar **Poetry** como gerenciador de dependências e empacotamento.

### Estrutura de grupos

```toml
[tool.poetry.dependencies]
python = "^3.14"
fastapi = "*"
uvicorn = {extras = ["standard"], version = "*"}
streamlit = "*"
python-telegram-bot = "*"
sqlalchemy = "*"
scikit-learn = "*"
pandas = "*"
pymupdf = "*"
rapidocr-onnxruntime = "*"
httpx = "*"

[tool.poetry.group.dev.dependencies]
pytest = "*"
pytest-asyncio = "*"
ipykernel = "*"   # notebooks
jupyterlab = "*"
```

### Comandos principais

```bash
poetry install              # instala main + dev (desenvolvimento)
poetry install --only main  # só produção (Docker)
poetry run uvicorn ...      # roda sem ativar venv manualmente
poetry export -f requirements.txt --without-hashes > requirements.txt  # ambientes só-pip
poetry add <pacote>         # adiciona e atualiza lock
```

### Scripts de conveniência no pyproject.toml

```toml
[tool.poetry.scripts]
api   = "src.api.main:start"
app   = "src.app.streamlit_app:start"
bot   = "src.bot.telegram_bot:start"
```

---

## Alternativas Consideradas

| Alternativa | Por que rejeitada |
|---|---|
| `pip` + `requirements.txt` | Sem lockfile determinístico de sub-deps; sem grupos dev/prod; sem resolução de conflitos |
| `conda` / `mamba` | Pesado; não integra com PyPI wheel de `rapidocr`; Docker image grande |
| `uv` (Astral) | Mais rápido, mas suporte Python 3.14 e ecossistema ainda madurando; Poetry é mais defensável na entrevista |
| `pipenv` | Obsolescência relativa; comunidade migrou para Poetry/uv |
| `hatch` | Menos adoção; comportamento de lock menos maduro que Poetry |

---

## Consequências

**Positivas:**
- `poetry.lock` garante builds idênticos em qualquer máquina — avaliador obtém mesmo resultado
- Grupo `dev` mantém pytest/jupyter fora da imagem Docker de produção
- `pyproject.toml` substitui `setup.py`, `setup.cfg`, `requirements.txt`, `requirements-dev.txt`
- `poetry run <cmd>` elimina necessidade de ativar venv manualmente
- Integração Docker: `COPY pyproject.toml poetry.lock ./` antes do `COPY . .`
  → camada de deps é cacheada; rebuild só quando deps mudam

**Negativas / Trade-offs:**
- `poetry install` é mais lento que `pip install` em primeira execução
  — mitigado por cache de layer Docker e `$POETRY_CACHE_DIR`
- Alguns ambientes que só leem `requirements.txt` não consomem `pyproject.toml` nativo
  — resolver com `poetry export > requirements.txt` quando necessário
- Python 3.14 pode ter wheels faltando para alguns pacotes
  — Poetry resolve com fallback para sdist; stack leve (ADR-001) minimiza risco

**Relação com ADR-006 (Docker):**
```dockerfile
# Padrão recomendado — cache de layer eficiente
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root && rm -rf $POETRY_CACHE_DIR
COPY . .
```
