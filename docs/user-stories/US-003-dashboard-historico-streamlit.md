# US-003 — Dashboard Multi-Stakeholder (Streamlit)

**MoSCoW:** Must
**Personas:** Operador, Engenheiro de Manutenção, Gerente, Diretor

---

## User Story

> Como **qualquer stakeholder do parque fabril**, quero **um dashboard com visão clara
> do status de manutenção**, para **monitorar prioridades, editar status, registrar
> comentários e acompanhar a evolução ao longo do tempo**.

---

## Critérios de Aceite

---

### Painel 1 — KPIs e Semáforo (visão gerencial)

**Given** que qualquer usuário abre o dashboard,

**When** a página principal carrega,

**Then** exibe bloco de KPIs no topo:

| KPI | Descrição |
|---|---|
| 🔴 Crítico | N eventos com status crítico em aberto |
| 🟡 Atenção | N eventos com status atenção em aberto |
| 🟢 Resolvido | N eventos resolvidos (hoje / esta semana) |
| ⚠️ Sem manual | N defeitos sem procedimento documentado |
| 📋 Total eventos | N eventos analisados (período selecionável) |
| 🔁 Defeito mais frequente | Tipo + contagem no período |
| ⏱️ Tempo médio de resolução | Média entre criação e marcação como 🟢 |

---

### Painel 2 — Série Temporal de Resolvidos

**Given** que existem eventos com `status_manutencao = 🟢`,

**When** o dashboard carrega,

**Then** exibe gráfico de linha ou barras com:
- Eixo X: data (dia ou semana)
- Eixo Y: contagem de eventos resolvidos
- Linha secundária: eventos abertos (🔴 + 🟡) no mesmo período
- Permite filtrar por tipo de defeito

---

### Painel 3 — Tabela de Eventos com Semáforo

**Given** que o engenheiro ou operador acessa a aba "Eventos",

**When** a tabela carrega,

**Then**:
- Exibe: data/hora, defeito, confiança KNN (%), semáforo (ícone colorido), comentário, última atualização
- Filtros: por semáforo (🔴🟡🟢), por tipo de defeito, por período
- Ordenação padrão: 🔴 primeiro, depois 🟡, depois 🟢

---

### Painel 4 — Edição de Status e Comentário

**Given** que o engenheiro seleciona um evento na tabela,

**When** clica em "Editar",

**Then** abre formulário inline (ou sidebar) com:
- Campo: **Status** (select: 🔴 Crítico / 🟡 Atenção / 🟢 Resolvido)
- Campo: **Comentário** (textarea — ex: "Balanceamento realizado em 27/06, máquina OK")
- Campo: **Responsável** (texto livre ou dropdown)
- Botão **Salvar**

**When** salva,

**Then**:
- Banco atualizado: `status_manutencao`, `comentario`, `responsavel`, `data_atualizacao`
- Tabela de eventos atualiza imediatamente (sem recarregar a página inteira)
- Série temporal de resolvidos atualiza (se novo 🟢)
- KPIs atualizam

---

### Painel 5 — Distribuição por Defeito

**Given** que o engenheiro acessa a aba "Análise",

**When** carrega,

**Then** exibe:
- Gráfico de barras: N eventos por tipo de defeito (colorido por semáforo predominante)
- Gráfico de pizza: distribuição 🔴🟡🟢 do período selecionado
- Tabela de cobertura: quais defeitos têm manual (🟩) e quais não têm (🟥)

---

### Painel 6 — Pendências sem Documentação

**Given** que o engenheiro acessa a aba "Pendências",

**When** carrega,

**Then**:
- Tabela: defeito, data primeiro registro, N ocorrências, todos com 🔴 implícito
- Ordenada por frequência (maior impacto primeiro)
- Alerta visual para defeitos com > 5 ocorrências

---

## Regras de Negócio do Semáforo

| Status | Critério inicial (automático) |
|---|---|
| 🔴 Crítico | Defeito sem manual OU defeito com manual e alta frequência (> N/período) |
| 🟡 Atenção | Defeito com manual identificado, aberto, primeira ocorrência ou baixa frequência |
| 🟢 Normal | Estado operacional (normal/baseline) OU evento editado manualmente como resolvido |

> Status pode ser **sobrescrito manualmente** pelo engenheiro (Painel 4).
> A alteração manual tem precedência e é auditada (quem mudou + quando).

---

## Arquivos Envolvidos

- `src/app/streamlit_app.py` — todos os painéis acima
- `src/app/ui.py` — componentes: `kpi_semaforo()`, `badge_status()`, `form_edicao_status()`
- `src/core/db.py` — `listar_eventos()`, `atualizar_status()`, `serie_temporal_resolvidos()`, `resumo_semaforo()`
