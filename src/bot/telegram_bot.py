"""Bot Telegram - report de evento (push) + chat interativo.

Dois modos:
  1. push_report(event): processa evento -> envia report ao TELEGRAM_CHAT_ID.
  2. handlers de chat: /start, JSON colado, ou pergunta livre.

Formato: defeito, nº ocorrencias, frequencia, ultima ocorrencia, acao recomendada
(ou aviso 'registre documento'), fonte. Consome core.pipeline.process_event.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID


def format_report(report: dict) -> str:
    """Formata o dict do process_event em mensagem Telegram (Markdown)."""
    defeito = report.get("defeito_canonico", "?")
    eid = report.get("event_id", "?")
    quando = report.get("created_at", "")

    if not report.get("is_problem", False):
        return (f"✅ *Evento {eid}* — {quando}\n\n"
                f"Estado operacional: *{defeito}* (não é defeito).\n"
                f"Nenhuma ação necessária.")

    linhas = [
        f"🔧 *NOVO EVENTO {eid}* — {quando}",
        "",
        f"⚠️ Defeito: *{defeito}*",
        f"📊 Ocorrências similares: *{report.get('n_similar', 0)}*",
        f"📈 Frequência: ~{report.get('frequency_per_week', 0):.1f}/semana",
    ]
    if report.get("last_occurrence"):
        linhas.append(f"🕐 Última ocorrência: {report['last_occurrence']}")
    linhas.append("")

    if report.get("documented"):
        linhas.append("🛠️ *Ação recomendada:*")
        linhas.append(report.get("instructions", ""))
        fontes = report.get("sources") or []
        if fontes:
            linhas.append(f"\n📄 Fonte: {', '.join(fontes)}")
    else:
        linhas.append("❌ *Sem procedimento documentado.*")
        linhas.append("👉 Registre um novo documento para este defeito.")

    return "\n".join(linhas)


def push_report(event: dict, chat_id: str | None = None) -> None:
    """Processa um evento e empurra o report para o Telegram (modo alerta proativo)."""
    from core.pipeline import process_event  # import tardio (depende de indices)
    from telegram import Bot

    report = process_event(event)
    bot = Bot(token=TELEGRAM_TOKEN)
    bot.send_message(chat_id=chat_id or TELEGRAM_CHAT_ID,
                     text=format_report(report), parse_mode="Markdown")


# ----------------- modo chat interativo -----------------
async def _start(update, context):
    await update.message.reply_text(
        "Bot de Manutenção Prescritiva.\n"
        "Cole o JSON de um evento para receber o report, "
        "ou pergunte sobre um defeito (ex: 'como corrigir cocked_rotor?')."
    )


async def _handle(update, context):
    from core.pipeline import process_event
    from core.rag import prescribe
    text = (update.message.text or "").strip()
    try:
        if text.startswith("{"):
            report = process_event(json.loads(text))
            await update.message.reply_text(format_report(report), parse_mode="Markdown")
        else:
            # heuristica: ultima palavra parecida com defeito canonico
            from core.faults import normalize_fault
            fault = normalize_fault(text).canonical
            res = prescribe(fault, question=text)
            msg = res.instructions
            if res.sources:
                msg += f"\n\n📄 Fonte: {', '.join(res.sources)}"
            await update.message.reply_text(msg)
    except Exception as e:  # noqa: BLE001
        await update.message.reply_text(f"Erro ao processar: {e}")


def main() -> None:
    if not TELEGRAM_TOKEN:
        raise SystemExit("Defina TELEGRAM_TOKEN no ambiente.")
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", _start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle))
    print("Bot Telegram rodando...")
    app.run_polling()


if __name__ == "__main__":
    main()
