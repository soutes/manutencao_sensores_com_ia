# Review Notes — Reviewer (pane 5)
**Data:** 2026-06-27  
**Base:** fundação F0 (código já commitado) + diff atual (só docs/config)  
**Status Wave 1/2/3:** ⬜ todo — revisão antecipada para blindar implementações futuras.

---

## Achados

### ALTA

`src/api/main.py:28-30`: ALTA: /event chama `process_event()` mas NÃO chama `salvar_evento()` — eventos processados pela API não chegam ao banco. Quando B1 criar `backend.py`, a rota deve delegar para `backend.responder_evento()` (que chama o banco) em vez de chamar `process_event()` diretamente. Rota atual quebra o fluxo de persistência antes mesmo de B1 existir.

`src/core/rag.py:111`: ALTA: VAZAMENTO LGPD potencial — `llm_generate(prompt, ...)` envia chunks dos manuais técnicos (conteúdo proprietário) para o provedor ativo. Com `LLM_PROVIDER=openrouter`, esses chunks vão para servidores externos. ADR-002 documenta a intenção ("só demo com dados sintéticos"), mas **não há guard runtime no código**. Uma misconfiguration em produção (`LLM_PROVIDER=openrouter` + dados reais) vaza o conteúdo dos PDFs proprietários sem nenhum aviso. Adicionar: `if LLM_PROVIDER != "ollama" and not os.getenv("FIESC_ALLOW_CLOUD"): raise LLMError("openrouter proibido em producao — defina FIESC_ALLOW_CLOUD=1 para confirmar demo")` ou ao menos log de aviso com o provedor ativo em cada chamada ao RAG.

`src/core/faults.py:97`: ALTA: rótulo `"desconhecido"` → `is_problem=False` — uma falha cujo nome não bate em nenhuma regra de `_canonical` é silenciosamente tratada como estado operacional (sem alerta, sem gating). Deve ser `is_problem=True, documented=False` para disparar semáforo 🔴 e mensagem de "registre documento". Candidato defende mal na entrevista se um fault real é ignorado.

`src/core/db.py` (futura B1): ALTA: `atualizar_status()` ainda não existe — quando B1 implementar, deve obrigatoriamente gravar registro em `status_historico` (evento_id, status_anterior, status_novo, responsavel, data, comentario) **na mesma transação** que atualiza `Evento.status`. Um `UPDATE` sem INSERT em `status_historico` perde a trilha de auditoria. Testar em `tests/test_db.py` que `atualizar_status` grava exatamente 1 linha em `status_historico` por chamada.

`src/core/pipeline.py` + futura B1: ALTA: semáforo de sem-doc — `pipeline.process_event` retorna `documented=False` para `eccentric_rotor`, `ventoinha`, `falta_fase`. A função `_classificar_semaforo()` (B1) deve checar `report["documented"] == False` → 🔴, **independentemente** de `n_similar` ou `frequency_per_week`. Risco: implementação que só olha frequência dá 🟡 para defeito sem manual com poucos eventos recentes.

---

### MÉDIA

`src/core/llm.py:56-61`: MÉDIA: `_openrouter` sem timeout — `client.chat.completions.create(...)` não tem `timeout`. `_ollama` tem `timeout=120` (linha 43). Assimetria: uma request ao OpenRouter pode travar indefinidamente (Telegram/FastAPI bloqueado). Adicionar `timeout=60` no `create()` ou no httpx transport do cliente.

`src/core/rag.py:73`: MÉDIA: `joblib.load(_RAG_PATH)` em cada chamada a `_retrieve` — sem cache em memória. Cada evento recarrega vectorizer + matrix do disco. Com múltiplos eventos simultâneos (Telegram + API) causa leitura repetida de arquivo. Usar variável de módulo `_rag_cache: dict | None = None` e carregar uma vez.

`src/api/main.py:34-38`: MÉDIA: `/chat` chama `prescribe()` sem `salvar_consulta()` — consultas pela API não são persistidas. Inconsistente com o fluxo Telegram (que B2 deve salvar). B1/B2 devem padronizar: toda consulta passa por `backend.responder_duvida()` que grava.

---

### BAIXA

`src/bot/telegram_bot.py:86-90`: BAIXA: `_handle` chama `prescribe()` diretamente sem `salvar_consulta()` — chat do Telegram não persistido. Implementação B2 deve redirecionar para `backend.responder_duvida()`.

`src/core/similarity.py:121`: BAIXA: `frequency_per_week` é média histórica global (`n_total / semanas_dataset`), não contagem da última semana. O semáforo de B1 usa limiar `>5 ocorrências / 7 dias`. Se B1 aplicar o limiar sobre `frequency_per_week` do report, estará comparando magnitudes diferentes — um defeito com 1000 ocorrências ao longo de 2 anos (freq≈10/semana) seria 🔴 mesmo sem nenhum evento recente. B1 deve consultar o banco (eventos dos últimos 7 dias) para o limiar, não `frequency_per_week` do índice KNN.

`src/core/config.py:45`: BAIXA: `EMBED_MODEL = "intfloat/multilingual-e5-base"` declarado mas nunca importado nem usado em nenhum módulo. Sugere embedding neural que não existe no stack. Confunde leitura do código e potencialmente confunde o avaliador. Remover ou comentar como "evolução futura".

---

## Resumo executivo

Nenhum código de Wave 1/2/3 commitado ainda — revisão antecipada. Dois riscos de ALTA na fundação já commitada:

1. **`api/main.py` não persiste eventos** — a rota `/event` deve ser redirecionada para `backend.responder_evento()` em B1.  
2. **`faults.py` silencia defeitos desconhecidos** como estado operacional — `desconhecido` deve ser `is_problem=True, documented=False`.

Um risco de LGPD potencial (`rag.py` sem guard runtime para `openrouter`) que o candidato deve conseguir explicar na entrevista: a proteção é organizacional (variável de ambiente + documentação), não técnica. Adicionar ao menos um `WARNING` de log quando `LLM_PROVIDER=openrouter` é ativado aumenta a defensabilidade.

Para B1: implementar `atualizar_status` + `status_historico` na mesma transação é mandatório para auditoria. Para B1 semáforo: consultar banco para janela 7 dias, não usar `frequency_per_week` do report KNN.

---

**Reviewer marcou R1:** ⬜ (aguardando Q2 ✅ para revisão final do diff completo)
