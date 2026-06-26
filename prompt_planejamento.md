# 🧠 Etapa 1 — PLANEJAMENTO (sequencial, antes do tmux)

Pensar antes de construir. Roda em **uma sessão `claude`** (ou em panes, mas em ordem).
Produz só **artefatos** (PRD, ADRs, backlog) — **nenhum código**. Ao fim, a Etapa 2
(execução em tmux) usa esses artefatos.

Pré-requisito: ler `CONTEXTO.md` e `prompt_agents.md` (papéis e guardrails).

Ordem: **Fase 0 (PO) → Fase 1 (Arquiteto) → Fase 2 (Lead)**. Aprove cada uma antes da próxima.

---

## 📋 Fase 0 — PRODUCT OWNER (gera o PRD + User Stories)

Cole num `claude` na pasta do projeto:

```
Aja como PRODUCT OWNER do projeto de Manutenção Prescritiva (case FIESC).
Leia CONTEXTO.md e prompt_agents.md antes de tudo. NÃO escreva código.

Gere docs/PRD.md (em português, profissional):
1. Visão e problema (máquinas rotativas, manutenção prescritiva, on-prem/LGPD).
2. Objetivos e métricas de sucesso (5 diferenciais; gating sem-doc; anti-alucinação;
   acurácia de similaridade; latência aceitável; offline-capaz).
3. Personas: Operador (campo, Telegram) e Engenheiro de Manutenção (estação, Streamlit).
4. Escopo in/out (out: treinar visão computacional, multi-planta, auth complexa).
5. Requisitos funcionais e não-funcionais (LGPD, 32GB/16GB, dois perfis).
6. User Stories em docs/user-stories/US-NNN-*.md (uma por arquivo), cada uma:
   "Como <persona>, quero <ação>, para <valor>" + critérios de aceite (Given/When/Then)
   + prioridade MoSCoW.
7. Backlog priorizado + riscos.

Cubra: ingestão de evento JSON via Telegram → análise → feedback; Q&A sobre
histórico/pendências; gating "sem documento → registrar"; duas frentes (remota/local);
interruptor LGPD; persistência no banco.

Ao terminar: liste os arquivos criados e uma tabela das User Stories (ID, título, MoSCoW).
```

➡️ Revise o PRD. Ajuste prioridades se preciso. Só então siga.

---

## 🏛️ Fase 1 — ARQUITETO (gera as ADRs)

```
Aja como ARQUITETO. Leia CONTEXTO.md, prompt_agents.md e docs/PRD.md. NÃO escreva código.

Gere ADRs em docs/adr/ no formato MADR (Contexto, Decisão, Alternativas consideradas,
Consequências). Uma por decisão NÃO-óbvia:
- ADR-001 Stack leve sem faiss/torch/chromadb (Python 3.14): KNN sklearn + TF-IDF.
- ADR-002 Interruptor LGPD: LLM_PROVIDER ollama(local) ↔ openrouter(cloud).
- ADR-003 Banco trocável SQLite ↔ Postgres/Supabase via SQLAlchemy.
- ADR-004 Anti-alucinação: prompt restrito ao contexto + gating de cobertura.
- ADR-005 Similaridade por busca (KNN ponderado por distância) e não classificação treinada.
- ADR-006 Deploy 2 alvos: Docker on-prem + HF Spaces cloud (por que não Vercel).

Cada ADR curta e objetiva, com o trade-off explícito. Liste as ADRs criadas ao final.
```

➡️ Revise as ADRs (são a sua munição de "justificativa técnica" na entrevista).

---

## 🧭 Fase 2 — TECH LEAD (backlog + STATUS.md inicial)

```
Aja como TECH LEAD. Leia CONTEXTO.md, prompt_agents.md, docs/PRD.md e docs/adr/.
NÃO escreva código de feature.

Gere docs/STATUS.md no formato da seção 3 do prompt_agents.md, traduzindo as User Stories
prioritárias (Must/Should) em tarefas executáveis, com: ID, tarefa, dono (papel),
estado (⬜), dependências e ARQUIVOS DISJUNTOS por dono. Garanta que nenhum par de tarefas
paralelas compartilhe arquivo. Defina as waves (o que roda junto, o que espera).

Gere também docs/EXECUCAO_PLANO.md: resumo de qual pane do tmux faz o quê, em que ordem,
e os critérios de "pronto para integrar". Liste o backlog final.
```

➡️ Com PRD + ADRs + STATUS.md + plano prontos, o **planejamento acabou**. Vá para
[`prompt_execucao.md`](prompt_execucao.md) e abra o tmux.

---

## Checklist do Planejamento
- [ ] `docs/PRD.md` aprovado
- [ ] `docs/user-stories/US-*.md` com critérios de aceite + MoSCoW
- [ ] `docs/adr/ADR-*.md` (decisões justificadas)
- [ ] `docs/STATUS.md` com tarefas, donos, dependências e arquivos disjuntos
- [ ] `docs/EXECUCAO_PLANO.md` com as waves
