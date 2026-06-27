# US-012 — Edição de Status, Comentário e Auditoria

**MoSCoW:** Must
**Personas:** Engenheiro de Manutenção, Técnico de Manutenção

---

## User Story

> Como **Engenheiro de Manutenção**, quero **editar o status semáforo de um evento,
> registrar um comentário e salvar no banco**,
> para **documentar a resolução da manutenção e alimentar o histórico de tratativas**.

---

## Critérios de Aceite

**Given** que o engenheiro localiza um evento na tabela do dashboard,

**When** clica em "Editar status",

**Then** formulário disponível com:
- **Status** — select: 🔴 Crítico / 🟡 Atenção / 🟢 Resolvido
- **Comentário** — textarea (ex: "Balanceamento executado. Máquina retornou ao normal.")
- **Responsável** — texto livre
- Botão "Salvar"

**When** salva,

**Then**:
- Banco atualiza: `status_manutencao`, `comentario`, `responsavel`, `data_atualizacao`
- Registro de auditoria criado: quem mudou, de qual status, para qual status, quando
- KPIs do dashboard recalculados
- Série temporal de resolvidos atualiza se novo 🟢 registrado

**Given** que o evento é marcado como 🟢 Resolvido,

**When** salva,

**Then**:
- Evento sai dos contadores 🔴/🟡
- Entra na contagem de "Resolvidos hoje" e na série temporal
- Comentário obrigatório para resolução (não permite 🟢 sem comentário)

**Given** que o gerente ou diretor acessa o painel depois,

**When** visualiza o evento,

**Then** vê o histórico de alterações de status (quem, quando, de→para, comentário).

---

## Schema de Banco (novos campos em `eventos`)

```sql
status_manutencao  TEXT     -- '🔴 Crítico' | '🟡 Atenção' | '🟢 Resolvido'
comentario         TEXT
responsavel        TEXT
data_atualizacao   DATETIME
-- tabela de auditoria separada:
-- status_historico(evento_id, status_anterior, status_novo, responsavel, data, comentario)
```

---

## Arquivos Envolvidos

- `src/app/streamlit_app.py` — formulário de edição
- `src/app/ui.py` — `form_edicao_status(evento_id)`
- `src/core/db.py` — `atualizar_status(evento_id, status, comentario, responsavel)` + tabela `status_historico`
