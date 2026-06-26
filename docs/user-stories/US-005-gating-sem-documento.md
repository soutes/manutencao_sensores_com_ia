# US-005 — Gating "Sem Documento" — Registrar Pendência

**MoSCoW:** Must
**Persona:** Sistema (requisito crítico de negócio)

---

## User Story

> Como **sistema**, quero **detectar quando o defeito identificado não possui manual
> de procedimento** e registrar isso como pendência,
> para **garantir que o LLM nunca invente uma prescrição** e a empresa saiba o que
> ainda precisa ser documentado.

---

## Critérios de Aceite

**Given** que o pipeline identificou o defeito como `eccentric_rotor`, `ventoinha`
ou `falta_fase` (defeitos sem cobertura documental),

**When** o sistema tenta recuperar o manual,

**Then**:
- O RAG não encontra trecho relevante (score de cobertura abaixo do limiar)
- O sistema **não chama o LLM** para redigir prescrição
- Retorna mensagem padronizada: "Defeito identificado: `<defeito>`. Não há procedimento
  documentado para este defeito. Solicitação de documentação registrada."
- Insere registro na tabela `pendencias` com: defeito, data/hora, ID do evento de origem

**Given** que o mesmo defeito sem documento ocorre novamente,

**When** o sistema processa novo evento,

**Then** incrementa o contador de ocorrências no registro existente de pendência
(não duplica registros).

**Given** que o defeito tem manual mas o score de cobertura está baixo (< limiar),

**When** o sistema avalia,

**Then** também ativa o gating e registra como pendência (conservador por design).

---

## Arquivos Envolvidos

- `src/core/pipeline.py` — lógica de gating (verificação de cobertura)
- `src/core/rag.py` — score de cobertura do contexto recuperado
- `src/core/db.py` — `registrar_pendencia()` com upsert por defeito
