# US-002 — Q&A sobre Histórico e Pendências via Telegram

**MoSCoW:** Should
**Persona:** Operador de Campo

---

## User Story

> Como **Operador de Campo**, quero **fazer perguntas em texto livre pelo Telegram**
> sobre defeitos recentes ou pendências não documentadas,
> para **entender o histórico da máquina sem precisar acessar o computador**.

---

## Critérios de Aceite

**Given** que o operador envia uma mensagem de texto (não JSON) no Telegram,

**When** o bot detecta que não é um evento JSON,

**Then**:
- O sistema encaminha a pergunta para a função `responder_duvida(texto)`
- O RAG busca nos manuais trechos relevantes à pergunta
- O LLM responde baseado **apenas** nos trechos recuperados
- Se nenhum trecho relevante for encontrado: informa ao operador que não há documentação
  e sugere contatar o engenheiro responsável
- A resposta aparece no Telegram em menos de 60 segundos

**Given** que o operador pergunta "quais defeitos estão pendentes de documentação?",

**When** o bot processa,

**Then** retorna a lista de defeitos na tabela `pendencias` com data de registro e contagem.

**Given** que o operador pergunta sobre o histórico recente da máquina,

**When** o bot processa,

**Then** retorna os últimos N eventos registrados no banco com defeito e data.

---

## Arquivos Envolvidos

- `src/bot/telegram_bot.py` — detecção tipo mensagem + roteamento
- `src/core/backend.py` — função `responder_duvida(texto)`
- `src/core/rag.py` — recuperação de trechos
- `src/core/db.py` — consulta a eventos e pendências
