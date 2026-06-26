# ADR-006 — Deploy: Docker On-Prem + HF Spaces Cloud (não Vercel)

**Status:** Aceita
**Data:** 2026-06-26
**Autores:** Arquiteto

---

## Contexto

O sistema tem dois alvos de deploy: (1) ambiente industrial on-premises (máquina Linux
com Docker) e (2) demo pública para a banca avaliadora sem instalação local.

Precisa-se de uma plataforma cloud gratuita ou de baixo custo que suporte Python/Streamlit
com algum estado persistente.

---

## Decisão

**On-prem:** `docker compose up` com serviços FastAPI + Streamlit + bot Telegram.

**Cloud demo:** Hugging Face Spaces (Streamlit SDK), com banco Supabase e LLM OpenRouter.

---

## Alternativas Consideradas

### Vercel (rejeitado)

| Razão | Detalhe |
|---|---|
| Serverless, sem estado | Cada invocação = processo novo; modelos sklearn não persistem em memória |
| Sem suporte a Streamlit | Vercel roda Next.js/React; Streamlit exige processo Python com estado |
| Cold start | `NearestNeighbors` fit() em 166k amostras a cada request = inaceitável |
| Timeout | Funções serverless têm timeout de segundos; LLM local leva 57s |

### Render / Railway

| Razão | Detalhe |
|---|---|
| Viável tecnicamente | Suportam Docker; mais fácil de configurar que HF |
| Menos visível | HF Spaces tem descoberta orgânica para projetos de ML |

### HF Spaces (escolhido)

| Vantagem | Detalhe |
|---|---|
| Streamlit nativo | SDK Streamlit é suportado primeiro pela plataforma |
| Gratuito | Tier CPU gratuito suficiente com OpenRouter |
| Visibilidade | Comunidade ML; link público profissional |
| `.env` via Secrets | Chaves seguras via interface HF |

---

## Consequências

**Positivas:**
- Docker on-prem = ambiente de produção realista para industrial
- HF Spaces = demo instantânea sem que avaliador instale nada
- Mesmo código nas duas plataformas; diferença só nas variáveis de ambiente

**Negativas / Trade-offs:**
- HF Spaces gratuito reinicia contêiner periodicamente → usar Supabase para persistência
- HF Spaces não roda Ollama → demo usa OpenRouter (aceito: são dados sintéticos)
- Deploy HF requer push para repositório HF ou GitHub Actions
  — documentado no README com passos explícitos
