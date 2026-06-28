# Manutenção Prescritiva — Case SENAI/FIESC

Sistema de **manutenção prescritiva** para máquinas rotativas com sensores de vibração.
Dado um novo evento de sensor (JSON com 23 features), o sistema:

1. Encontra os **50 casos históricos mais similares** via KNN ponderado por distância (166k eventos)
2. Identifica o defeito por **maioria ponderada** dos vizinhos (classificação por similaridade)
3. **RandomForest confirma** a classificação (análise de dados, acc=87.9%)
4. Recupera o procedimento de correção nos manuais técnicos via **RAG** (TF-IDF + LLM)
5. Classifica a criticidade com **semáforo** 🔴 Crítico / 🟡 Atenção / 🟢 Normal
6. Se não há manual para o defeito: **registra pendência, nunca inventa** (anti-alucinação)
7. Persiste tudo no banco com auditoria de status editável pelo engenheiro

**Interfaces:** Telegram (operador no campo) · Dashboard Streamlit (estação) · API REST (integração)

**LGPD:** interruptor `LLM_PROVIDER=ollama` → LLM 100% local, nenhum dado sai da empresa.

---

## 📦 Entrega para Avaliação

Este projeto é composto por:

| Entrega | Formato | Descrição |
|---------|---------|-----------|
| **Código-fonte** | GitHub (repo) | Código completo com histórico de commits |
| **Apresentação** | PDF (Canva) | 17 slides com arquitetura, decisões e resultados |
| **EDA** | Jupyter Notebook | Análise exploratória + comparação de modelos |
| **Vídeo demo** | MP4 | Execução do app em tempo real (para quem não quiser rodar Docker) |

> **Não quer rodar Docker?** Assista ao vídeo demo para ver o sistema em ação.
> O download do Ollama (~2GB) é necessário apenas para rodar localmente via `docker compose up`.

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    SENSOR JSON (23 features)                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  KNN (50)   │ ← busca por similaridade
                    │  ponderado  │   50 vizinhos mais próximos
                    └──────┬──────┘
                           │
              ┌────────────▼────────────┐
              │  Votação ponderada      │
              │  (1/distância)          │
              │  43/50 = desbalanceado  │
              │  confiança: 86%         │
              └────────────┬────────────┘
                           │
                    ┌──────▼──────┐
                    │ RF (200)    │ ← confirmação
                    │ acc=87.9%   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Semáforo   │
                    │  🔴🟡🟢     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  RAG        │ ← prescrição
                    │  TF-IDF     │
                    │  6 PDFs     │
                    │  61 chunks  │
                    └──────┬──────┘
                           │
              ┌────────────▼────────────┐
              │  Resultado ao operador  │
              │  Defeito + Prescrição   │
              │  + Frequência + Fontes  │
              └─────────────────────────┘
```

---

## 🧠 Pipeline de Classificação

O fluxo combina **3 técnicas** do enunciado:

| Técnica | Componente | O que faz |
|---------|-----------|-----------|
| **Busca por similaridade** | KNN NearestNeighbors | Encontra 50 eventos mais parecidos no histórico |
| **Análise de dados** | RandomForest 200 árvores | Confirma a classificação (acc=87.9%) |
| **Recuperação de conhecimento** | RAG TF-IDF + LLM | Prescreve correção via manuais técnicos |

### Por que KNN como fluxo principal (não RF puro)?

- **Explicável:** "O defeito foi identificado porque 43 dos 50 eventos mais similares são desbalanceado"
- **Funciona para defeitos novos:** KNN não depende de classes pré-definidas
- **Alinha com o enunciado:** "não depende necessariamente da classificação prévia"

### Votação ponderada por distância

Vizinhos **mais próximos** pesam **mais** na decisão:

```
Vizinho 1 (dist=0.000) → acelerando → peso = 1/0.000 = ∞
Vizinho 2 (dist=0.934) → acelerando → peso = 1.071
Vizinho 3 (dist=0.942) → acelerando → peso = 1.062
...
Vizinho 44 (dist=2.500) → desalinhado → peso = 0.400
```

Isso resolve o problema de **classes com poucos registros** (ex: `acelerando` com apenas 7 registros) — se os 5 vizinhos mais próximos são `acelerando`, ele vence mesmo que classes dominantes tenham mais vizinhos distantes.

---

## 🚦 Semáforo de Criticidade

| Cor | Critério | Ação |
|-----|----------|------|
| 🔴 **Crítico** | Sem manual OU freq > 5/sem OU RPM fora de [400, 3800] | Atenção imediata |
| 🟡 **Atenção** | Com manual + baixa freq + RPM normal | Monitoramento |
| 🟢 **Normal** | Estado operacional (não-defeito) | Nenhuma ação |

---

## 📊 Cobertura RAG (Anti-Alucinação)

| Defeito | Documento | Status |
|---------|-----------|--------|
| rolamento (inner/outer/ball/combination) | Doc1.pdf | ✅ Documentado |
| desalinhado | Doc2.pdf | ✅ Documentado |
| desbalanceado | Doc3.pdf | ✅ Documentado |
| correia | Doc4.pdf | ✅ Documentado |
| polia | Doc5.pdf | ✅ Documentado |
| cocked_rotor | Doc6.pdf | ✅ Documentado |
| eccentric_rotor, ventoinha, falta_fase | — | ⚠️ Sem manual → registra pendência |

**RAG auto-atualizável:** adicione um PDF em `docs/` → o índice rebuilda automaticamente na próxima prescrição.

### Avaliador de Retrieval (antes do LLM)

| Nota | Score | Significado |
|------|-------|-------------|
| A | ≥ 0.30 | Contexto altamente relevante |
| B | ≥ 0.15 | Contexto relevante recuperado |
| C | ≥ 0.05 | Contexto parcialmente relacionado |
| **F** | < 0.05 | **LLM bloqueado** — sem contexto útil |

---

## 🚀 Setup Rápido

### Opção 1: Docker (recomendado)

```bash
git clone https://github.com/soutes/manutencao_sensores_com_ia
cd manutencao_sensores_com_ia
cp .env.example .env
docker compose up
```

Acesse: http://localhost:8501

> O Docker baixa o Ollama (~2GB) automaticamente na primeira execução.

### Opção 2: Desenvolvimento local

```bash
poetry install
poetry run streamlit run src/app/streamlit_app.py
```

### Opção 3: Só ver o resultado (sem Docker)

Assista ao vídeo demo incluído na entrega.

---

## 🧪 Testando

### Via Dashboard

1. Acesse http://localhost:8501
2. Vá na aba "Nova Análise"
3. Faça upload de qualquer JSON da pasta `json_ok/`
4. Veja o resultado: defeito + prescrição + semáforo

### JSONs de teste (17 reais extraídos do dataset)

```
json_ok/
├── 01_acelerando.json          # estado operacional (7 registros no dataset)
├── 02_baseline.json            # baseline de referência
├── 03_cocked_rotor.json        # rotor inclinado
├── 04_correia.json             # desgaste de correia
├── 05_desalinhado.json         # desalinhamento
├── 06_desbalanceado.json       # desbalanceamento
├── 07_eccentric_rotor.json     # rotor excêntrico (sem manual → 🔴)
├── 08_falta_fase.json          # falta de fase elétrica (sem manual → 🔴)
├── 09_motor_desligado.json     # motor desligado (RPM=0)
├── 10_normal.json              # estado normal
├── 11_polia.json               # desgaste de polia
├── 12_rolamento_ball.json      # rolamento esfera
├── 13_rolamento_combination.json  # rolamento combinado
├── 14_rolamento_inner.json     # rolamento pista interna
├── 15_rolamento_outer.json     # rolamento pista externa
├── 16_teste.json               # estado de teste
├── 17_ventoinha.json           # ventoinha (sem manual → 🔴)
├── 18_acelerando_v1.json       # acelerando variação 1
├── 19_acelerando_v2.json       # acelerando variação 2
└── 20_acelerando_v3.json       # acelerando variação 3
```

> Todos os JSONs são **dados reais** extraídos do `banner_clean.parquet` (166k registros).
> Não contêm campo `"fault"` — o sistema classifica automaticamente.

---

## 📁 Estrutura do Projeto

```
src/
  core/
    config.py           # variáveis de ambiente + load_dotenv
    faults.py           # normalização 151→17 canônicos + labels PT-BR
    similarity.py       # KNN ponderado + RF confirmação
    rag.py              # TF-IDF index + auto-rebuild + prescribe()
    llm.py              # gateway ollama ↔ openrouter (LGPD)
    backend.py          # responder_evento() + responder_duvida()
    db.py               # SQLAlchemy: Evento, Consulta, StatusHistorico
    pipeline.py         # process_event() end-to-end
    doc_extract.py      # pdfplumber (texto) + OCR (PyMuPDF + RapidOCR-onnxruntime)
  app/
    streamlit_app.py    # 8 abas: Overview|Nova Análise|Pendências|Resolvidos|Análise|Chat|Relatório IA|Configuração IA
    ui.py               # design system dark (#10F5A3 accent)
  bot/
    telegram_bot.py     # multi-persona: JSON→semáforo, texto→Q&A
  api/
    main.py             # FastAPI /health /event /chat
artifacts/
  rag.joblib            # índice TF-IDF serializado (auto-rebuild)
  similarity.joblib     # KNN + RF serializados
data/
  banner_clean.parquet  # 166k eventos processados
  fiesc.db              # SQLite (gerado automaticamente)
docs/
  Doc1-6.pdf            # manuais técnicos (base do RAG)
  Descritivo Prova Prática.pdf  # enunciado do case
json_ok/                # 20 JSONs de teste reais
notebooks/
  EDA_FIESC.ipynb       # análise exploratória + comparação de modelos
```

---

## 📊 Resultados do EDA

| Modelo | Acurácia | Treino | Observação |
|--------|----------|--------|------------|
| KNN k=5 | 54.7% | instantâneo | Baseline — limitado por features redundantes |
| KNN GridSearch (k=15, manhattan) | 60.6% | ~3min | Teto do KNN puro |
| XGBoost 300 trees | 84.0% | 23s | Bom, mas mais lento |
| **RF 200 trees (default)** | **87.9%** | **7.7s** | **Vencedor** — melhor custo-benefício |
| RF 500 trees (tuned) | 87.9% | 34.8s | Retorno decrescente — não compensa |

**Decisão:** RF 200 trees default como confirmação + KNN ponderado como fluxo principal.

---

## 📄 Dados

- `data/banner_clean.parquet` — 166.796 eventos, 23 features numéricas
- `fault` original → 151+ rótulos brutos normalizados para **17 canônicos**
- Período: Abril–Junho 2026

---

## 🛡️ Segurança e LGPD

| Aspecto | Implementação |
|---------|--------------|
| LLM local | Ollama on-prem, nenhum dado sai da empresa |
| Dados ao LLM | Apenas nome canônico do defeito (não JSON bruto) |
| Anti-alucinação | 3 portões: documento existe? → retrieval relevante? → resposta ancorada? |
| Auditoria | status_historico registra quem, quando, de→para |
| Bot Telegram | Controle de acesso via ALLOWED_USER_IDS |

---

## 📚 Stack

| Camada | Tecnologia | Motivo |
|--------|-----------|--------|
| Classificação | KNN ponderado + RF 200 árvores | Similaridade + confirmação (166k×18 features) |
| RAG | TF-IDF + cosine similarity | Sem torch; corpus pequeno (61 chunks, 6 PDFs) |
| OCR | pymupdf + rapidocr-onnxruntime | Python 3.14 compatível |
| LLM | Ollama (local) ↔ OpenRouter (demo) | Interruptor LGPD |
| Banco | SQLAlchemy (SQLite ↔ Postgres) | Trocável via DATABASE_URL |
| API | FastAPI (porta 8000) | Swagger em /docs |
| Dashboard | Streamlit (porta 8501) | 8 abas, dark theme |
| Bot | python-telegram-bot | Multi-persona com guardrails |
| Deploy | Docker Compose | `docker compose up` sobe tudo |
| Deps | Poetry 2.2.1 | Lockfile determinístico |

---

## 🗺️ Melhorias Futuras

| Área | Melhoria | Requisito |
|------|----------|-----------|
| LLM | qwen2.5:14b (mais preciso) | 8-16 GB VRAM |
| RAG | Embeddings densos (multilingual-e5) | GPU ou ONNX |
| ML | XGBoost ou rede neural 1D | GPU para séries temporais |
| Infra | MQTT/OPC-UA real (Ignition, Kepware) | Middleware industrial |
| Escala | Multi-planta com Postgres + row-level security | Supabase |
