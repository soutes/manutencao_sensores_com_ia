# 🤖 Time de Agentes — Playbook de Desenvolvimento (Claude Code CLI)

Playbook para conduzir o projeto **Manutenção Prescritiva (FIESC)** como uma consultoria
especialista: papéis definidos, fases de SDLC, build em paralelo, status vivo e checklist.

> **Como usar:** cole o **PROMPT MESTRE** (seção 6) num `claude` novo dentro da pasta do
> projeto. Ele inicia o Tech Lead, que conduz as fases e delega aos demais agentes.
> Para rodar uma fase isolada, use os blocos copia-e-cola da seção 7.

---

## 1. Princípios (guardrails — leia antes)

1. **NÃO recomeçar do zero.** O repo já tem MVP funcionando. Todo agente lê `CONTEXTO.md`
   primeiro e **evolui** o que existe. Proibido reescrever módulos prontos sem motivo.
2. **Contratos são lei.** Não mudar assinaturas públicas de `core.pipeline.process_event`,
   `core.similarity`, `core.rag.prescribe`, `core.llm.llm_generate`, `core.db.*` sem ADR.
3. **Paralelismo = arquivos disjuntos.** Dois agentes nunca editam o mesmo arquivo ao mesmo
   tempo. O Lead atribui propriedade de arquivos. Integração é do Lead.
4. **Interruptor LGPD intocável.** `LLM_PROVIDER` (ollama/openrouter) e `DATABASE_URL`
   (sqlite/supabase) continuam sendo a fronteira. Conteúdo de manual só sai no perfil cloud.
5. **Nível defensável.** Código no nível que o candidato domina (ver `CONTEXTO.md` §10).
   Nada "esperto demais" que ele não consiga explicar na entrevista. Comentar o porquê.
6. **Português** em código, docstrings, commits e artefatos.
7. **Commit por fase**, mensagem clara. Atualizar `docs/STATUS.md` ao fim de cada tarefa.
8. **Honestidade.** QA/Reviewer não maquiam: se um teste falha, reporta com a saída real.

---

## 2. Papéis (RACI)

| Papel | Responsabilidade | Entregáveis |
|---|---|---|
| 🧭 **Tech Lead** (orquestrador) | Coordena, quebra em tarefas, atribui arquivos, integra, commita, mantém `STATUS.md` | backlog, integração, releases |
| 📋 **Product Owner** | Visão de produto, requisitos, prioridade (MoSCoW), critérios de aceite | `docs/PRD.md`, `docs/user-stories/` |
| 🏛️ **Arquiteto** | Decisões técnicas com trade-offs e consequências | `docs/adr/ADR-NNN-*.md` |
| ⚙️ **Backend** | FastAPI, pipeline, db, llm gateway, telegram | código `src/api`, `src/core`, `src/bot` |
| 🎨 **Frontend** | Dashboard Streamlit (frente local) | `src/app/streamlit_app.py` |
| ✨ **UI/UX** | Design system, layout, usabilidade, heurísticas | `src/app/ui.py` (CSS/componentes) |
| 🧪 **QA** | Testes, métricas (holdout/confusão), casos de borda, validação | `tests/`, relatório de QA |
| 🔍 **Reviewer** | Revisão de código, segurança/LGPD, consistência, anti-scope-creep | comentários de review |

> O **Product Owner** é o responsável pelo PRD. Ele decide se gera User Stories (sim, neste
> caso) e quais ADRs são necessárias (delega a decisão técnica ao Arquiteto).

---

## 3. Fases (fluxo de uma empresa especialista)

```
Fase 0  Discovery   → PO: PRD + User Stories + critérios de aceite
Fase 1  Arquitetura → Arquiteto: ADRs das decisões (stack leve, 2 perfis, LGPD, gating)
Fase 2  Planejamento→ Lead: backlog (tarefas), donos, arquivos, STATUS.md inicial
Fase 3  Build       → Backend ∥ Frontend ∥ UI/UX (paralelo, arquivos disjuntos)
Fase 4  QA          → QA: testes + métricas + casos de borda
Fase 5  Review      → Reviewer: correção, LGPD, simplicidade
Fase 6  Integração  → Lead: integra, testa end-to-end, commita, atualiza STATUS
```

Repete Fase 3–6 por incremento (épico) até o backlog fechar.

---

## 4. Quadro de status (`docs/STATUS.md`)

Cada agente atualiza sua linha ao mudar de estado. Formato:

```markdown
# STATUS — atualizado por todos os agentes

## Legenda: ⬜ todo · 🟦 doing · 🟨 review · ✅ done · 🟥 bloqueado

| ID  | Tarefa                          | Dono     | Estado | Arquivos                 | Nota |
|-----|---------------------------------|----------|--------|--------------------------|------|
| B1  | responder_evento/responder_duvida | Backend  | ⬜     | src/core/backend.py      |      |
| B2  | Telegram ligado ao backend+DB   | Backend  | ⬜     | src/bot/telegram_bot.py  |      |
| U1  | Portar design system (ui.py)    | UI/UX    | ⬜     | src/app/ui.py            |      |
| F1  | Dashboard vestido + pendências  | Frontend | ⬜     | src/app/streamlit_app.py |      |
| Q1  | Notebook EDA+métricas+confusão  | QA       | ⬜     | notebooks/analise.ipynb  |      |
| R1  | Review LGPD + contratos         | Reviewer | ⬜     | —                        |      |
```

O Lead consolida e mostra o quadro a cada rodada.

---

## 5. Definition of Done (DoD)

Uma tarefa só é ✅ quando:
- [ ] Roda sem erro (`PYTHONIOENCODING=utf-8`), smoke test incluso.
- [ ] Não quebra contratos nem o interruptor LGPD.
- [ ] Comentada no nível defensável (porquê das escolhas).
- [ ] `docs/STATUS.md` atualizado.
- [ ] Passou pelo Reviewer (Fase 5) sem severidade alta aberta.

---

## 6. PROMPT MESTRE — cole isto num `claude` novo

```
Você é o TECH LEAD de um time de agentes desenvolvendo o projeto de Manutenção
Prescritiva (case FIESC). Trabalhe como uma consultoria especialista.

PASSO 0 — Contexto obrigatório antes de qualquer ação:
1. Leia CONTEXTO.md (visão, arquitetura, stack, o que já existe, nível do candidato).
2. Leia prompt_agents.md (este playbook: papéis, fases, guardrails, DoD, status).
3. NÃO recomece nada: o repo já tem MVP funcionando. Evolua o que existe.

REGRAS:
- Respeite os guardrails da seção 1 do prompt_agents.md (contratos, interruptor LGPD,
  paralelismo só em arquivos disjuntos, português, nível defensável, commit por fase).
- Você coordena; delega aos papéis via subagentes (Task tool). Para paralelizar, dispare
  vários subagentes na MESMA mensagem, cada um dono de arquivos DISJUNTOS.
- Mantenha docs/STATUS.md como quadro vivo. Commit ao fim de cada fase.

EXECUTE AS FASES NA ORDEM:
- Fase 0: acione o PRODUCT OWNER para gerar docs/PRD.md + docs/user-stories/ (com
  critérios de aceite e prioridade MoSCoW). Pare e me mostre o PRD para aprovação.
- Após aprovação: Fase 1 (Arquiteto → docs/adr/ADR-NNN), Fase 2 (backlog + STATUS),
  Fase 3 (build paralelo Backend ∥ Frontend ∥ UI/UX), Fase 4 (QA), Fase 5 (Reviewer),
  Fase 6 (integração + commit). Repita 3–6 por incremento até fechar o backlog.

Comece pela Fase 0 agora. Ao fim de cada fase, mostre o quadro docs/STATUS.md e aguarde
meu "ok" para a próxima.
```

---

## 7. Prompts por fase (copia-e-cola individuais)

### 📋 Fase 0 — PRODUCT OWNER (gera o PRD)

```
Aja como PRODUCT OWNER do projeto de Manutenção Prescritiva (case FIESC).
Leia CONTEXTO.md e prompt_agents.md antes.

Gere docs/PRD.md (Product Requirements Document) profissional, em português, contendo:
1. Visão e problema (indústria rotativa, manutenção prescritiva, on-prem/LGPD).
2. Objetivos e métricas de sucesso (ex: cobre os 5 diferenciais; gating sem doc;
   anti-alucinação; acc de similaridade; latência aceitável).
3. Personas: Operador (campo, Telegram) e Engenheiro de Manutenção (estação, Streamlit).
4. Escopo (in/out). Out: treinar modelo novo de visão, multi-planta, auth complexa.
5. Requisitos funcionais e não-funcionais (LGPD, 32GB/16GB, offline-capaz).
6. User Stories em docs/user-stories/US-NNN-*.md (uma por arquivo OU um índice), cada uma:
   "Como <persona>, quero <ação>, para <valor>", + critérios de aceite (Given/When/Then),
   + prioridade MoSCoW (Must/Should/Could/Won't).
7. Backlog priorizado e riscos.

Cubra explicitamente: ingestão de evento JSON via Telegram → análise → feedback;
Q&A sobre histórico/pendências; gating "sem documento → registrar"; duas frentes
(remota/local); interruptor LGPD; persistência no banco.

NÃO escreva código. Só os artefatos de produto. Ao terminar, liste os arquivos criados
e um resumo das User Stories (ID + título + prioridade).
```

### 🏛️ Fase 1 — ARQUITETO (gera ADRs)

```
Aja como ARQUITETO. Leia CONTEXTO.md, prompt_agents.md e docs/PRD.md.
Gere ADRs em docs/adr/ (formato MADR: Contexto, Decisão, Alternativas, Consequências),
uma por decisão NÃO-óbvia já tomada ou a tomar. Candidatas:
- ADR-001 Stack leve sem faiss/torch/chromadb (Python 3.14) — KNN sklearn + TF-IDF.
- ADR-002 Interruptor LGPD: LLM_PROVIDER ollama(local) ↔ openrouter(cloud).
- ADR-003 Banco trocável SQLite ↔ Postgres/Supabase via SQLAlchemy.
- ADR-004 Anti-alucinação: prompt restrito ao contexto + gating de cobertura.
- ADR-005 Similaridade por busca (KNN ponderado) em vez de classificação treinada.
- ADR-006 Deploy 2 alvos: Docker on-prem + HF Spaces cloud (não Vercel).
Cada ADR curta e objetiva. NÃO mude código. Liste as ADRs criadas ao final.
```

### ⚙️/🎨/✨ Fase 3 — BUILD (o Lead dispara em paralelo, arquivos disjuntos)

```
[BACKEND] Implemente src/core/backend.py com responder_evento(event:dict)->dict
(process_event + db.salvar_evento + monta feedback) e responder_duvida(texto:str)->dict
(interpreta pergunta → consulta db.listar_pendencias/historico_defeito + rag.prescribe →
resposta). Depois ligue src/bot/telegram_bot.py a essas funções (ingestão JSON + Q&A,
gravando origem='telegram'). Não toque em similarity.py/rag.py/streamlit_app.py/ui.py.
Smoke test em scripts/. Atualize docs/STATUS.md.

[UI/UX] Crie src/app/ui.py portando o design system do PlanejAI
(C:/Users/luiz_/_DS/Analista_Financeiro/src/ui.py): tema escuro, accent, glow KPI box,
barras, alertas, ícones — adaptado a "defeito/ocorrências/pendência". Só este arquivo.

[FRONTEND] Reescreva src/app/streamlit_app.py usando ui.py: KPIs em glow box, gráfico
temporal, instruções, alerta amarelo no gating, aba pendências (db.listar_pendencias),
dashboard geral, chat. Mantenha o modo demo. Só este arquivo. Depende de ui.py (UI/UX).

[QA] Crie notebooks/analise.ipynb estilo EDA: distribuição de falhas, holdout
acc/f1 (k=1,5,15), matriz de confusão, confusão eccentric↔desbalanceado, insights
escritos. Use data/banner_clean.parquet. Só notebooks/ e tests/.
```

### 🧪 Fase 4 — QA / 🔍 Fase 5 — REVIEW

```
[QA] Rode todos os smoke tests e o pipeline end-to-end (eventos com-doc, sem-doc, estado).
Reporte tabela: caso → esperado → obtido → passou?. Liste casos de borda e bugs com a
saída real. NÃO corrija — só reporte.

[REVIEWER] Revise o diff da fase. Uma linha por achado:
path:linha: <severidade> problema. correção. Foque em: contratos quebrados, vazamento
LGPD (manual indo pra cloud no perfil errado), erros de robustez, e simplicidade
(algo difícil de defender na entrevista). Sem elogios. Sem scope creep.
```

---

## 8. Checklist de execução (Lead acompanha)

### Processo
- [ ] Fase 0 — PRD aprovado + User Stories
- [ ] Fase 1 — ADRs registradas
- [ ] Fase 2 — backlog + STATUS.md inicial
- [ ] Fase 3 — build paralelo concluído
- [ ] Fase 4 — QA com relatório
- [ ] Fase 5 — Review sem severidade alta aberta
- [ ] Fase 6 — integrado, commitado, STATUS atualizado

### Produto (incrementos)
- [ ] B1 backend responder_evento/responder_duvida
- [ ] B2 Telegram → backend + DB (ingestão JSON + Q&A pendências/histórico)
- [ ] U1 design system ui.py portado
- [ ] F1 dashboard vestido + aba pendências
- [ ] Q1 notebook EDA + métricas + matriz de confusão
- [ ] D1 relatório prescritivo narrativo estruturado (JSON)
- [ ] Cloud: Supabase + OpenRouter (perfil online)
- [ ] Deploy: Docker on-prem + HF Spaces
- [ ] Diagrama de arquitetura + simulador PLC (MQTT)
- [ ] README + preview/mockup + slides

---

## 9. Como rodar agentes em paralelo no Claude Code (prático)

- **Paralelo real:** o Lead chama várias vezes a ferramenta de subagente **na mesma
  mensagem**. Cada subagente recebe arquivos DISJUNTOS (seção 1, regra 3).
- **Persistência:** subagentes em background podem morrer se o processo reinicia. Para
  trabalho que precisa persistir, o Lead roda em primeiro plano e commita por fase.
- **Agentes customizados (opcional):** crie `.claude/agents/<papel>.md` com a descrição de
  cada papel para reuso (o candidato já usa esse padrão no PlanejAI).
- **Integração:** subagente NÃO faz merge nem commit final — quem integra é o Lead, que
  entende cada peça (essencial para a defesa na entrevista).
