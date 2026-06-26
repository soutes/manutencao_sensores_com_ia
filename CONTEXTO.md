# CONTEXTO DO PROJETO — Manutenção Prescritiva (Case SENAI/FIESC)

> Documento de contexto e plano de ataque. Atualizado conforme o projeto evolui.
> Processo seletivo 01747/2026 — Analista P&D Pleno. **Deadline: 29/06/2026 14h.**
> Alvo pessoal: domingo 28/06 18h. Entrevista: 01/07.

---

## 1. O PROBLEMA (o quê / pra quem / por quê)

Indústria grande de SC tem máquinas rotativas com **sensores de vibração**. Quer sair da
manutenção reativa para **manutenção prescritiva**: o sistema não só prevê que a máquina
vai falhar, mas **diz como corrigir** — buscando a solução nos **manuais da empresa**.

**Fluxo desejado:** chega um evento novo (JSON de sensor) → sistema acha casos
históricos parecidos → reporta quantas vezes ocorreu, frequência, distribuição no tempo →
busca o procedimento de correção nos documentos → entrega a ação recomendada.
**Se não existe documento para o defeito, NÃO inventa: pede para registrar um documento.**

Avaliam: interpretação do problema, qualidade, organização, versionamento, documentação,
diferenciais, e na entrevista: **domínio dos conceitos, justificativa, alucinação do modelo**.

---

## 2. AS DUAS TÉCNICAS (o coração)

1. **Similaridade** (achar padrões nos sensores): cada evento = 23 números (impressão
   digital da vibração). KNN acha os históricos mais parecidos → defeito provável +
   estatísticas. NÃO é classificação treinada, é busca por semelhança.
2. **RAG** (buscar nos manuais): recupera os trechos relevantes dos PDFs e o LLM redige a
   correção **só com base nesses trechos** (anti-alucinação). Se não há manual → avisa.

A sacada é **costurar as duas**: similaridade diz O QUE é; RAG diz COMO corrigir.

---

## 3. ARQUITETURA DECIDIDA — DUAS FRENTES + INTERRUPTOR LGPD

```
Operador (Telegram, campo) ─┐                 ┌─ Engenheiro (Streamlit, estação local)
                            ▼                 ▼
                   ┌──────────────────────────────────┐
                   │   BACKEND FastAPI (o "cérebro")   │
                   │  pipeline: similaridade → RAG     │
                   │  → gateway LLM → grava no banco   │
                   └──────────────────────────────────┘
                            │                 │
                   LLM gateway          Banco trocável
                (interruptor LGPD)    (camada SQLAlchemy)
```

**Interruptor LGPD** = variável `LLM_PROVIDER`:
- `ollama` → LLM **local on-prem**, conteúdo do manual NÃO sai da empresa (PRODUÇÃO/LGPD).
- `openrouter` → API externa, **só DEMO com dados sintéticos** do case.

**Banco trocável** = `DATABASE_URL`:
- SQLite local (on-prem/offline) ↔ Postgres/Supabase (cloud, persiste a demo).

As abstrações (gateway + camada de banco) **SÃO** a resposta de LGPD — mecanismo, não slide.
Mesmo código roda local (seguro) ou nuvem (demo). Espelha o padrão `config_ia` do PlanejAI.

---

## 4. STACK (leve de propósito — Python 3.14 sem faiss/torch/chromadb)

| Camada | Escolha | Por quê |
|---|---|---|
| Similaridade | sklearn `NearestNeighbors` + voto ponderado | sem faiss; 166k×23 resolve em ms |
| RAG retriever | sklearn `TfidfVectorizer` + cosseno | sem torch; corpus pequeno (6 docs) |
| OCR (Doc1 escaneado) | `pymupdf` + `rapidocr-onnxruntime` | OCR sem binário de SO |
| LLM | gateway `ollama` ↔ `openrouter` | interruptor LGPD |
| Banco | SQLAlchemy (SQLite ↔ Supabase) | trocável por connection string |
| API | FastAPI | diferencial |
| Dashboard | Streamlit (+ design system do PlanejAI) | diferencial |
| Integração | Telegram bot | diferencial industrial |
| Deploy | Docker (on-prem) + HF Spaces (cloud) | NÃO Vercel (serverless não roda ML pesado) |

---

## 5. DADOS

- `docs/banner.csv` — 166.796 eventos, 23 features de vibração + `fault` + `rpm`.
- `data/banner_clean.parquet` — processado (`fault_canonical`, `is_problem`, `documented`).
- **151 rótulos brutos → 17 canônicos** (normalização de typos+variantes), 0 desconhecidos.
- Cobertura de documentos:
  - COM doc: rolamento (Doc1, OCR), desalinhado (Doc2), desbalanceado (Doc3),
    correia (Doc4), polia (Doc5), cocked_rotor (Doc6).
  - SEM doc (→ registrar): eccentric_rotor, ventoinha, falta_fase.
  - Estados (não-defeito): normal, baseline, teste, acelerando, motor_desligado.

---

## 6. O QUE JÁ FOI FEITO ✅

| Componente | Estado | Validação |
|---|---|---|
| `normalize_fault` | ✅ | 151→17, 0 desconhecidos |
| Similaridade (KNN ponderado) | ✅ | holdout acc **0.74** |
| RAG + OCR dos 6 manuais | ✅ | 61 chunks |
| Gating "sem documento" | ✅ | dispara p/ eccentric/ventoinha |
| Pipeline end-to-end | ✅ | 4 casos OK |
| FastAPI | ✅ | testado (TestClient) |
| Dashboard Streamlit | ✅ | sintaxe + modo demo |
| Telegram bot (código) | ✅ | escrito |
| Banco SQLAlchemy (eventos/consultas/pendências) | ✅ | 3 eventos gravados |
| Gateway LLM (ollama↔openrouter) | ✅ | rótulo de provedor OK |
| **LLM redige a prescrição (Ollama qwen2.5:3b)** | ✅ | prescrição fiel ao Doc6, 57s na CPU |
| Docker + compose | ✅ | tesseract+poppler |

**Commits:** `e2c090b` scaffold → `25e8f9e` pipeline → `53703bf` fundação 2 frentes →
`be9a11c` contexto → `5b061fe` perfis env. Ollama instalado (qwen2.5:3b), servidor local OK.

---

## 7. INSIGHTS TÉCNICOS (munição p/ entrevista)

- **k=1 dá acc 0.74; k alto degrada** → classes de defeito se sobrepõem.
- **KNN confunde `eccentric_rotor` ↔ `desbalanceado`** (vibração fisicamente parecida).
  Corrigido com **voto ponderado por distância**. (Mostra que medi e ajustei.)
- Doc1 era escaneado → sem OCR, perderíamos o manual do defeito MAIS comum (rolamento).
- Anti-alucinação = prompt restrito ao contexto recuperado **+** gating de cobertura.

---

## 8. PLANO DE ATAQUE (ordem)

1. ✅ Fundação: banco trocável + gateway LLM.
2. ⬜ Backend: `responder_evento(json)` e `responder_duvida(texto)` (histórico/pendências + RAG).
3. ⬜ Telegram ligado ao backend (ingestão JSON + Q&A) → grava no banco.
4. ⬜ LLM estruturado (JSON) + **relatório prescritivo narrativo** (estilo do app financeiro).
5. ⬜ Dashboard vestido com o **design system** do PlanejAI (`ui.py`).
6. ⬜ **Notebook de análise** estilo BlackFriday (EDA + similaridade + métricas + insights).
7. ⬜ Supabase (perfil cloud) + OpenRouter key.
8. ⬜ Deploy: Docker (on-prem) + HF Spaces (cloud demo).
9. ⬜ Diagrama de arquitetura + simulador de PLC (MQTT) + README/preview.

Itens 2–6 = o "produto". 7–9 = vitrine.

---

## 9. CHECKLIST

### Diferenciais
- [x] APIs (FastAPI)
- [x] Banco de Dados (SQLAlchemy / SQLite, Supabase pluga)
- [x] Dashboards (Streamlit — falta vestir)
- [x] Deploy (Docker on-prem — falta cloud HF Spaces)
- [~] Integração industrial (Telegram feito — falta diagrama MQTT/OPC-UA + simulador)

### Critérios de avaliação
- [x] Interpretação do problema
- [x] Pipeline completo de IA
- [x] Gating "sem documento" (requisito crítico)
- [x] Controle de alucinação (prompt restrito + gating)
- [x] Versionamento (commits incrementais)
- [~] Documentação (README ok; falta diagrama + notebook)
- [ ] Relatório/insights apresentável (notebook estilo BlackFriday)
- [x] LLM redigindo de verdade (Ollama qwen2.5:3b local)
- [ ] Demo ao vivo testada (dashboard no navegador + Telegram com token)
- [ ] Slides da entrevista

---

## 10. NÍVEL DE PYTHON / REFERÊNCIAS

- Nível DS do candidato (notebook `Exec_BlackFriday.ipynb`): intermediário sólido —
  pandas, EDA, encoding, train_test_split, KNN, comparação de modelos, RMSE/R².
- O **núcleo analítico do FIESC está nesse mesmo nível** (KNN/scaler/split/métricas).
- Engenharia (FastAPI/SQLite/LLM panel) = nível dos apps reais do candidato
  (`Analista_Financeiro`, `Gestor_Financeiro`/PlanejAI). Reusar `ui.py` e padrão `config_ia`.
- Regra: manter tudo **explicável**. Nada que o candidato não consiga defender na entrevista.

---

## 11. RISCOS / PENDÊNCIAS DE AMBIENTE

- Ollama **não instalado** localmente ainda → hoje RAG usa fallback (mostra trecho do manual).
- OpenRouter precisa de `OPENROUTER_API_KEY` no `.env` (perfil cloud).
- Supabase: criar projeto + `DATABASE_URL`.
- Telegram: criar bot + `TELEGRAM_TOKEN`.
- Repo GitHub: será **público** (gh logado como `soutes`); ainda sem remote.
- Background agents do harness morrem em restart → fazer trabalho que persiste em foreground.

---

## 12. PROCESSO COM TIME DE AGENTES (SDLC completo)

A partir daqui o desenvolvimento segue como uma consultoria especialista faria, com
papéis: **Product Owner, Arquiteto, Tech Lead, Backend, Frontend, UI/UX, QA, Reviewer.**

Fases: Discovery/PRD → ADRs → Backlog → Build paralelo → QA → Review → Integração.

Artefatos gerados em `docs/`: `PRD.md`, `user-stories/`, `adr/ADR-NNN-*.md`,
`STATUS.md` (quadro vivo de andamento).

**O playbook completo e os prompts copia-e-cola estão em [`prompt_agents.md`](prompt_agents.md).**
Comece pela **Fase 0 (Product Owner → PRD + User Stories)**.
