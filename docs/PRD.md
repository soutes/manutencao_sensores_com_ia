# PRD — Manutenção Prescritiva (Case SENAI/FIESC)

**Versão:** 1.0 | **Data:** 2026-06-26 | **Autor:** Product Owner
**Deadline de entrega:** 29/06/2026 14h | **Entrevista:** 01/07/2026

---

## 1. Visão e Problema

### Contexto

Indústria de grande porte em Santa Catarina opera máquinas rotativas equipadas com sensores
de vibração. O regime atual de manutenção é **reativo**: a equipe intervém após a falha.
O custo de paradas não programadas (downtime, peças, mão de obra) é alto e evitável.

### Problema Central

A empresa possui:
- **Histórico de 166.796 eventos** de vibração com rótulo de defeito (banner.csv)
- **6 manuais técnicos** descrevendo procedimentos de correção para defeitos conhecidos
- Operadores no campo sem acesso rápido ao procedimento correto no momento da falha

Faltam dois elos: (1) identificar o defeito provável a partir da assinatura de vibração e
(2) entregar ao operador o procedimento correto **com garantia de que não foi inventado**.

### Solução

Sistema de **Manutenção Prescritiva** que:
1. Recebe evento JSON de sensor (23 features de vibração + rpm)
2. Encontra casos históricos semelhantes via KNN (similaridade, não classificação)
3. Recupera o trecho do manual correspondente via RAG (TF-IDF + cosseno)
4. Redige a prescrição com LLM restrito ao trecho recuperado (anti-alucinação)
5. Se não há manual para o defeito: **registra solicitação de documentação** (nunca inventa)
6. Persiste tudo no banco de dados para rastreabilidade

### Restrição LGPD

Dados industriais são sensíveis. O sistema deve poder operar **100% on-premises**
(LLM local via Ollama) sem que conteúdo de manuais ou eventos de produção trafeguem
para serviços externos. O perfil cloud (OpenRouter) é exclusivo para demonstração com
dados sintéticos.

---

## 2. Objetivos e Métricas de Sucesso

| Objetivo | Métrica | Alvo |
|---|---|---|
| **Diferencial 1 — APIs** | FastAPI com rotas documentadas (Swagger) | Swagger acessível em /docs |
| **Diferencial 2 — Banco** | Eventos, consultas e pendências persistidos | 3 tabelas, trocável por DATABASE_URL |
| **Diferencial 3 — Dashboard** | Streamlit com histórico + pendências + KPIs | Roda sem erro, design system aplicado |
| **Diferencial 4 — Deploy** | Docker on-prem + HF Spaces cloud | `docker compose up` funciona |
| **Diferencial 5 — Integração industrial** | Telegram bot ingerindo JSON e respondendo Q&A | Bot responde em < 30s |
| **Gating sem-doc** | Defeitos sem manual nunca recebem prescrição inventada | 100% dos casos eccentric/ventoinha/falta_fase retornam solicitação de registro |
| **Anti-alucinação** | LLM usa só trechos recuperados; prompt bloqueia invenção | Review manual confirma 0 fatos fora do contexto |
| **Acurácia de similaridade** | KNN holdout accuracy | ≥ 0.70 (obtido: 0.74) |
| **Latência aceitável** | Tempo de resposta end-to-end | < 60s na CPU (obtido: 57s Ollama qwen2.5:3b) |
| **Offline-capaz** | Sistema funciona sem internet com Ollama local | Pipeline completo roda sem rede |

---

## 3. Personas

### Persona A — Operador de Campo

- **Perfil:** Técnico industrial no chão de fábrica, smartphone, sem acesso a estação
- **Objetivo:** Saber rapidamente o que fazer quando sensor dispara alerta
- **Canal:** Telegram (disponível no smartphone, sem instalação extra)
- **Nível técnico:** Médio — entende termos de manutenção, não é programador
- **Necessidades:**
  - Enviar foto/JSON do evento e receber instrução clara
  - Perguntar "quais defeitos estão pendentes?" em linguagem natural
  - Respostas rápidas, objetivas, sem jargão de IA

### Persona B — Engenheiro de Manutenção

- **Perfil:** Engenheiro na estação de trabalho, acesso ao sistema de gestão
- **Objetivo:** Monitorar padrões de falha, acompanhar pendências, validar prescrições
- **Canal:** Dashboard Streamlit na estação local ou navegador
- **Nível técnico:** Alto — entende métricas, gráficos, quer detalhes técnicos
- **Necessidades:**
  - Visualizar histórico de eventos com filtros
  - Ver lista de defeitos pendentes de documentação
  - Analisar distribuição de defeitos e frequências
  - Exportar relatórios

---

## 4. Escopo

### In-Scope

- Ingestão de evento JSON (23 features vibração + rpm) via Telegram e API REST
- Análise de similaridade KNN com histórico (166k eventos, 17 defeitos canônicos)
- Recuperação de procedimento nos 6 manuais via RAG (TF-IDF + cosseno)
- Redação de prescrição via LLM (Ollama local ou OpenRouter cloud)
- Gating "sem documento" — registra pendência, nunca inventa
- Persistência em banco (SQLite on-prem ↔ Supabase cloud)
- Dashboard Streamlit multi-stakeholder: semáforo, KPIs, série temporal, edição de status
- Telegram bot (ingestão JSON + Q&A de status do parque para operador/gerente/diretor)
- Deploy Docker on-premises + HF Spaces (demo cloud)
- Notebook EDA com análise dos dados, métricas e insights

### Out-of-Scope

- Treinamento de modelo de visão computacional (câmeras)
- Suporte a múltiplas plantas (escopo: 1 planta, 1 banco)
- Autenticação e autorização complexas (fora do escopo do case)
- Integração MQTT/OPC-UA real com PLC (apenas simulador conceitual no README)
- Fine-tuning de LLM
- Interface mobile nativa (Telegram serve como proxy mobile)

---

## 5. Requisitos

### 5.1 Funcionais

| ID | Requisito | Prioridade |
|---|---|---|
| RF-01 | Sistema recebe JSON de evento via `/api/evento` (POST) e retorna análise prescritiva | Must |
| RF-02 | Sistema encontra k=5 casos históricos mais similares (KNN ponderado) | Must |
| RF-03 | Sistema recupera trecho do manual do defeito identificado via TF-IDF + cosseno | Must |
| RF-04 | LLM redige prescrição restrita ao trecho recuperado | Must |
| RF-05 | Se defeito sem manual: retorna mensagem de gating + registra em tabela `pendencias` | Must |
| RF-06 | Telegram bot aceita JSON e responde com análise + semáforo de prioridade | Must |
| RF-07 | Telegram bot responde consultas de status do parque (gerente/diretor/operador) com semáforo agregado | Should |
| RF-08 | Dashboard exibe KPIs: 🔴🟡🟢 contagens, defeito mais frequente, tempo médio de resolução | Must |
| RF-09 | Dashboard exibe série temporal de eventos resolvidos (🟢) por dia/semana | Must |
| RF-10 | Dashboard exibe tabela de eventos com semáforo editável (status + comentário + responsável) | Must |
| RF-11 | Dashboard exibe lista de pendências sem documentação com semáforo 🔴 implícito | Must |
| RF-12 | Edição de status persiste no banco com auditoria (quem, quando, de→para) | Must |
| RF-13 | Troca de LLM via variável `LLM_PROVIDER` sem alterar código | Must |
| RF-14 | Troca de banco via variável `DATABASE_URL` sem alterar código | Must |
| RF-15 | Notebook EDA com gráficos de distribuição, métricas KNN, matriz de confusão | Should |
| RF-16 | Deploy funcional via `docker compose up` | Must |
| RF-17 | Deploy alternativo via HF Spaces (demo cloud) | Could |

### 5.2 Não-Funcionais

| ID | Requisito | Detalhe |
|---|---|---|
| RNF-01 | **LGPD / privacidade** | Perfil `ollama`: nenhum dado sai da máquina; perfil `openrouter`: só dados sintéticos |
| RNF-02 | **Offline-capaz** | Pipeline completo funciona sem internet (Ollama + SQLite) |
| RNF-03 | **Hardware** | Roda em 16GB RAM (sem GPU obrigatório); otimizado para 32GB |
| RNF-04 | **Dependências leves** | Sem faiss, torch, chromadb — só sklearn, pymupdf, rapidocr |
| RNF-05 | **Latência** | Resposta end-to-end < 60s em CPU |
| RNF-06 | **Defensabilidade** | Todo código explicável pelo candidato na entrevista |
| RNF-07 | **Versionamento** | Commits incrementais com mensagem descritiva |
| RNF-08 | **Idioma** | Português em código, docstrings, commits e artefatos |

---

## 6. User Stories

Ver arquivos individuais em `docs/user-stories/`.

### Tabela Consolidada

| ID | Título | Personas | MoSCoW |
|---|---|---|---|
| US-001 | Ingestão de evento JSON via Telegram + semáforo na resposta | Operador | Must |
| US-002 | Q&A status do parque fabril via Telegram (semáforo agregado) | Operador, Gerente, Diretor | Should |
| US-003 | Dashboard multi-stakeholder: KPIs, semáforo, série temporal, edição | Todos | Must |
| US-004 | Painel de pendências sem documento com semáforo 🔴 | Engenheiro, Gerente | Must |
| US-005 | Gating "sem documento" — registrar pendência | Sistema | Must |
| US-006 | Anti-alucinação — RAG restrito ao contexto | Sistema | Must |
| US-007 | Operação offline com Ollama (modo on-prem / LGPD) | Sistema | Must |
| US-008 | Operação cloud com OpenRouter (modo demo) | Sistema | Should |
| US-009 | Notebook EDA com métricas e insights | Engenheiro | Should |
| US-010 | Deploy Docker on-prem | Ops | Must |
| US-011 | Deploy HF Spaces (demo cloud) | Ops | Could |
| US-012 | Edição de status semáforo + comentário + auditoria → banco | Engenheiro, Técnico | Must |

---

## 7. Backlog Priorizado

### Must — Entrega mínima para avaliação

1. **B1** — `responder_evento(json)` e `responder_duvida(texto)` no backend
2. **B2** — Telegram conectado ao backend (ingestão + Q&A + gravação no banco)
3. **B3** — LLM retorna JSON estruturado + relatório prescritivo narrativo
4. **F1** — Dashboard vestido com design system (histórico + pendências + KPIs)
5. **D1** — Docker compose funcional (smoke test)

### Should — Eleva qualidade da apresentação

6. **Q1** — Notebook EDA (análise + métricas + matriz de confusão + insights)
7. **D2** — Supabase + OpenRouter configurados (perfil cloud)

### Could — Diferencial extra se sobrar tempo

8. **D3** — HF Spaces deploy
9. **D4** — Diagrama de arquitetura (draw.io / mermaid)
10. **D5** — Simulador MQTT/PLC no README

### Won't (neste ciclo)

- Autenticação OAuth, multi-planta, fine-tuning, visão computacional

---

## 8. Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Ollama lento na CPU (> 60s) | Média | Médio | qwen2.5:3b já testado a 57s; aceitável |
| OpenRouter key não configurada antes da demo | Alta | Alto | Configurar + testar antes do dia |
| Supabase URL inválida quebra perfil cloud | Média | Médio | Graceful fallback para SQLite |
| Telegram token expirado/inválido | Média | Alto | Criar bot + testar no final da implementação |
| Candidato não consegue explicar ADR na entrevista | Baixa | Alto | ADRs escritas com linguagem simples e defensável |
