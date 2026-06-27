# STATUS — Fonte Única de Coordenação

> Todos os agentes leem e atualizam este arquivo. Marque `🟦 doing` ao iniciar, `✅` ao concluir.
> Regra: se `Depende` não está `✅`, a tarefa fica `🟥 bloqueado`.

## Legenda
⬜ todo · 🟦 doing · 🟨 review · ✅ done · 🟥 bloqueado

---

## Fundação (já concluída — NÃO reeditar)

| ID | Componente | Estado | Arquivo(s) |
|----|-----------|--------|-----------|
| F0-01 | `normalize_fault` (151→17 canônicos) | ✅ | `src/core/faults.py` |
| F0-02 | KNN ponderado (acc 0.74 holdout) | ✅ | `src/core/similarity.py` |
| F0-03 | RAG TF-IDF + OCR (61 chunks, 6 docs) | ✅ | `src/core/rag.py`, `src/core/doc_extract.py` |
| F0-04 | Gating "sem documento" | ✅ | `src/core/pipeline.py` |
| F0-05 | Pipeline end-to-end (4 casos testados) | ✅ | `src/core/pipeline.py` |
| F0-06 | FastAPI + rotas base | ✅ | `src/api/main.py` |
| F0-07 | Streamlit (sintaxe + modo demo) | ✅ | `src/app/streamlit_app.py` |
| F0-08 | Telegram bot (código base) | ✅ | `src/bot/telegram_bot.py` |
| F0-09 | Banco SQLAlchemy (3 tabelas, 3 eventos) | ✅ | `src/core/db.py` |
| F0-10 | Gateway LLM ollama↔openrouter | ✅ | `src/core/llm.py`, `src/core/config.py` |
| F0-11 | LLM redige prescrição (qwen2.5:3b, 57s) | ✅ | `src/core/llm.py` |
| F0-12 | Docker + compose (tesseract+poppler) | ✅ | `Dockerfile`, `docker-compose.yml` |

---

## Wave 1 — Paralelo (Backend ∥ UI/UX ∥ QA)

| ID | Tarefa | Dono | Estado | Depende | Arquivos (exclusivos) |
|----|--------|------|--------|---------|----------------------|
| B1 | `responder_evento()` com semáforo + `responder_duvida()` com banco+RAG; novas funções db: `atualizar_status()`, `serie_temporal_resolvidos()`, `resumo_semaforo()`, tabela `status_historico` | Backend | ✅ | — | `src/core/backend.py`, `src/core/db.py` |
| U1 | `ui.py`: design system + `kpi_semaforo()`, `badge_status()`, `form_edicao_status()` | UI/UX | ✅ | — | `src/app/ui.py` |
| Q1 | Notebook EDA: distribuição, métricas KNN, matriz de confusão, insights | QA | ✅ | — | `notebooks/analise.ipynb` |

> **Arquivos disjuntos garantidos:** B1 ↔ U1 ↔ Q1 não compartilham nenhum arquivo.

---

## Wave 2 — Paralelo (Backend B2 ∥ Frontend F1)

| ID | Tarefa | Dono | Estado | Depende | Arquivos (exclusivos) |
|----|--------|------|--------|---------|----------------------|
| B2 | Telegram: JSON→semáforo, Q&A status parque (banco+RAG), multi-persona | Backend | ✅ | B1 ✅ | `src/bot/telegram_bot.py` |
| F1 | Dashboard: KPIs semáforo, série temporal resolvidos, tabela editável, pendências, distribuição por defeito | Frontend | ✅ | U1 ✅, B1 ✅ | `src/app/streamlit_app.py` |

> **Arquivos disjuntos garantidos:** B2 (bot) ↔ F1 (streamlit) não compartilham arquivo.

---

## Wave 3 — Sequencial (QA → Reviewer → Lead)

| ID | Tarefa | Dono | Estado | Depende | Arquivos |
|----|--------|------|--------|---------|---------|
| Q2 | Smoke test end-to-end: Telegram → backend → banco → resposta | QA | ✅ | B2 ✅, F1 ✅ | `tests/test_api.py`, `tests/test_backend.py`, `tests/test_db.py`, `tests/test_semaforo.py`, `tests/test_telegram.py` |
| R1 | Review LGPD: gateway, gating, prompt restritivo, contratos | Reviewer | ✅ | Q2 ✅ | — (leitura apenas) |
| L1 | Integração final: commit, tag v1.0, docker compose smoke test | Tech Lead | ⬜ | R1 ✅ | — |

---

## Wave 4 — Deploy e Vitrine (Could)

| ID | Tarefa | Dono | Estado | Depende | Arquivos |
|----|--------|------|--------|---------|---------|
| D1 | Configurar Supabase + OpenRouter (perfil cloud) | Tech Lead | ⬜ | L1 ✅ | `.env`, `docker-compose.yml` |
| D2 | HF Spaces deploy (Streamlit + Supabase + OpenRouter) | Tech Lead | ⬜ | D1 ✅ | `README.md` |
| D3 | Diagrama de arquitetura (mermaid no README) | Tech Lead | ⬜ | L1 ✅ | `README.md` |

---

## Critérios de "Pronto para Integrar" (DoD por wave)

### Wave 1 pronta quando:
- [ ] B1: `responder_evento` e `responder_duvida` retornam resposta correta em smoke test local
- [ ] U1: `ui.py` exporta componentes sem erro; preview no Streamlit OK
- [ ] Q1: notebook executa do início ao fim sem erro; todas as métricas aparecem

### Wave 2 pronta quando:
- [ ] B2: bot recebe JSON no Telegram, retorna prescrição, grava no banco
- [ ] F1: dashboard carrega histórico e pendências; design system aplicado

### Wave 3 pronta quando:
- [ ] Q2: fluxo completo testado (JSON in → prescrição out + banco atualizado)
- [ ] R1: sem severidade alta no review LGPD
- [ ] L1: `docker compose up` sobe tudo sem erro; tag v1.0 criada
