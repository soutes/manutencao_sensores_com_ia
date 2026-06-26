# Manutenção Prescritiva — SENAI SC

Solução de manutenção **prescritiva** para máquinas rotativas: dado um novo evento de
sensor (vibração), o sistema (1) encontra ocorrências históricas similares, (2) reporta
quantidade / frequência / distribuição temporal e (3) recupera o procedimento de correção
nos documentos da empresa via RAG + LLM. Se o defeito não tem documento, instrui o usuário
a registrar um novo.

## Arquitetura

```
Sensor/PLC ──(JSON)──> FastAPI /event ──> core.pipeline.process_event
                                              │
                          ┌───────────────────┼───────────────────┐
               similaridade (FAISS)     gating cobertura      RAG (Chroma+LLM)
               banner.csv histórico     defeito tem doc?      procedimentos PDF
                                              │
                          ┌───────────────────┴───────────────────┐
                     Streamlit dashboard                   Telegram report bot
```

- **core/**: lógica pura (sem UI). `faults`, `similarity`, `rag`, `llm`, `pipeline`.
- **api/**: FastAPI expõe o core.
- **app/**: dashboard + chat Streamlit.
- **bot/**: bot Telegram (report push + chat).

### Restrição de hardware
Inferência roda em estação 32GB RAM / GPU 16GB → LLM local (Ollama, modelo quantizado).
Backend plugável (`LLM_BACKEND=ollama|api`) — ver `core/config.py`.

## Cobertura de defeitos (gating)
| Defeito canônico | Documento |
|---|---|
| rolamento_inner/outer/ball/combination | Doc1 (OCR) |
| desalinhado | Doc2 |
| desbalanceado | Doc3 |
| correia | Doc4 |
| polia | Doc5 |
| cocked_rotor | Doc6 |
| **eccentric_rotor, ventoinha, falta_fase** | **sem doc → registrar** |

Estados (não-defeito): normal, baseline, teste, acelerando, motor_desligado.

## Setup
```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
# OCR: instalar tesseract + poppler no SO
# LLM: ollama pull qwen2.5:7b

python scripts/build_all.py          # constrói índices (similaridade + RAG)
uvicorn api.main:app --app-dir src   # API
streamlit run src/app/streamlit_app.py
```

## Dados
- `docs/banner.csv` — 166.796 eventos, 23 features de vibração + `fault` + `rpm`.
- `data/banner_clean.parquet` — processado, com `fault_canonical` / `is_problem` / `documented`.
- 151 rótulos brutos → 17 canônicos (normalização de variantes + typos em `core/faults.py`).
