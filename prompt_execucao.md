# 🛠️ Etapa 2 — EXECUÇÃO em tmux (paralelo, multi-painel)

Só comece **depois** do planejamento pronto (PRD, ADRs, `docs/STATUS.md`, plano).
Aqui cada **painel do tmux é um `claude` independente** (processo próprio, contexto
próprio). Não há delegação em-processo: a coordenação é **por arquivo** (`docs/STATUS.md`)
e a integração é feita pelo **pane LEAD**.

---

## 1. Pré-requisitos

- `docs/STATUS.md` preenchido (tarefas, donos, dependências, arquivos disjuntos).
- tmux disponível. No Windows: rode via **WSL** ou **Git Bash** (o candidato já usa tmux).
- Ollama rodando (perfil local) e/ou `OPENROUTER_API_KEY` no `.env` (perfil cloud).

## 2. Subir a sessão

Na raiz do projeto:
```bash
bash scripts/tmux_team.sh
tmux attach -t fiesc
```
Cria 6 panes, um por papel (na ordem):

| Pane | Papel | Edita só |
|---|---|---|
| 0 | 🧭 **LEAD** | `docs/STATUS.md`, integração, git (ÚNICO que commita) |
| 1 | ⚙️ **BACKEND** | `src/core/backend.py`, `src/api/main.py`, `src/bot/telegram_bot.py` |
| 2 | ✨ **UI/UX** | `src/app/ui.py` |
| 3 | 🎨 **FRONTEND** | `src/app/streamlit_app.py` |
| 4 | 🧪 **QA** | `notebooks/`, `tests/`, `scripts/_smoke_*.py` |
| 5 | 🔍 **REVIEWER** | nada (só lê e comenta) |

Em cada pane: rode `claude` e cole o prompt do papel (seção 5).
Navegação tmux: `Ctrl-b` + seta (mudar pane), `Ctrl-b z` (zoom), `Ctrl-b d` (desconectar).

---

## 3. Protocolo de coordenação (CRÍTICO — processos separados)

1. **Matriz de arquivos é lei.** Cada papel edita só os arquivos da tabela acima. Zero
   sobreposição → zero conflito de merge.
2. **Claim pelo STATUS.md.** Antes de editar, o agente muda sua linha em `docs/STATUS.md`
   para `🟦 doing`. Ao terminar (com smoke test ok), para `✅`. Edita **só a própria linha**.
3. **Dependências (waves).** Se a coluna `Depende` não está `✅`, o agente fica
   `🟥 bloqueado` e aguarda — relê o board periodicamente.
4. **Só o LEAD commita.** Workers NÃO rodam `git add/commit` (evita lock concorrente do
   index). O LEAD observa o board, roda os testes e commita por wave.
5. **Sincronizar antes de pegar tarefa nova:** reler `docs/STATUS.md` e o `git log`.

### Waves (ordem de execução)
```
Wave 1 (paralelo):  BACKEND B1 ∥ UI/UX U1 ∥ QA Q1
Wave 2 (paralelo):  BACKEND B2 ∥ FRONTEND F1 (só após U1=✅ e B1=✅)
Wave 3:             QA testa tudo → REVIEWER revisa → LEAD integra+commita
```

---

## 4. Definition of Done — ver `prompt_agents.md` §4.

---

## 5. Prompts dos panes (copia-e-cola — um por painel)

Todos começam lendo o contexto. São **autossuficientes** (processos separados).

### 🧭 PANE 0 — LEAD
```
Você é o TECH LEAD (pane 0) numa execução em tmux com 5 outros agentes em panes vizinhos.
Leia CONTEXTO.md, prompt_agents.md, prompt_execucao.md e docs/STATUS.md.

Seu papel: NÃO implementar features. Você (a) mantém docs/STATUS.md coerente, (b) observa
os estados, (c) quando uma tarefa vira ✅, roda o smoke test correspondente e o pipeline
end-to-end, (d) você é o ÚNICO que roda git add/commit — commite por wave com mensagem
clara em português, (e) destrava bloqueios. A cada rodada, imprima o board atual.
Comece validando o ambiente (parquet, artifacts, Ollama em localhost:11434) e o board.
```

### ⚙️ PANE 1 — BACKEND
```
Você é o BACKEND (pane 1). Leia CONTEXTO.md, prompt_agents.md, prompt_execucao.md, docs/STATUS.md.
Edite SOMENTE: src/core/backend.py, src/core/db.py, src/api/main.py, src/bot/telegram_bot.py.
NÃO commite (o LEAD commita).

Tarefa B1: crie src/core/backend.py com:
  - responder_evento(event: dict, origem='api') -> dict:
      chama core.pipeline.process_event, classifica semáforo (🔴/🟡/🟢) via _classificar_semaforo(),
      grava com core.db.salvar_evento (inclui status_manutencao), retorna o report + id salvo.
      Regras semáforo: 🔴 = sem manual OU alta freq (>5 ocorrências/7 dias) OU rpm anormal;
      🟡 = defeito com manual, primeira ocorrência ou baixa freq; 🟢 = estado normal/baseline.
  - responder_duvida(texto: str, origem='api') -> dict:
      Detecta intenção da pergunta e combina banco + RAG:
      "status parque / pontos críticos / manutenções abertas" → core.db.resumo_semaforo() + lista 🔴🟡;
      "pendência/pendências" → core.db.listar_pendencias();
      "histórico" → core.db.historico_defeito(defeito);
      pergunta técnica sobre defeito → core.rag.prescribe();
      grava com core.db.salvar_consulta; retorna {resposta, contexto, fonte}.
  - Expanda core/db.py com: resumo_semaforo(), serie_temporal_resolvidos(dias=30),
    atualizar_status(evento_id, status, comentario, responsavel),
    e tabela status_historico (evento_id, status_anterior, status_novo, responsavel, data, comentario).

Tarefa B2 (após B1=✅): ligue src/bot/telegram_bot.py:
  JSON válido → responder_evento, origem='telegram';
  texto → responder_duvida, origem='telegram';
  formata resposta p/ Telegram incluindo emoji do semáforo.

Antes de cada tarefa marque 🟦 doing; ao fim, smoke test em scripts/_smoke_backend.py e marque ✅.
Respeite contratos (pipeline, similarity, rag, llm) e interruptor LGPD.
```

### ✨ PANE 2 — UI/UX
```
Você é o UI/UX (pane 2). Leia CONTEXTO.md, prompt_agents.md, prompt_execucao.md, docs/STATUS.md.
Edite SOMENTE: src/app/ui.py. NÃO commite.

Tarefa U1: crie src/app/ui.py portando o DESIGN SYSTEM do GESTOR_FINANCEIRO do candidato
(fonte de verdade — NÃO usar o Analista_Financeiro):
  - C:/Users/luiz_/_DS/Gestor_Financeiro/src/ui.py  (paleta, CSS, componentes, fonte Inter)
  - C:/Users/luiz_/_DS/Gestor_Financeiro/design-brief.md  (princípios visuais)
  - C:/Users/luiz_/_DS/Gestor_Financeiro/assets/design-system/  (referências)
Porte: inject_css() com a mesma paleta (accent #10F5A3, tema escuro, Inter), glow_kpi_box,
barras de progresso, alert_line, ícones SVG — ADAPTADO ao domínio (defeito, ocorrências,
frequência, pendência, "sem documento"). Mantenha a IDENTIDADE VISUAL do Gestor (o
candidato quer consistência com o app dele). Funções puras de componente (recebem dados,
renderizam via st.markdown). Marque 🟦/✅ na sua linha do STATUS.
```

### 🎨 PANE 3 — FRONTEND
```
Você é o FRONTEND (pane 3). Leia CONTEXTO.md, prompt_agents.md, prompt_execucao.md, docs/STATUS.md.
Edite SOMENTE: src/app/streamlit_app.py. NÃO commite.
NÃO comece enquanto U1 (ui.py) e B1 (backend) não estiverem ✅ no STATUS — fique 🟥 bloqueado.

Tarefa F1: reescreva src/app/streamlit_app.py usando src/app/ui.py e core.backend.
O dashboard atende múltiplos stakeholders (operador, engenheiro, gerente, diretor).

Estrutura em abas/páginas:

Aba 1 — "Painel": KPIs no topo em glow_kpi_box:
  🔴 Críticos (n) | 🟡 Atenção (n) | 🟢 Resolvidos hoje | ⚠️ Sem manual | Defeito mais freq.
  Gráfico Plotly: série temporal de eventos resolvidos (🟢) por dia (core.db.serie_temporal_resolvidos).
  Segunda linha do gráfico: eventos abertos (🔴+🟡) no mesmo período.

Aba 2 — "Eventos": tabela core.db.listar_eventos(), ordenada 🔴→🟡→🟢.
  Filtros: semáforo, tipo de defeito, período.
  Para cada linha: botão "Editar" abre formulário (st.form) lateral ou inline:
    select status (🔴/🟡/🟢), textarea comentário (obrigatório p/ 🟢), text responsável.
    Salvar → core.db.atualizar_status() → recarrega tabela e KPIs.

Aba 3 — "Pendências": tabela core.db.listar_pendencias(), badge 🔴 implícito, por freq desc.
  Alerta visual para >5 ocorrências.

Aba 4 — "Análise": distribuição de defeitos (barras Plotly, coloridas por semáforo predominante),
  pizza 🔴🟡🟢 do período, tabela de cobertura COM/SEM manual.

Aba 5 — "Chat": core.backend.responder_duvida(texto) — responde status parque, pontos críticos,
  histórico e Q&A técnico. Exibe fonte (banco / RAG / banco+RAG).

Mantenha MODO DEMO (try/except se índices/LLM ausentes, dados mock). Marque 🟦/✅ no STATUS.
```

### 🧪 PANE 4 — QA
```
Você é o QA (pane 4). Leia CONTEXTO.md, prompt_agents.md, prompt_execucao.md, docs/STATUS.md.
Edite SOMENTE: notebooks/, tests/, scripts/_smoke_*.py. NÃO commite.

Tarefa Q1 (notebook): crie notebooks/analise.ipynb no estilo EDA do candidato (notebook
BlackFriday): carregar data/banner_clean.parquet, distribuição de falhas, holdout KNN
(k=1,5,15) com acurácia/f1, matriz de confusão, evidência da confusão
eccentric_rotor↔desbalanceado, e INSIGHTS escritos em markdown.

Tarefa Q2 (TESTES — obrigatório, use pytest + FastAPI TestClient):
  - tests/test_api.py: TestClient sobre src/api/main.py — GET /health (200),
    POST /event com tests/sample_events.json (valida defeito_canonico, is_problem,
    documented, n_similar), POST /chat (resposta não vazia).
  - tests/test_backend.py: core.backend.responder_evento (grava no banco e retorna report),
    responder_duvida para pergunta de pendência, histórico e correção de defeito.
  - tests/test_pipeline.py: process_event end-to-end nos 3 casos (com-doc cocked_rotor,
    sem-doc eccentric_rotor → documented=False, estado normal → is_problem=False).
  - tests/test_db.py: salvar_evento/listar_pendencias/resumo_semaforo/serie_temporal_resolvidos
    em SQLite temporário; atualizar_status grava status_historico com auditoria correta.
  - tests/test_faults.py: normalize_fault cobre typos e estados (0 desconhecidos).
  - tests/test_telegram.py: format_report do bot p/ caso com-doc (🟡) e sem-doc (🔴),
    e p/ consulta de status parque (sem enviar rede).
  - tests/test_semaforo.py: _classificar_semaforo retorna 🔴 p/ sem-doc, 🔴 p/ alta freq,
    🟡 p/ defeito com doc primeira ocorrência, 🟢 p/ estado normal.
Rode `pytest -q` e gere tests/relatorio_qa.md: caso → esperado → obtido → passou?.
Reporte bugs com a saída real, SEM corrigir. Marque 🟦/✅ no STATUS.
```

### 🔍 PANE 5 — REVIEWER
```
Você é o REVIEWER (pane 5). Leia CONTEXTO.md, prompt_agents.md, prompt_execucao.md, docs/STATUS.md.
NÃO edite código. Aguarde tarefas chegarem a 🟨/✅ e revise o diff (git diff).
Uma linha por achado:  arquivo:linha: <ALTA|MÉDIA|BAIXA> problema. correção sugerida.
Priorize: contrato quebrado, VAZAMENTO LGPD (manual indo p/ cloud no perfil errado),
robustez, e simplicidade (algo difícil de o candidato defender na entrevista). Sem elogios,
sem scope creep. Escreva o resumo em docs/review_notes.md.
```

---

## 6. Encerramento (LEAD)
Quando todas as tarefas da wave estão ✅ e o Reviewer sem severidade ALTA aberta:
```
LEAD: rode pipeline end-to-end + smoke tests, atualize docs/STATUS.md, e commite a wave:
git add -A && git commit -m "feat(wave-N): <resumo> [backend/front/uiux/qa]"
```

## 7. Troubleshooting
- **Conflito de arquivo:** alguém saiu da matriz. Pare, volte ao dono correto.
- **STATUS.md com edição perdida:** dois panes editaram a mesma linha — reabra e reescreva.
- **Frontend quebrando:** confirme U1 e B1 ✅ antes (dependência de wave).
- **git index.lock:** só o LEAD commita. Se travar, `rm -f .git/index.lock` e recommite.
- **Persistência:** se um pane fecha, o trabalho em disco permanece; reabra `claude` e
  releia o STATUS para retomar.
