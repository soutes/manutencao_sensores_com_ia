# US-001 — Ingestão de Evento JSON via Telegram

**MoSCoW:** Must
**Persona:** Operador de Campo

---

## User Story

> Como **Operador de Campo**, quero **enviar um JSON de evento de sensor pelo Telegram**,
> para **receber imediatamente a análise do defeito provável, o procedimento de correção
> e a classificação de prioridade (semáforo)** sem precisar acessar nenhum sistema especial.

---

## Critérios de Aceite

**Given** que o operador envia JSON com as 23 features de vibração e `rpm`,

**When** o bot processa,

**Then** a resposta contém:
- Defeito mais provável + confiança KNN (%)
- Frequência histórica do defeito (N ocorrências, % do total)
- Prescrição de correção (baseada no manual via RAG)
- **`status_manutencao`** com semáforo de prioridade:
  - 🔴 **Crítico** — defeito com manual, sem resolução registrada, ocorrência frequente ou rpm fora do padrão
  - 🟡 **Atenção** — defeito identificado, aberto, monitoramento necessário
  - 🟢 **Normal** — estado operacional sem defeito ativo
- O evento, prescrição e `status_manutencao` inicial são gravados no banco

**Given** que o defeito não tem manual,

**When** o pipeline processa,

**Then**:
- Gating ativado: nenhuma prescrição gerada
- `status_manutencao = 🔴 Crítico` (sem procedimento = máximo risco)
- Pendência registrada no banco

**Given** que o JSON é inválido ou incompleto,

**When** o bot tenta processar,

**Then** retorna erro descritivo com os campos ausentes, sem travar.

---

## Campos do JSON de Resposta

```json
{
  "evento_id": "uuid",
  "defeito": "desbalanceado",
  "confianca_pct": 87.3,
  "casos_similares": 5,
  "freq_historica_pct": 12.4,
  "prescricao": "Verificar massa de balanceamento...",
  "fonte_manual": "Doc3 — Procedimento de Balanceamento",
  "status_manutencao": "🟡 Atenção",
  "tem_manual": true,
  "timestamp": "2026-06-26T14:32:00"
}
```

---

## Arquivos Envolvidos

- `src/bot/telegram_bot.py` — handler JSON
- `src/core/backend.py` — `responder_evento(json)` → inclui lógica semáforo
- `src/core/pipeline.py` — orquestração + classificação semáforo
- `src/core/db.py` — grava evento com `status_manutencao`
