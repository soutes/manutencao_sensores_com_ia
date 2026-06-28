# CLAUDE.md — Manutenção Prescritiva SENAI SC

## O que é este projeto

Sistema de manutenção prescritiva para motores industriais. Recebe eventos de sensores de vibração (JSON), classifica o defeito via RandomForest (acc=0.879), calcula semáforo de criticidade e gera prescrição de correção via RAG sobre manuais técnicos em PDF.

Entregável: case técnico para vaga SENAI/FIESC. Deadline 29/06, entrevista 01/07.

---

## Stack

- **Python 3.14** + Poetry 2.2.1
- **ML**: KNN NearestNeighbors (50 vizinhos, busca por similaridade) + RandomForest (200 árvores, confirmação) — fluxo: similaridade → maioria → prescrição
- **RAG**: TF-IDF + cosine similarity, 61 chunks, 6 PDFs — sem torch/faiss/chromadb
- **LLM**: Ollama local (`qwen2.5:3b`) ou OpenRouter (demo only)
- **Banco**: SQLAlchemy — SQLite (dev/on-prem) ↔ Postgres/Supabase (cloud) via `DATABASE_URL`
- **API**: FastAPI (porta 8000)
- **Dashboard**: Streamlit (porta 8501)
- **Bot**: python-telegram-bot (polling)
- **Docker**: compose com 3 serviços (ollama, api, app) + bot com `profiles: ["bot"]`

---

## Estrutura

```
src/
  core/
    config.py       # variáveis de ambiente + load_dotenv
    faults.py       # normalização 151→17 canônicos + FAULT_LABELS_PT (PT-BR)
    similarity.py   # KNN ponderado por distância
    rag.py          # TF-IDF index + prescribe() + search_all()
    llm.py          # gateway ollama ↔ openrouter (interruptor LGPD)
    backend.py      # responder_evento() + responder_duvida() (banco+RAG+LLM)
    db.py           # SQLAlchemy: Evento, Consulta, StatusHistorico
    pipeline.py     # process_event() end-to-end
    doc_extract.py  # pdfplumber + OCR (tesseract)
  app/
    streamlit_app.py  # 6 abas: Evento|Painel|Eventos|Pendências|Análise|Chat
    ui.py             # design system dark (#10F5A3 accent)
  bot/
    telegram_bot.py   # multi-persona: JSON→semáforo, texto→Q&A
  api/
    main.py           # FastAPI /health /event /chat
artifacts/
  rag.joblib        # índice TF-IDF serializado
  similarity.joblib # scaler + knn model
data/
  fiesc.db          # SQLite (gerado automaticamente)
  banner_clean.parquet
docs/
  Doc1-6.pdf        # manuais técnicos (base do RAG)
tests/              # 125 testes, 124 passando
```

---

## Rodar localmente

```powershell
# instalar dependências
poetry install

# subir Streamlit
poetry run streamlit run src/app/streamlit_app.py

# subir bot Telegram (terminal separado)
poetry run python -m src.bot.telegram_bot

# subir API
poetry run uvicorn src.api.main:app --reload
```

---

## Variáveis de ambiente (.env)

```env
LLM_PROVIDER=ollama              # ollama (produção/LGPD) | openrouter (demo)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b

DATABASE_URL=sqlite:///data/fiesc.db

TELEGRAM_TOKEN=...
TELEGRAM_CHAT_ID=
ALLOWED_USER_IDS=                # user_ids separados por vírgula (privado)
OPENROUTER_API_KEY=
```

---

## Interruptor LGPD

`LLM_PROVIDER` controla onde o conteúdo dos manuais é processado:
- `ollama` → LLM local on-prem, nada sai da empresa **(PRODUÇÃO)**
- `openrouter` → API externa, **somente DEMO com dados sintéticos**

Nenhum dado bruto do payload vai ao LLM — só o nome canônico do defeito.

---

## Semáforo

| Cor | Condição |
|-----|----------|
| 🔴 | sem manual OR freq > 5/sem OR RPM fora de [400, 3800] |
| 🟡 | com manual + baixa freq + RPM normal |
| 🟢 | não é defeito (estado operacional) |

---

## 17 defeitos canônicos

`rolamento`, `rolamento_inner`, `rolamento_outer`, `rolamento_ball`, `rolamento_combination`, `desalinhado`, `desbalanceado`, `correia`, `polia`, `cocked_rotor`, `eccentric_rotor`, `ventoinha`, `falta_fase` + estados: `normal`, `baseline`, `teste`, `acelerando`, `motor_desligado`

Sem manual (sempre 🔴 + pendência): `eccentric_rotor`, `ventoinha`, `falta_fase`

---

## Banco — tabelas

- `eventos`: evento analisado, semáforo, status, frequência, documented
- `consultas`: log de Q&A (pergunta, resposta, defeito, origem)
- `status_historico`: auditoria (quem mudou, de→para, quando, comentário)

Status possíveis: `pendente` | `em_andamento` | `resolvido` | `descartado`

---

## Telegram bot

- `/start` — boas-vindas
- `/myid` — retorna user_id e chat_id
- JSON colado → `responder_evento()` → semáforo + prescrição
- Texto livre → `responder_duvida()` → banco + RAG + LLM
- Privado: restrito a `ALLOWED_USER_IDS`. Grupo: qualquer membro

---

## Testes

```powershell
poetry run pytest -q
# 124/125 passando (1 falha pré-existente: test_fault_doc_map_tem_seis_documentados)
```

---

## Decisões de arquitetura

- **Sem torch/faiss/chromadb**: Python 3.14 incompatível. TF-IDF puro funciona para corpus pequeno (6 docs, 61 chunks).
- **SQLAlchemy abstraction**: troca SQLite↔Postgres sem mudar código, só `DATABASE_URL`.
- **Anti-alucinação**: gating por cobertura — defeito sem documento nunca gera prescrição inventada, registra pendência.
- **`search_all()`**: busca RAG por texto livre sem precisar identificar defeito canônico — usado no chat.
