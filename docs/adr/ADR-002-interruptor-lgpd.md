# ADR-002 — Interruptor LGPD: LLM_PROVIDER ollama ↔ openrouter

**Status:** Aceita
**Data:** 2026-06-26
**Autores:** Arquiteto

---

## Contexto

O sistema lida com dados industriais sensíveis: eventos de sensores e conteúdo de manuais
técnicos proprietários. A LGPD (Lei 13.709/2018) e as políticas internas da empresa
industrial exigem que dados de produção **não trafeguem para serviços externos** sem
controle explícito.

Ao mesmo tempo, a demo para a banca avaliadora precisa de um LLM respondendo rapidamente
sem GPU local.

---

## Decisão

Implementar um **gateway LLM com interruptor por variável de ambiente** `LLM_PROVIDER`:

```
LLM_PROVIDER=ollama     → LLM local (Ollama, on-prem, sem rede)
LLM_PROVIDER=openrouter → API externa (OpenRouter, apenas para demo)
```

O gateway (`src/core/llm.py`) encapsula a lógica; o restante do sistema chama apenas
`llm_generate(prompt, contexto)` sem saber qual provedor está ativo.

---

## Alternativas Consideradas

| Alternativa | Por que rejeitada |
|---|---|
| Sempre usar API externa | Viola LGPD em produção; dados saem da empresa |
| Sempre usar LLM local | Demo lenta em CPU (57s); impraticável para HF Spaces |
| Dois sistemas separados | Duplica manutenção; riscos de divergência de comportamento |
| Feature flag no código | Variável de ambiente é mais operacional e não requer redeploy |

---

## Consequências

**Positivas:**
- Conformidade LGPD garantida no perfil `ollama` — verificável tecnicamente
- Mesmo código em produção e demo — sem bifurcação de lógica
- Decisão é **mecanismo**, não slide — pode ser mostrado e explicado na entrevista
- Adicionar novo provedor = adicionar branch em `llm.py`

**Negativas / Trade-offs:**
- Operador precisa garantir que configura `ollama` em produção (risco humano)
- Qualidade de resposta pode diferir entre modelos ollama e openrouter
  — aceitável pois os prompts são idênticos e o contexto RAG é o mesmo

**Regra de ouro documentada no README:**
> `openrouter`: só com dados sintéticos. `ollama`: dados reais de produção.
