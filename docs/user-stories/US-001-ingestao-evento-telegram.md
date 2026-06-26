# US-001 — Ingestão de Evento JSON via Telegram

**MoSCoW:** Must
**Persona:** Operador de Campo

---

## User Story

> Como **Operador de Campo**, quero **enviar um JSON de evento de sensor pelo Telegram**,
> para **receber imediatamente a análise do defeito provável e o procedimento de correção**
> sem precisar acessar nenhum sistema especial.

---

## Critérios de Aceite

**Given** que o Telegram bot está rodando e o operador envia uma mensagem contendo JSON
com as 23 features de vibração e o campo `rpm`,

**When** o bot processa a mensagem,

**Then**:
- O sistema identifica o defeito mais provável com base nos k=5 casos históricos mais similares
- O sistema retorna quantas vezes esse defeito ocorreu no histórico e a frequência (% do total)
- O sistema recupera o trecho do manual correspondente e redige a prescrição de correção
- Se o defeito **não tem manual**: retorna mensagem explicando que não há procedimento
  documentado e que a solicitação foi registrada para documentação futura
- A resposta aparece no Telegram em menos de 60 segundos
- O evento e a prescrição são gravados no banco de dados

**Given** que o JSON enviado é inválido ou incompleto,

**When** o bot tenta processar,

**Then** retorna mensagem de erro clara indicando os campos ausentes, sem travar o bot.

---

## Arquivos Envolvidos

- `src/bot/telegram_bot.py` — handler de mensagem JSON
- `src/core/backend.py` — função `responder_evento(json)`
- `src/core/pipeline.py` — orquestração similaridade → RAG → LLM
- `src/core/db.py` — gravação do evento e prescrição
