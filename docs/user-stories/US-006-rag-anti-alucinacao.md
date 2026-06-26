# US-006 — Anti-alucinação — RAG Restrito ao Contexto

**MoSCoW:** Must
**Persona:** Sistema (requisito crítico de confiabilidade)

---

## User Story

> Como **sistema**, quero **garantir que o LLM só use informações dos trechos do manual
> recuperados pelo RAG**,
> para **eliminar o risco de prescrições inventadas** que poderiam causar danos à máquina
> ou acidentes de trabalho.

---

## Critérios de Aceite

**Given** que o RAG recuperou trechos relevantes do manual para o defeito identificado,

**When** o LLM é chamado para redigir a prescrição,

**Then**:
- O prompt instrui explicitamente o LLM a usar **somente** as informações do contexto fornecido
- O prompt instrui a dizer "não sei" ou "não encontrado no manual" se a informação não estiver
  no contexto
- A prescrição gerada não contém informações que não estejam nos trechos recuperados
  (verificável manualmente cruzando saída com contexto)

**Given** que o sistema é revisado por auditor (avaliador da FIESC),

**When** o auditor cruza a prescrição com os manuais originais,

**Then** toda afirmação na prescrição tem fonte rastreável nos trechos fornecidos ao LLM.

**Given** que o LLM retorna resposta que menciona algo além do contexto,

**When** o sistema avalia (futuro — fora do escopo atual),

**Then** o sistema marca a prescrição como "não verificada" e não a exibe ao operador.

---

## Arquivos Envolvidos

- `src/core/rag.py` — recuperação de trechos + montagem do contexto
- `src/core/llm.py` — template do prompt com restrição de contexto
- `src/core/pipeline.py` — passagem do contexto RAG para o LLM
