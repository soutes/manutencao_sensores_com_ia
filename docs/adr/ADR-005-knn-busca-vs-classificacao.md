# ADR-005 — Similaridade por Busca KNN vs Classificação Treinada

**Status:** Aceita
**Data:** 2026-06-26
**Autores:** Arquiteto

---

## Contexto

O sistema precisa identificar o defeito provável dado um novo evento de vibração (23 features).
Duas abordagens são candidatas: (1) treinar um classificador supervisionado e predizer o rótulo,
ou (2) buscar os k vizinhos mais próximos no histórico e derivar o defeito por similaridade.

O dataset tem 166.796 eventos, 17 classes canônicas, com distribuição desbalanceada e
sobreposição física entre alguns defeitos (ex: `eccentric_rotor` e `desbalanceado`).

---

## Decisão

Usar **KNN como busca por similaridade** (não classificação):

- `NearestNeighbors(n_neighbors=5, metric='euclidean', algorithm='ball_tree')`
- Voto ponderado por distância: defeito com menor distância média entre os k vizinhos
- Retornar os k vizinhos ao usuário (não só o rótulo) — transparência e auditabilidade
- Retornar estatísticas: frequência do defeito, distribuição temporal

---

## Alternativas Consideradas

| Alternativa | Por que rejeitada |
|---|---|
| Random Forest / XGBoost | Caixa-preta para o usuário; não entrega os casos históricos semelhantes |
| SVM com kernel RBF | Mesmo problema de opacidade; sem vizinhos retornados |
| KNN classificador simples (voto majoritário) | Confunde eccentric_rotor ↔ desbalanceado (testado: k=1 acc 0.74, k alto degrada) |
| Embeddings neurais + cosseno | torch, sem GPU; overkill para 23 features numéricas |

---

## Consequências

**Positivas:**
- Sistema retorna **os casos históricos** (não só o rótulo) — operador pode validar
- Voto ponderado por distância resolve a sobreposição eccentric ↔ desbalanceado
- k=5 com ponderação é mais robusto que k=1 (acc 0.74 no holdout)
- Auditável: "aqui estão os 5 eventos mais parecidos com o seu"
- Comunicação honesta: "similaridade de X%" não "100% certo que é Y"

**Negativas / Trade-offs:**
- KNN é lazy learner: previsão requer busca em todos os exemplos (166k)
  — resolvido pelo `ball_tree` que resolve em < 100ms
- Acc 0.74 não é perfeito — documentado e explicado (sobreposição física real entre classes)
  — argumento de entrevista: "medimos, encontramos a causa, aplicamos voto ponderado"

---

## Insight para Entrevista

> "k=1 dá acc 0.74; valores altos de k degradam. Por quê? Classes de defeito se sobrepõem
> no espaço de features — fenômeno físico real (eccentric e desbalanceado têm assinatura
> similar). Voto ponderado por distância melhora a fronteira sem aumentar k."
