# US-011 — Deploy HF Spaces (Demo Cloud)

**MoSCoW:** Could
**Persona:** Avaliador / Demonstrador

---

## User Story

> Como **demonstrador**,
> quero ter o dashboard Streamlit disponível publicamente no Hugging Face Spaces,
> para **compartilhar uma demo ao vivo antes da entrevista** sem que o avaliador
> precise instalar nada.

---

## Critérios de Aceite

**Given** que o código está no HF Spaces com `LLM_PROVIDER=openrouter` e
`DATABASE_URL` apontando para Supabase,

**When** o avaliador acessa a URL pública do Space,

**Then**:
- O dashboard Streamlit carrega e exibe dados de demonstração
- É possível simular um evento pelo painel e receber a prescrição
- O aviso de "dados sintéticos / modo demo" está visível na interface

**Given** que o HF Space é gratuito (CPU básica),

**When** uma requisição LLM é feita,

**Then** usa OpenRouter (não Ollama, que não roda no Space gratuito) e responde em < 15s.

---

## Arquivos Envolvidos

- `src/app/streamlit_app.py` — entrada do Space
- `requirements.txt` — dependências para HF
- `README.md` — link para o Space
