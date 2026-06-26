# Plano de Execução — tmux Multi-Painel

> Use este documento ao abrir o tmux para a Etapa 2 (execução).
> Cada pane = um agente especialista com papel único.
> Coordenação via `docs/STATUS.md`.

---

## Layout tmux (4 panes)

```
┌─────────────────────────┬─────────────────────────┐
│  Pane 0: Backend        │  Pane 1: Frontend/UI/UX │
│  (B1 → B2)              │  (U1 → F1)              │
├─────────────────────────┼─────────────────────────┤
│  Pane 2: QA/Reviewer    │  Pane 3: Tech Lead      │
│  (Q1, Q2, R1)           │  (integração, deploy)   │
└─────────────────────────┴─────────────────────────┘
```

### Comandos para abrir

```bash
tmux new-session -d -s fiesc
tmux split-window -h
tmux split-window -v
tmux select-pane -t 0
tmux split-window -v
tmux attach -t fiesc
```

---

## Prompt por Pane

### Pane 0 — Backend

```
Aja como BACKEND ENGINEER do projeto Manutenção Prescritiva (FIESC).
Leia CONTEXTO.md, prompt_agents.md e docs/STATUS.md antes de tudo.
Sua tarefa é a Wave 1 → Wave 2 do backend:

B1 (Wave 1): Crie src/core/backend.py com:
  - responder_evento(evento_json: dict) -> dict
    Chama pipeline.process_event → retorna análise completa formatada
  - responder_duvida(texto: str) -> str
    Chama rag.prescribe com a pergunta → retorna resposta baseada nos manuais
    Consulta db.listar_eventos() e db/listar_pendencias() para contextualizar
  Grave o resultado no banco (db.gravar_consulta).

B2 (Wave 2, após B1 ✅): Atualize src/bot/telegram_bot.py:
  - Se mensagem parece JSON → chama responder_evento → formata e envia
  - Caso contrário → chama responder_duvida → envia resposta
  - Persiste evento e resposta no banco

Regras:
- Não edite arquivos de outro agente (ui.py, streamlit_app.py, analise.ipynb)
- Não quebre contratos (assinaturas de pipeline, similarity, rag, llm, db)
- Atualize docs/STATUS.md (B1→🟦 ao iniciar, ✅ ao concluir)
- Português em código e comentários
- Código defensável: comente o PORQUÊ das escolhas não-óbvias
```

---

### Pane 1 — Frontend / UI/UX

```
Aja como FRONTEND + UI/UX ENGINEER do projeto Manutenção Prescritiva (FIESC).
Leia CONTEXTO.md, prompt_agents.md e docs/STATUS.md antes de tudo.
Sua tarefa é Wave 1 → Wave 2 do frontend:

U1 (Wave 1): Crie src/app/ui.py com design system:
  - Paleta de cores (fundo escuro industrial, destaque laranja/azul)
  - Funções: cabecalho(), card_metrica(label, valor, delta), badge_defeito(nome),
    alerta_sem_doc(defeito), tabela_eventos(df), tabela_pendencias(df)
  - Baseie no padrão do PlanejAI (mencionado em CONTEXTO.md §10) — limpo e profissional

F1 (Wave 2, após U1 ✅ e B1 ✅): Atualize src/app/streamlit_app.py:
  - Importe ui.py e aplique design system
  - Página "Histórico": tabela de eventos + 3 KPIs (total, defeito mais freq, sem doc)
  - Página "Pendências": tabela ordenada por ocorrências + alerta visual
  - Simulador de evento (formulário JSON) que chama a API e exibe resultado
  - Modo demo: se API não disponível, usa dados mock para não quebrar

Regras:
- Não edite arquivos de outro agente (backend.py, telegram_bot.py, analise.ipynb)
- Atualize docs/STATUS.md (U1, F1)
- Design limpo, sem poluição visual — avaliador vai abrir no navegador
```

---

### Pane 2 — QA / Reviewer

```
Aja como QA ENGINEER + REVIEWER do projeto Manutenção Prescritiva (FIESC).
Leia CONTEXTO.md, prompt_agents.md e docs/STATUS.md antes de tudo.
Suas tarefas:

Q1 (Wave 1 — paralelo): Crie notebooks/analise.ipynb:
  - Seção 1: Carrega data/banner_clean.parquet, mostra shape e sample
  - Seção 2: Distribuição dos 17 defeitos canônicos (gráfico de barras)
  - Seção 3: Distribuição temporal dos eventos
  - Seção 4: Curva k vs accuracy do KNN (k=1..15), destaca k=1 (0.74)
  - Seção 5: Matriz de confusão dos 6 defeitos com manual
  - Seção 6: Sobreposição eccentric_rotor ↔ desbalanceado (scatter 2D PCA)
  - Seção 7: Cobertura documental (COM vs SEM manual — gráfico)
  - Seção 8: Tabela resumo de métricas + 3 insights analíticos comentados

Q2 (Wave 3 — após B2 ✅ e F1 ✅): Crie tests/test_e2e.py:
  - Teste 1: POST /api/evento com JSON válido → prescrição retornada
  - Teste 2: POST /api/evento com defeito sem manual → mensagem de gating
  - Teste 3: POST /api/duvida com pergunta → resposta baseada em contexto
  - Confirma gravação no banco (SELECT após cada POST)

R1 (Wave 3 — após Q2 ✅): Review LGPD e contratos:
  - Verifica: LLM_PROVIDER é lido de config, não hardcoded
  - Verifica: nenhum dado vaza para log em modo ollama
  - Verifica: gating não é bypassável
  - Verifica: assinaturas de contrato respeitadas
  - Reporta findings em docs/REVIEW.md (formato: path:linha: severidade: problema. fix.)

Regras:
- Q1 usa apenas notebooks/analise.ipynb (não toca src/)
- Q2 usa apenas tests/ (não toca src/)
- R1 é leitura apenas — não edita código
- Atualize docs/STATUS.md (Q1, Q2, R1)
```

---

### Pane 3 — Tech Lead (integração + deploy)

```
Aja como TECH LEAD do projeto Manutenção Prescritiva (FIESC).
Leia CONTEXTO.md, prompt_agents.md e docs/STATUS.md antes de tudo.

Sua função é COORDENAÇÃO e INTEGRAÇÃO — não implementa features.
Monitora docs/STATUS.md. Quando Wave 1 completa → libera Wave 2.
Quando Wave 3 completa → executa L1:

L1 (após R1 ✅):
  - docker compose build && docker compose up -d
  - Smoke test: curl localhost:8000/docs (FastAPI up?)
  - Smoke test: curl localhost:8501 (Streamlit up?)
  - Se tudo OK: git add -A && git commit -m "feat: sistema completo wave 1-3"
  - git tag v1.0

D1 (after L1 ✅ — se sobrar tempo):
  - Configure .env com OPENROUTER_API_KEY e DATABASE_URL Supabase
  - Teste perfil cloud end-to-end

D2 (after D1 ✅ — se sobrar tempo):
  - HF Spaces: push do código, configure Secrets (OPENROUTER_API_KEY, DATABASE_URL)
  - Adicione link no README.md

D3 (any time):
  - Adicione diagrama mermaid de arquitetura ao README.md

Atualize docs/STATUS.md ao longo do processo.
```

---

## Ordem de Execução

```
t=0    Wave 1 INICIA: Pane0(B1) ∥ Pane1(U1) ∥ Pane2(Q1)
       Pane3 monitora STATUS.md

t=B1✅+U1✅  Wave 2 INICIA: Pane0(B2) ∥ Pane1(F1)
       Pane2 finaliza Q1 se não concluiu

t=B2✅+F1✅  Wave 3 INICIA: Pane2(Q2 → R1)
       Pane3 aguarda R1✅

t=R1✅  Lead executa L1 (integração + tag v1.0)
       Se sobrar tempo: D1 → D2 → D3
```

---

## Critério Final de "Done para Entrega"

- [ ] `docker compose up` sobe sem erro
- [ ] FastAPI /docs responde
- [ ] Streamlit abre histórico + pendências com design
- [ ] Telegram recebe JSON e responde prescrição (ou gating)
- [ ] Notebook EDA executa sem erro com métricas visíveis
- [ ] `git tag v1.0` criado
- [ ] README descreve como rodar (2 comandos: `cp .env.example .env` + `docker compose up`)
