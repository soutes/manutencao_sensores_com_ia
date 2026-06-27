# US-004 — Painel de Pendências sem Documento

**MoSCoW:** Must
**Personas:** Engenheiro de Manutenção, Gerente

---

## User Story

> Como **Engenheiro de Manutenção ou Gerente**, quero **ver os defeitos sem procedimento
> documentado com semáforo de prioridade**,
> para **priorizar a criação de manuais e fechar as lacunas de maior impacto no parque**.

---

## Critérios de Aceite

**Given** que o usuário acessa a aba "Pendências",

**When** a página carrega,

**Then**:
- Tabela com: defeito, 🔴 Crítico implícito, data do primeiro registro,
  N ocorrências sem cobertura, última ocorrência
- Ordenada por N ocorrências (maior impacto primeiro)
- Badge 🔴 em todos os itens (sem manual = sempre crítico)
- Alerta visual destacado para > 5 ocorrências

**Given** que não há pendências,

**When** carrega,

**Then** mensagem positiva "✅ Todos os defeitos possuem documentação" sem erro.

**Given** que o gerente ou diretor vê o painel,

**When** visualiza,

**Then** consegue entender sem contexto técnico:
- Qual defeito ocorre mais
- Há quanto tempo está sem procedimento
- Quantas vezes ocorreu sem resolução documentada

---

## Arquivos Envolvidos

- `src/app/streamlit_app.py` — aba Pendências
- `src/app/ui.py` — `badge_status()`, `alerta_sem_doc()`
- `src/core/db.py` — `listar_pendencias()` com contagem e datas
