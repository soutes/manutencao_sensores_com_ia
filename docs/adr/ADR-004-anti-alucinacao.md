# ADR-004 — Anti-alucinação: Prompt Restrito ao Contexto + Gating de Cobertura

**Status:** Aceita
**Data:** 2026-06-26
**Autores:** Arquiteto

---

## Contexto

LLMs têm tendência a "completar" respostas com informações plausíveis mas incorretas
(alucinação). Em contexto industrial, uma prescrição de manutenção inventada pode causar
danos à máquina ou acidentes. O sistema precisa garantir **rastreabilidade** —
cada afirmação na prescrição deve ter origem nos manuais da empresa.

A banca avaliadora explicitamente vai testar "alucinação do modelo" na entrevista.

---

## Decisão

Dois mecanismos combinados, por camadas:

**Camada 1 — Prompt engineering restritivo:**
```
Você é um especialista em manutenção industrial.
Responda SOMENTE com base no contexto abaixo.
Se a informação não estiver no contexto, diga "não encontrado no manual".
NÃO invente procedimentos.

CONTEXTO:
{trechos_recuperados}

PERGUNTA: {defeito_identificado}
```

**Camada 2 — Gating de cobertura:**
- RAG calcula score de similaridade do melhor trecho recuperado
- Se score < limiar (0.20 por padrão): bloqueia chamada ao LLM
- Retorna mensagem padronizada e registra em `pendencias`
- Dois tipos de gating: (a) defeito sem manual no índice, (b) manual presente mas
  sem trecho suficientemente relevante

---

## Alternativas Consideradas

| Alternativa | Por que rejeitada |
|---|---|
| Confiar no LLM sem restrição | Alucinação inevitável; inaceitável em contexto industrial |
| Validação pós-geração por segundo LLM | Dobra latência e custo; complexidade sem garantia |
| Só gating, sem prompt restritivo | LLM ainda pode alucinar dentro do contexto |
| Só prompt restritivo, sem gating | LLM pode ignorar instrução; sem garantia formal |

---

## Consequências

**Positivas:**
- Camada dupla: engenharia de prompt + verificação de cobertura
- Gating é determinístico e auditável (não depende do LLM)
- Defensável na entrevista: "duas linhas de defesa distintas"
- Pendências são registradas — empresa sabe o que documentar

**Negativas / Trade-offs:**
- Limiar de cobertura (0.20) pode ser conservador — alguns casos válidos caem no gating
  — preferível falso negativo (pede documentação) a falso positivo (inventa prescrição)
- TF-IDF pode ter baixo recall em perguntas com vocabulário diferente do manual
  — aceitável; corpus de manuais técnicos tem vocabulário controlado
