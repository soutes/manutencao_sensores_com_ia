# 🤖 Time de Agentes — Índice e Regras Comuns

Projeto **Manutenção Prescritiva (FIESC)** conduzido como consultoria especialista.
O processo é dividido em **duas etapas separadas**:

| Etapa | Arquivo | Modo | Quem |
|---|---|---|---|
| 🧠 **Planejamento** | [`prompt_planejamento.md`](prompt_planejamento.md) | sequencial, 1 sessão | PO → Arquiteto → Lead |
| 🛠️ **Execução** | [`prompt_execucao.md`](prompt_execucao.md) | paralelo em **tmux** | Backend ∥ Front ∥ UI/UX ∥ QA ∥ Reviewer |

> Faça **todo o planejamento primeiro** (PRD, ADRs, backlog). Só então abra o tmux para a
> execução. Não misture as etapas.

Este arquivo guarda o que é **comum às duas**: papéis, guardrails, status board e DoD.

---

## 1. Princípios (guardrails — valem nas duas etapas)

1. **NÃO recomeçar do zero.** O repo já tem MVP funcionando. Todo agente lê `CONTEXTO.md`
   primeiro e **evolui** o que existe. Proibido reescrever módulos prontos sem motivo.
2. **Contratos são lei.** Não mudar assinaturas de `core.pipeline.process_event`,
   `core.similarity`, `core.rag.prescribe`, `core.llm.llm_generate`, `core.db.*` sem ADR.
3. **Paralelismo = arquivos disjuntos.** Dois agentes nunca editam o mesmo arquivo. A
   matriz de propriedade de arquivos está em `prompt_execucao.md`.
4. **Interruptor LGPD intocável.** `LLM_PROVIDER` (ollama/openrouter) e `DATABASE_URL`
   (sqlite/supabase) são a fronteira. Conteúdo de manual só sai no perfil cloud.
5. **Nível defensável.** Código no nível que o candidato domina (`CONTEXTO.md` §10). Nada
   "esperto demais" que ele não consiga explicar na entrevista. Comentar o porquê.
6. **Português** em código, docstrings, commits e artefatos.
7. **Fonte única de coordenação = `docs/STATUS.md`.** Quem inicia uma tarefa a marca
   `🟦 doing` com seu nome; ao concluir, `✅`. Leia o board antes de pegar tarefa.
8. **Honestidade.** QA/Reviewer não maquiam: teste que falha é reportado com a saída real.

---

## 2. Papéis (RACI)

| Papel | Responsabilidade | Entregáveis | Etapa |
|---|---|---|---|
| 📋 **Product Owner** | requisitos, prioridade MoSCoW, critérios de aceite | `docs/PRD.md`, `docs/user-stories/` | Planejamento |
| 🏛️ **Arquiteto** | decisões técnicas com trade-offs | `docs/adr/ADR-NNN-*.md` | Planejamento |
| 🧭 **Tech Lead** | backlog, atribui arquivos, integra, commita, mantém `STATUS.md` | backlog, integração, releases | ambas |
| ⚙️ **Backend** | FastAPI, pipeline, db, llm, telegram | `src/api`, `src/core/backend.py`, `src/bot` | Execução |
| 🎨 **Frontend** | dashboard Streamlit | `src/app/streamlit_app.py` | Execução |
| ✨ **UI/UX** | design system, layout, usabilidade | `src/app/ui.py` | Execução |
| 🧪 **QA** | testes, métricas, casos de borda | `tests/`, `notebooks/` | Execução |
| 🔍 **Reviewer** | review, segurança/LGPD, simplicidade | comentários de review | Execução |

> **PRD é do Product Owner.** Ele decide gerar User Stories (sim) e quais ADRs são
> necessárias (delega a decisão ao Arquiteto).

---

## 3. Quadro de status (`docs/STATUS.md`) — coração da coordenação

Como os painéis do tmux são processos **independentes** (não compartilham contexto), a
coordenação acontece por **arquivo**. Cada agente lê e atualiza este board.

```markdown
# STATUS — fonte única de coordenação (todos editam a sua linha)
## Legenda: ⬜ todo · 🟦 doing · 🟨 review · ✅ done · 🟥 bloqueado

| ID | Tarefa                          | Dono     | Estado | Depende | Arquivos                 |
|----|---------------------------------|----------|--------|---------|--------------------------|
| B1 | responder_evento/responder_duvida | Backend  | ⬜     | —       | src/core/backend.py      |
| B2 | Telegram → backend + DB         | Backend  | ⬜     | B1      | src/bot/telegram_bot.py  |
| U1 | Design system (portar ui.py)    | UI/UX    | ⬜     | —       | src/app/ui.py            |
| F1 | Dashboard vestido + pendências  | Frontend | ⬜     | U1, B1  | src/app/streamlit_app.py |
| Q1 | Notebook EDA+métricas+confusão  | QA       | ⬜     | —       | notebooks/analise.ipynb  |
| Q2 | Testes (api/backend/pipeline/db) | QA      | ⬜     | B1,B2   | tests/test_*.py          |
| R1 | Review LGPD + contratos         | Reviewer | ⬜     | B*,F*   | docs/review_notes.md     |
```

**Regra de claim:** antes de editar, mude o Estado para `🟦 doing`. Se `Depende` não está
`✅`, NÃO comece (fica `🟥 bloqueado` aguardando).

---

## 4. Definition of Done (DoD)

- [ ] Roda sem erro (`PYTHONIOENCODING=utf-8`), com smoke test.
- [ ] Não quebra contratos nem o interruptor LGPD.
- [ ] Comentado no nível defensável (porquê das escolhas).
- [ ] `docs/STATUS.md` atualizado para `✅`.
- [ ] Passou pelo Reviewer sem severidade alta aberta.

---

## 5. Ordem geral

```
PLANEJAMENTO (sequencial)        EXECUÇÃO (tmux, paralelo)
  PO → PRD + User Stories          Wave 1: Backend(B1) ∥ UI/UX(U1) ∥ QA(Q1)
  Arquiteto → ADRs                 Wave 2: Backend(B2) ∥ Frontend(F1, após U1)
  Lead → backlog + STATUS.md       QA testa → Reviewer revisa → Lead integra/commita
```

Detalhes de cada etapa nos arquivos próprios.
