# US-007 — Operação Offline com Ollama (Modo On-Prem / LGPD)

**MoSCoW:** Must
**Persona:** Sistema / Responsável de TI / LGPD

---

## User Story

> Como **responsável pela conformidade LGPD da planta**,
> quero que o sistema possa operar **100% local sem acesso à internet**,
> para que **dados de produção e conteúdo dos manuais nunca saiam da empresa**.

---

## Critérios de Aceite

**Given** que a variável de ambiente `LLM_PROVIDER=ollama` está configurada,

**When** o pipeline é executado,

**Then**:
- O LLM chamado é o Ollama local (modelo `qwen2.5:3b` ou conforme `.env`)
- Nenhuma requisição HTTP é feita a serviços externos (verificável por firewall ou log)
- O banco usado é SQLite local (se `DATABASE_URL` aponta para arquivo local)
- O pipeline completo funciona sem conexão de rede

**Given** que o servidor Ollama não está rodando quando o sistema tenta chamar o LLM,

**When** a chamada falha,

**Then** o sistema retorna erro claro: "LLM local (Ollama) não disponível. Verifique se
`ollama serve` está em execução." sem expor stack trace ao usuário final.

**Given** que o sistema roda em modo `ollama` e alguém tenta configurar `openrouter`
em produção,

**When** a mudança de variável é detectada,

**Then** o sistema não impede (é variável de ambiente), mas o README alerta claramente
que o perfil `openrouter` é apenas para demo com dados sintéticos.

---

## Arquivos Envolvidos

- `src/core/config.py` — leitura de `LLM_PROVIDER` e `DATABASE_URL`
- `src/core/llm.py` — gateway com branch ollama/openrouter
- `.env.example` — documentação dos dois perfis
