# US-002 — Q&A sobre Status do Parque Fabril via Telegram

**MoSCoW:** Should
**Personas:** Operador de Campo, Gerente de Manutenção, Diretor Industrial

---

## User Story

> Como **Gerente, Diretor ou Operador**, quero **fazer perguntas em linguagem natural
> pelo Telegram sobre o status do parque fabril**,
> para **obter rapidamente um panorama de prioridades, pontos de atenção e lista de
> manutenções** sem precisar abrir nenhum sistema.

---

## Critérios de Aceite

### Consulta de status geral (Gerente / Diretor)

**Given** que o usuário envia "qual o status do parque?" ou similar,

**When** o bot processa,

**Then** retorna painel resumido com semáforo:
```
📊 Status Parque Fabril — 27/06/2026
🔴 Crítico:   3 equipamentos
🟡 Atenção:   7 equipamentos
🟢 Normal:   42 equipamentos

⚠️ Pontos de atenção:
• rolamento (3x hoje) — Doc1 disponível
• eccentric_rotor (1x) — SEM manual ⚠️

📋 Pendências sem documentação: 2 defeitos
```

### Consulta de pontos de atenção

**Given** que o usuário pergunta "quais são os pontos críticos?" ou "o que precisa de atenção?",

**When** o bot processa,

**Then** retorna lista dos eventos 🔴 e 🟡 em aberto, ordenada por prioridade, com defeito,
frequência e se há manual disponível.

### Consulta de lista de manutenções

**Given** que o usuário pergunta "lista de manutenções pendentes" ou "o que está aberto?",

**When** o bot processa,

**Then** retorna lista de eventos com `status_manutencao ≠ 🟢`, agrupados por semáforo,
com data do evento e defeito identificado.

### Q&A sobre histórico com RAG + dados históricos

**Given** que o usuário pergunta algo como "quantas vezes ocorreu desbalanceamento essa semana?",

**When** o bot processa,

**Then**:
- Consulta banco de dados (histórico de eventos) para frequências e datas
- Consulta RAG (manuais) para contexto técnico do defeito
- Combina as duas fontes na resposta: "Ocorreu 5x esta semana. Procedimento: ..."

### Q&A com texto livre (Operador)

**Given** que o operador pergunta algo técnico em texto,

**When** o bot processa,

**Then**:
- RAG recupera trechos relevantes dos manuais
- LLM responde restrito ao contexto recuperado (anti-alucinação)
- Se sem trecho relevante: informa que não há documentação e sugere contato com engenheiro

### Consulta de pendências

**Given** que o usuário pergunta "quais defeitos não têm manual?",

**When** o bot processa,

**Then** retorna lista da tabela `pendencias` com defeito, data do primeiro registro e
número de ocorrências, ordenada por frequência.

---

## Fontes de Dados por Tipo de Consulta

| Tipo de pergunta | Fonte |
|---|---|
| Status geral / semáforo | Banco (tabela `eventos`) |
| Pontos de atenção | Banco (🔴🟡 em aberto) |
| Lista de manutenções | Banco (filtro por status) |
| Frequência / histórico | Banco (aggregate queries) |
| Procedimento técnico | RAG (manuais PDF) |
| Pergunta híbrida | Banco + RAG combinados |

---

## Arquivos Envolvidos

- `src/bot/telegram_bot.py` — roteamento de mensagens (JSON vs texto)
- `src/core/backend.py` — `responder_duvida(texto)` com acesso a banco + RAG
- `src/core/db.py` — `resumo_semaforo()`, `listar_criticos()`, `listar_pendencias()`
- `src/core/rag.py` — recuperação de trechos por pergunta
