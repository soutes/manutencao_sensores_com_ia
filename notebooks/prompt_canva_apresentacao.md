# Prompt para Canva — Apresentação: Manutenção Prescritiva SENAI/FIESC

Cole o bloco abaixo no Canva (Magic Design / AI Presentation ou Design → Create new design → Presentation 16:9).

---

## TEMA VISUAL

Dark industrial dashboard theme. Background #0B0E13 (near-black), accent #10F5A3 (neon green), secondary accent #4FC3F7 (blue), warning #F5C518 (amber), danger #FF6B7A (red). Typography: Inter or similar sans-serif. Style: technical/SCADA dashboard aesthetic — clean, data-heavy, minimal decorative elements. Use subtle grid patterns or sensor waveform backgrounds where appropriate. Icons should be minimal/geometric (gears, sensors, charts).

---

## CONTEÚDO — 17 SLIDES

### Slide 1 — CAPA
**Title:** Manutenção Prescritiva para Motores Industriais
**Subtitle:** Case Técnico — SENAI/FIESC
**Visual:** Dark background with subtle waveform/vibration pattern. Accent line in neon green at top.
**Bottom text:** Luiz Augusto Soutes | 2026

---

### Slide 2 — O PROBLEMA (Storytelling opener)
**Title:** O Problema
**Content (bullet points):**
- Motores industriais falham sem aviso → parada não planejada custa R$5k–50k/hora
- Manutenção corretiva é reativa; preditiva ainda exige interpretação humana
- **Gap:** Nenhum sistema conecta diagnóstico automático → prescrição de correção → acompanhamento do reparo em tempo real

**Visual suggestion:** Icon of broken motor or factory floor. Red accent for urgency.

---

### Slide 3 — O OBJETIVO
**Title:** O que o sistema faz
**Content:**
Sensor de vibração → **Classificação do defeito** → **Semáforo de criticidade** → **Prescrição de correção** (via manuais técnicos) → **Acompanhamento do reparo**

**Below, 3 key outcomes:**
1. Diagnóstico automático em <2 segundos
2. Prescição rastreável a manuais técnicos (sem alucinação)
3. Dashboard + Bot Telegram + API — 3 canais, 1 backend

**Visual suggestion:** Horizontal pipeline flow diagram with icons at each step.

---

### Slide 4 — VISÃO GERAL DO SISTEMA (Architecture)
**Title:** Arquitetura do Sistema
**Visual:** Architecture diagram showing:

```
[Sensores JSON] → [API FastAPI :8000]
                        ↓
              [Pipeline process_event()]
              ↓              ↓         ↓
    [RF Classifier]   [KNN Stats]  [RAG/LLM]
         ↓                ↓            ↓
    [Fault Label]   [Frequency]  [Prescription]
         ↓                ↓            ↓
              [Semáforo 🔴🟡🟢]
                        ↓
              [SQLAlchemy DB]
                        ↓
         ┌──────────┼──────────┐
    [Dashboard]   [API]    [Bot TG]
   Streamlit :8501  REST   Telegram
```

**Bottom note:** 1 backend (2 funções: responder_evento + responder_duvida) → 3 interfaces

---

### Slide 5 — DADOS: O QUE TEMOS
**Title:** Dataset — 166.796 Eventos de Sensores
**Left side — Stats table:**

| Métrica | Valor |
|---------|-------|
| Registros | 166.796 |
| Features numéricas | 23 (vibração, temperatura, RPM) |
| Classes de defeito | 17 (13 defeitos + 4 estados) |
| Labels brutos normalizados | 151 → 17 |
| Período | Abr–Jun 2026 |
| Manuais técnicos (PDFs) | 6 → 61 chunks |

**Right side:** Small bar chart showing defect distribution (rolamento_inner 10.6%, eccentric_rotor 9.9%, normal 9.0%, etc.)

---

### Slide 6 — JORNADA ML: KNN → RF (Storytelling)
**Title:** A Jornada do Modelo — Do KNN ao Random Forest
**Visual:** Accuracy progression chart (horizontal bar chart):

```
KNN k=5 (baseline)        0.547  ████░░░░░░░░░░░
KNN k=8 (elbow)           0.554  ████░░░░░░░░░░░
KNN GridSearch (k=15)     0.606  █████░░░░░░░░░░
XGBoost 300 trees         0.840  █████████░░░░░░
RF 200 (default) ★        0.879  ██████████░░░░░
```

**Narrative text:** "KNN foi o ponto de partida — intuitivo, mas limitado por features redundantes (correlação 1.0) e alta dimensionalidade. Após elbow, GridSearch e comparação com XGBoost, o Random Forest 200 árvores se mostrou superior: 0.879 de acurácia em 7.7s de treino. Tuning tentou espremer mais — mas balanced piorou (-0.42pp) e 500 árvores ganhou apenas +0.01pp. RF default venceu."

---

### Slide 7 — EDA: INSIGHTS-CHAVE
**Title:** Análise Exploratória — O que os dados revelam
**Content (3 cards):**

**Card 1 — Features:**
- Distribuições enviesadas à direita (típico de vibração)
- Curtose alta → transientes/impactos nos sinais
- 5 pares de features com correlação 1.0 (unidades diferentes)

**Card 2 — RPM:**
- RPM varia significativamente entre defeitos
- Motor desligado ≈ 0 RPM, defeitos entre 400–3800 RPM
- Feature discriminativa relevante

**Card 3 — Balanceamento:**
- Leve desbalanceamento: rolamento_inner (10.6%) vs acelerando (0.004%)
- Dataset é predominantemente defeitos reais (não ruído)

---

### Slide 8 — CLASSIFICAÇÃO: COMO FUNCIONA
**Title:** Motor de Classificação — RandomForest
**Content:**

**RF Classifier:**
- 200 árvores, 18 features (5 redundantes removidas)
- Acc: 87.9% | Treino: 7.7s
- Prediz o defeito canônico (1 de 17 classes)
- Top features: aceleração pico, curtose, RPM

**Semáforo de criticidade:**
- Frequência semanal, distribuição temporal, última ocorrência
- Alimenta as 4 métricas do sistema

---

### Slide 9 — AS 4 MÉTRICAS DO SISTEMA
**Title:** 4 Métricas que o Sistema Calcula para Cada Evento
**Visual:** 2x2 grid with icons:

**① Eventos Similares** — Quantos registros históricos com o mesmo defeito existem? (bar chart icon)

**② Distribuição Temporal** — Como esse defeito evoluiu ao longo dos meses? (line chart icon)

**③ Frequência Semanal** — Quantas vezes por semana esse defeito aparece? (clock icon, with threshold line at 5/sem → 🔴)

**④ Contexto Operacional** — Qual o RPM médio desse defeito? (gauge icon, range 400–3800)

---

### Slide 10 — SEMÁFORO DE CRITICIDADE
**Title:** Semáforo — Classificação de Criticidade
**Visual:** Three large colored cards side by side:

**🔴 CRÍTICO**
- Sem manual técnico documentado
- Frequência > 5 ocorrências/semana
- RPM fora da faixa [400, 3800]

**🟡 ATENÇÃO**
- Com manual + baixa frequência + RPM normal
- Requer monitoramento

**🟢 OPERACIONAL**
- Não é defeito (estado normal, baseline, etc.)
- Sistema operando dentro dos parâmetros

---

### Slide 11 — RAG: ANTI-ALUCINAÇÃO
**Title:** RAG com Anti-Alucinação — 3 Portões de Controle
**Content:**

**Portão 1 — Documento existe?**
→ Defeito sem manual (eccentric_rotor, ventoinha, falta_fase) → 🔴 + pendência automática. LLM NUNCA é chamado.

**Portão 2 — Retrieval relevante?**
→ TF-IDF busca top-4 chunks → "Professor" avalia qualidade (A/B/C/F). Score F bloqueia LLM.

**Portão 3 — Resposta fundamentada?**
→ "Professor" verifica se a resposta do LLM está ancorada no contexto. Score C ou abaixo → descarta.

**Bottom note:** Nenhum dado bruto do sensor vai ao LLM. Apenas o nome canônico do defeito (ex: "rolamento_inner").

---

### Slide 12 — LGPD: COMPLIANCE BY DESIGN
**Title:** Interruptor LGPD — Compliance Arquitetural
**Visual:** Toggle switch illustration:

**ON-PREM (PRODUÇÃO):**
- LLM local via Ollama (qwen2.5:3b)
- Nenhum dado sai da rede da empresa
- Adequado para dados reais de sensores

**CLOUD (DEMO):**
- API externa via OpenRouter (gpt-4o-mini)
- Apenas dados sintéticos
- Para apresentações e testes

**Key point:** A decisão é um .env — `LLM_PROVIDER=ollama|openrouter`. Não é política, é arquitetura.

---

### Slide 13 — INTERFACES: 3 CANAIS, 1 BACKEND
**Title:** Interfaces — Multi-Canal
**Visual:** Three columns with screenshots/icons:

**Dashboard Streamlit (7 abas)**
- Dark theme com acento neon (#10F5A3)
- KPIs, gráficos Plotly, chat com IA, relatório gerado por LLM
- Formulário de análise + edição de status

**Bot Telegram (multi-persona)**
- JSON colado → classificação + prescrição
- Texto livre → Q&A via RAG + LLM
- Controle de acesso (ALLOWED_USER_IDS)
- Guardrails: detecção de prompt injection + verificação de relevância

**API FastAPI**
- POST /event → pipeline completo
- POST /chat → prescrição por defeito
- GET /health → status

---

### Slide 14 — DOCKER: DEPLOYMENT
**Title:** Docker Compose — Deploy com um Comando
**Visual:** Docker Compose architecture diagram:

```
docker compose up
┌──────────┐  ┌──────────┐  ┌──────────┐
│ ollama   │  │   api    │  │   app    │
│ :11434   │  │  :8000   │  │  :8501   │
│ LLM local│  │ FastAPI  │  │Streamlit │
└──────────┘  └──────────┘  └──────────┘
       ↓            ↓            ↓
    [volume]    [SQLite]    [artifacts]
   ollama model  fiesc.db   rag.joblib
                           similarity.joblib

# Opcional: bot Telegram
docker compose --profile bot up
```

**Key points:**
- Python 3.14-slim + tesseract-ocr + poppler
- SQLite (dev) ↔ Postgres/Supabase (cloud) — só trocar DATABASE_URL
- 125 testes (124 passando)

---

### Slide 15 — NÚMEROS-CHAVE (KPI Dashboard style)
**Title:** Resultados em Números
**Visual:** Large KPI cards (dark background, neon green numbers):

**87.9%** — Acurácia do classificador (RF 200 trees)

**166.796** — Eventos de sensores analisados

**151→17** — Normalização de labels brutos para canônicos

**61** — Chunks de manuais técnicos indexados (TF-IDF)

**3** — Portões anti-alucinação (doc → retrieval → resposta)

**125** — Testes automatizados (99.2% passando)

**<2s** — Latência de classificação + prescrição

---

### Slide 16 — DECISÕES TÉCNICAS (Show de raciocínio)
**Title:** Decisões de Arquitetura — Por Que Assim?
**Content (decision table):**

| Decisão | Alternativa descartada | Por quê |
|---------|----------------------|---------|
| TF-IDF puro | torch + faiss + chromadb | Python 3.14 incompatível + corpus pequeno (61 chunks) — TF-IDF resolve |
| SQLAlchemy | SQLite direto | Abstração: troca para Postgres sem mudar código |
| RF over XGBoost | XGBoost 300 trees | RF: 0.879 vs XGB: 0.840, 3x mais rápido (7.7s vs 23.3s) |
| RF default | RF tuned (balanced) | Tuning: -0.42pp → balanced penalizou maioria sem ganho |
| Anti-alucinação 3 portões | LLM direto | Defeito sem manual → zero prescrição inventada |
| Ollama on-prem | Apenas OpenRouter | LGPD: dados de sensores não podem sair da rede |

---

### Slide 17 — ENCERRAMENTO
**Title:** O Que Foi Construído
**Content (summary):**

Um sistema completo de manutenção prescritiva que vai além do preditivo:
- **Classifica** o defeito automaticamente (RF, 87.9%)
- **Prescreve** a correção via manuais técnicos (RAG anti-alucinação)
- **Classifica** a criticidade (semáforo 🔴🟡🟢)
- **Acompanha** o ciclo de vida do reparo (pendente → resolvido)
- **Opera** em 3 canais com compliance LGPD by design

**Bottom:** Contato / QR code para repositório

---

## INSTRUÇÕES DE DESIGN PARA O CANVA

1. **Tema:** Busque por "dark dashboard" ou "technology presentation" no Canva
2. **Cores:** Use o hex #10F5A3 (neon green) como cor principal de destaque, #0B0E13 como fundo
3. **Fonte:** Inter, Montserrat, ou similar sans-serif clean
4. **Ícones:** Use ícones minimalistas/geometric (Canva tiene biblioteca de tech icons)
5. **Gráficos:** Para os slides 5, 6, 9 — crie gráficos simples inline (barras horizontais com cores)
6. **Animações:** Use "Appear" ou "Fade" nas bullets para apresentação ao vivo
7. **Layout:** Máximo 5-6 bullets por slide. Muita informação → divida em 2 slides
8. **Exportação:** PDF para backup + link compartilhável para envio
