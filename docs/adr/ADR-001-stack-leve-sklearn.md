# ADR-001 — Stack Leve: sklearn KNN + TF-IDF sem faiss/torch/chromadb

**Status:** Aceita
**Data:** 2026-06-26
**Autores:** Arquiteto

---

## Contexto

O sistema precisa de dois componentes de ML:
1. **Busca por similaridade** em 166k eventos com 23 features numéricas
2. **Recuperação de texto** em corpus de 6 documentos (61 chunks)

O ambiente alvo é on-premises (CPU, sem GPU garantida). Python 3.14 está em uso.
Bibliotecas como `faiss` (C++), `torch` (grande), `chromadb` (dependências complexas)
apresentam riscos de compatibilidade com Python 3.14 e aumentam o tamanho do Docker image.

---

## Decisão

Usar **sklearn** (`NearestNeighbors` + `TfidfVectorizer`) para ambos os componentes.

- **Similaridade:** `NearestNeighbors(algorithm='ball_tree')` com `StandardScaler`
- **RAG retriever:** `TfidfVectorizer` + similaridade de cosseno (`cosine_similarity`)

---

## Alternativas Consideradas

| Alternativa | Por que rejeitada |
|---|---|
| `faiss` (Meta) | Requer compilação C++; compatibilidade incerta com Python 3.14; overkill para 166k×23 |
| `chromadb` | Dependências pesadas; adiciona complexidade de servidor; desnecessário para 61 chunks |
| `torch` + embeddings neurais | GPU opcional mas necessária para performance; 2GB+ de modelo; não defensável sem GPU |
| Elasticsearch | Infraestrutura adicional; fora do escopo on-prem simples |

---

## Consequências

**Positivas:**
- sklearn é puro Python, compatível com Python 3.14 sem compilação
- `NearestNeighbors` em 166k×23 resolve em < 100ms em CPU — sem necessidade de índice vetorial
- Corpus de 61 chunks é pequeno demais para justificar embeddings neurais
- Código simples e defensável na entrevista

**Negativas / Trade-offs:**
- TF-IDF não captura semântica (ex: "vibração axial" ≠ "oscilação no eixo")
  — aceitável para manuais técnicos com vocabulário controlado
- Se o corpus crescer para milhares de documentos, migrar para `faiss` ou `sentence-transformers`
