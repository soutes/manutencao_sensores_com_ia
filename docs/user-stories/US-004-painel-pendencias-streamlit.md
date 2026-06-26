# US-004 — Painel de Pendências sem Documento (Streamlit)

**MoSCoW:** Must
**Persona:** Engenheiro de Manutenção

---

## User Story

> Como **Engenheiro de Manutenção**, quero **ver no dashboard a lista de defeitos que
> ocorreram mas não têm procedimento documentado**,
> para **priorizar a criação de novos manuais** e fechar lacunas no conhecimento da planta.

---

## Critérios de Aceite

**Given** que o engenheiro acessa a aba/página "Pendências" no dashboard,

**When** a página carrega,

**Then**:
- Exibe tabela com todos os registros da tabela `pendencias`: defeito, data do primeiro
  registro, número de ocorrências sem cobertura
- Ordena por número de ocorrências (maior primeiro) — prioriza o que mais impacta
- Exibe alerta visual (cor destacada) para defeitos com mais de 5 ocorrências sem documento
- Inclui botão conceitual "Exportar lista" (pode ser apenas download CSV)

**Given** que não há pendências registradas,

**When** a página carrega,

**Then** exibe mensagem positiva "Todos os defeitos possuem documentação" sem erro.

---

## Arquivos Envolvidos

- `src/app/streamlit_app.py` — aba/página de pendências
- `src/app/ui.py` — componentes visuais
- `src/core/db.py` — função `listar_pendencias()`
