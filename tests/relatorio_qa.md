# Relatorio QA — Wave 3 (Q2)

**Data:** 2026-06-27
**Executado por:** QA Agent
**Comando:** `python -m pytest -q --tb=short`

---

## Resumo executivo

| Metrica | Valor |
|---------|-------|
| Total de testes | 125 |
| Passando | 124 |
| Falhando | 1 (pre-existente) |
| Novos testes adicionados | 70 |
| Cobertura de modulos | `backend`, `db`, `api`, `semaforo`, `telegram_bot` |

---

## Arquivos de teste criados (Q2)

| Arquivo | Testes | Modulo coberto |
|---------|--------|----------------|
| `tests/test_semaforo.py` | 10 | `core.backend._classificar_semaforo` |
| `tests/test_db.py` | 18 | `core.db` (salvar, listar, atualizar, resumo, historico) |
| `tests/test_backend.py` | 17 | `core.backend` (intencao, responder_evento, responder_duvida) |
| `tests/test_api.py` | 8 | `api.main` (/health, /event, /chat) |
| `tests/test_telegram.py` | 17 | `bot.telegram_bot` (formatadores, _is_json_event) |

---

## Resultado por modulo

### test_semaforo.py — 10/10 PASS

Logica de semaforo validada:
- Verde: estado normal (is_problem=False)
- Amarelo: defeito documentado + freq <= 5 + rpm normal
- Vermelho: sem doc OR freq > 5 OR rpm fora de [400, 3800]
- Limiar freq=5.0 -> amarelo; freq=5.1 -> vermelho (PASS)

### test_db.py — 18/18 PASS

Banco SQLite in-memory por fixture (`tmp_path`). Coberto:
- `salvar_evento`: id retornado, status pendente/ok correto por is_problem
- `listar_pendencias`: filtra apenas status=pendente
- `atualizar_status`: retorna True/False, semaforo vira verde ao resolver, audit em status_historico
- `resumo_semaforo`: contagens 🔴/🟡/🟢 corretas
- `serie_temporal_resolvidos`: retorna lista com campos dia/resolvidos/abertos
- `historico_defeito`: filtra por defeito, retorna lista com campo status
- `salvar_consulta`: nao levanta excecao

### test_backend.py — 17/17 PASS

Imports locais (lazy imports dentro de funcoes) patchados nas fontes:
- `core.pipeline.process_event` (nao `core.backend.process_event`)
- `core.db.*` diretamente (nao `core.backend.db`)
- `core.rag.prescribe` (nao `core.backend.prescribe`)

Cenarios cobertos:
- `_detectar_intencao`: 9 frases → 4 intencoes (status_parque, pendencias, historico, tecnica)
- `_extrair_defeito_texto`: direto, typo, desconhecido
- `responder_evento`: campos obrigatorios, semaforo vermelho sem doc, vermelho com rpm anormal
- `responder_duvida`: status_parque, pendencias, historico, tecnica (RAG)

### test_api.py — 8/8 PASS

FastAPI TestClient. Coberto:
- `GET /health` -> 200, `{"status": "ok"}`
- `POST /event`: 200, campos obrigatorios presentes, payload vazio aceito
- `POST /chat`: sem fault, com fault valido (SimpleNamespace com `__dict__`), retorna dict

> **Nota tecnica:** `prescribe().__dict__` na rota `/chat` requer objeto com `__dict__` real.
> Usar `SimpleNamespace` nos mocks, nao `type("P", (), {...})()` (instancia com atributos de classe nao popula `__dict__`).

### test_telegram.py — 17/17 PASS

Sem conexao real ao Telegram. Coberto:
- `_semaforo_titulo`: 🔴/🟡/🟢/desconhecido
- `_is_json_event`: JSON valido, texto livre, JSON invalido, vazio, lista (nao dict)
- `format_event_report`: semaforo, defeito, instrucoes, estado normal, sem doc (alerta), id_salvo
- `format_duvida_response`: resposta, fonte, sem fonte

---

## Falha pre-existente

| Arquivo | Teste | Causa |
|---------|-------|-------|
| `tests/test_faults.py` | `test_fault_doc_map_tem_seis_documentados` | Teste esperava 6 defeitos documentados; `FAULT_DOC_MAP` atual tem 10 (familia rolamento tem 5 subfamilias + rolamento generico, todos com Doc1.pdf). Teste foi escrito para versao anterior do mapa. |

**Nao introduzido por Q2.** Recomendacao: atualizar o teste para `len(documentados) == 10` ou agrupar por documento (6 PDFs distintos).

---

## Cobertura de fluxo end-to-end

```
JSON sensor → POST /event → process_event (mock) → _classificar_semaforo → salvar_evento (mock)
                                                        ↓ semaforo
                        ← {report, semaforo, id_salvo}

Texto livre → responder_duvida → _detectar_intencao
                                    ├── status_parque → db.resumo_semaforo (mock)
                                    ├── pendencias    → db.listar_pendencias (mock)
                                    ├── historico     → db.historico_defeito (mock)
                                    └── tecnica       → rag.prescribe (mock) → RAG
```

---

## Observacoes / Riscos

1. **Sem KNN real nos testes de backend/api:** `process_event` sempre mockado. KNN real testado apenas em `test_pipeline.py` (Wave 1). Aceitavel para smoke test.
2. **Telegram bot nao tem teste de handler async** (`_handle`, `_start`): requer `python-telegram-bot` + event loop. Cobertos indiretamente via formatadores.
3. **DB in-memory por teste:** isolamento correto, mas nao testa migracoes (`_apply_migrations`) em DB pre-existente.
4. **Falha pre-existente FAULT_DOC_MAP:** deve ser corrigida antes de L1 (integracao final).
