# US-009 — Notebook EDA com Métricas e Insights

**MoSCoW:** Should
**Persona:** Engenheiro de Manutenção / Avaliador Técnico

---

## User Story

> Como **avaliador técnico da FIESC**,
> quero ver um notebook Jupyter com análise exploratória dos dados de vibração,
> para **avaliar a profundidade analítica do candidato e a qualidade do modelo de similaridade**.

---

## Critérios de Aceite

**Given** que o avaliador abre `notebooks/analise.ipynb`,

**When** executa todas as células em ordem,

**Then**:
- Carrega `data/banner_clean.parquet` sem erro
- Exibe distribuição dos 17 defeitos canônicos (gráfico de barras ou pizza)
- Exibe distribuição temporal dos eventos (histograma por período)
- Exibe holdout accuracy do KNN (≥ 0.70) com curva de k vs accuracy
- Exibe matriz de confusão dos principais defeitos
- Identifica e comenta o par `eccentric_rotor ↔ desbalanceado` (sobreposição física)
- Exibe cobertura documental: quais defeitos têm manual, quais não têm (gráfico)
- Inclui ao menos 3 insights analíticos comentados (não apenas gráficos sem explicação)
- Termina com tabela de resumo das métricas

**Given** que o notebook roda com Python 3.14 e as dependências do projeto,

**When** executado em ambiente limpo,

**Then** todas as células executam sem erro (nenhuma célula com `NameError`, `ImportError`
ou `FileNotFoundError`).

---

## Arquivos Envolvidos

- `notebooks/analise.ipynb` — notebook principal (a criar)
- `data/banner_clean.parquet` — dados processados
- `src/core/similarity.py` — importado para demonstrar o modelo
