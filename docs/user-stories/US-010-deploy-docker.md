# US-010 — Deploy Docker On-Prem

**MoSCoW:** Must
**Persona:** Ops / Avaliador Técnico

---

## User Story

> Como **avaliador técnico**,
> quero executar `docker compose up` e ter o sistema completo rodando,
> para **confirmar que o projeto é deployável em ambiente industrial real** sem configuração manual.

---

## Critérios de Aceite

**Given** que o avaliador tem Docker e Docker Compose instalados,

**When** executa `docker compose up` na raiz do projeto,

**Then**:
- FastAPI sobe em `localhost:8000` com Swagger disponível em `/docs`
- Streamlit sobe em `localhost:8501`
- Telegram bot inicia (aguarda token no `.env`)
- Todos os serviços sobem sem erro em menos de 2 minutos
- Banco SQLite é inicializado automaticamente na primeira execução

**Given** que `TELEGRAM_TOKEN` não está configurado no `.env`,

**When** o compose sobe,

**Then** apenas o serviço do bot falha com mensagem clara; FastAPI e Streamlit sobem normalmente.

**Given** que o avaliador executa `docker compose down`,

**When** os serviços param,

**Then** o banco SQLite é preservado no volume (dados não são perdidos).

---

## Arquivos Envolvidos

- `docker-compose.yml` — já existente, verificar se cobre todos os serviços
- `Dockerfile` — já existente
- `.env.example` — referência para configuração mínima
