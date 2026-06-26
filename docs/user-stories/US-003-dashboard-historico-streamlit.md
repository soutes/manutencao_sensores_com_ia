# US-003 — Dashboard de Histórico de Eventos (Streamlit)

**MoSCoW:** Must
**Persona:** Engenheiro de Manutenção

---

## User Story

> Como **Engenheiro de Manutenção**, quero **visualizar o histórico de eventos analisados**
> em um dashboard web,
> para **monitorar padrões de falha, frequências e prescrições aplicadas** sem precisar
> consultar o banco diretamente.

---

## Critérios de Aceite

**Given** que o engenheiro acessa o dashboard Streamlit,

**When** a página de histórico carrega,

**Then**:
- Exibe tabela com todos os eventos registrados: data/hora, defeito identificado, confiança
  do KNN, prescrição gerada, provedor LLM usado
- Permite filtrar por tipo de defeito
- Exibe KPIs resumidos: total de eventos, defeito mais frequente, eventos sem documento
- Aplica o design system do projeto (cores, tipografia, layout consistente com `ui.py`)
- Carrega em menos de 5 segundos para até 10.000 eventos

**Given** que não há eventos no banco ainda,

**When** a página carrega,

**Then** exibe mensagem "Nenhum evento registrado ainda" sem erro.

---

## Arquivos Envolvidos

- `src/app/streamlit_app.py` — página de histórico
- `src/app/ui.py` — componentes do design system
- `src/core/db.py` — função `listar_eventos()`
