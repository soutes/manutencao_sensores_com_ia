# US-008 — Operação Cloud com OpenRouter (Modo Demo)

**MoSCoW:** Should
**Persona:** Avaliador / Demonstrador

---

## User Story

> Como **demonstrador do sistema para a banca avaliadora**,
> quero poder ativar o modo cloud com OpenRouter e banco Supabase,
> para **fazer uma demo ao vivo com resposta rápida** sem precisar de GPU local.

---

## Critérios de Aceite

**Given** que `.env` contém `LLM_PROVIDER=openrouter`, `OPENROUTER_API_KEY=<key>` e
`DATABASE_URL=postgresql://...` (Supabase),

**When** o pipeline é executado,

**Then**:
- O LLM chamado é OpenRouter (modelo configurado em `OPENROUTER_MODEL`)
- Eventos são persistidos no banco Supabase (PostgreSQL remoto)
- A resposta chega em menos de 15 segundos (latência cloud vs 57s CPU local)

**Given** que a chave OpenRouter é inválida ou expirada,

**When** a chamada falha,

**Then** o sistema retorna erro claro com indicação do problema sem expor a chave no log.

**Given** que o Supabase está indisponível,

**When** a gravação falha,

**Then** o sistema retorna a prescrição ao usuário mesmo assim (a análise não falha por
causa do banco) e registra o erro em log.

---

## Arquivos Envolvidos

- `src/core/config.py` — leitura de variáveis do perfil cloud
- `src/core/llm.py` — branch openrouter
- `src/core/db.py` — SQLAlchemy aceita URL Postgres transparentemente
- `.env.example` — perfil cloud documentado
