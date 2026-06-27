"""Bot Telegram — multi-persona: JSON de sensor → semáforo, texto → Q&A banco+RAG.

Modos:
  1. push_report(event): evento externo → backend.responder_evento → alerta proativo.
  2. Handler chat: JSON colado → responder_evento; texto livre → responder_duvida.

Contrato de saída visual:
  🔴 crítico  — sem doc OU freq>5 OU rpm fora de faixa
  🟡 atenção  — documentado, baixa freq
  🟢 normal   — não é defeito
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import os

from core.config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

# IDs de usuários autorizados (chat privado).
# Em grupos, qualquer membro pode interagir — o controle é pela adição ao grupo.
_raw = os.getenv("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS: set[int] = {int(x.strip()) for x in _raw.split(",") if x.strip().lstrip("-").isdigit()}


def _autorizado(update) -> bool:
    """Privado: só ALLOWED_USER_IDS. Grupo/supergrupo: todos os membros."""
    chat_type = update.effective_chat.type if update.effective_chat else "private"
    if chat_type in ("group", "supergroup"):
        return True
    if not ALLOWED_USER_IDS:
        return True  # sem whitelist configurada → aberto (desenvolvimento)
    return (update.effective_user.id in ALLOWED_USER_IDS) if update.effective_user else False


# ─── formatadores ────────────────────────────────────────────────────────────

def _semaforo_titulo(semaforo: str) -> str:
    return {
        "🔴": "🔴 CRÍTICO",
        "🟡": "🟡 ATENÇÃO",
        "🟢": "🟢 NORMAL",
    }.get(semaforo, semaforo)


def format_event_report(result: dict) -> str:
    """Formata resultado de responder_evento() em mensagem Markdown."""
    semaforo = result.get("semaforo", "🟢")
    defeito = result.get("defeito_canonico", "?")
    eid = result.get("event_id", "?")
    quando = result.get("created_at", "")
    titulo = _semaforo_titulo(semaforo)

    if not result.get("is_problem", False):
        return (
            f"{semaforo} *Evento {eid}* — {quando}\n\n"
            f"Estado operacional: *{defeito}* (não é defeito).\n"
            f"Nenhuma ação necessária."
        )

    linhas = [
        f"{titulo} — *Evento {eid}* — {quando}",
        "",
        f"⚙️ Defeito: *{defeito}*",
        f"📊 Ocorrências similares: *{result.get('n_similar', 0)}*",
        f"📈 Frequência: ~{result.get('frequency_per_week', 0):.1f}/semana",
    ]
    if result.get("last_occurrence"):
        linhas.append(f"🕐 Última ocorrência: {result['last_occurrence']}")
    linhas.append("")

    if result.get("documented"):
        linhas.append("🛠️ *Ação recomendada:*")
        linhas.append(result.get("instructions", ""))
        fontes = result.get("sources") or []
        if fontes:
            linhas.append(f"\n📄 Fonte: {', '.join(fontes)}")
    else:
        linhas.append("❌ *Sem procedimento documentado.*")
        linhas.append("👉 Registre um novo documento para este defeito.")

    if result.get("id_salvo"):
        linhas.append(f"\n💾 Gravado como evento #{result['id_salvo']}")

    return "\n".join(linhas)


def format_duvida_response(result: dict) -> str:
    """Formata resultado de responder_duvida() em mensagem Markdown."""
    resposta = result.get("resposta", "Sem resposta.")
    fonte = result.get("fonte", "")
    sufixo = f"\n\n_Fonte: {fonte}_" if fonte else ""
    return f"{resposta}{sufixo}"


def _is_json_event(text: str) -> bool:
    """True se texto parece JSON de evento de sensor."""
    stripped = text.strip()
    if not stripped.startswith("{"):
        return False
    try:
        json.loads(stripped)
        return True
    except json.JSONDecodeError:
        return False


# ─── push proativo ───────────────────────────────────────────────────────────

def push_report(event: dict, chat_id: str | None = None) -> None:
    """Processa evento externo e empurra report para o Telegram."""
    from core.backend import responder_evento
    from telegram import Bot

    result = responder_evento(event, origem="telegram_push")
    bot = Bot(token=TELEGRAM_TOKEN)
    bot.send_message(
        chat_id=chat_id or TELEGRAM_CHAT_ID,
        text=format_event_report(result),
        parse_mode="Markdown",
    )


# ─── handlers de chat ────────────────────────────────────────────────────────

async def _start(update, context):
    if not _autorizado(update):
        return
    await update.message.reply_text(
        "🤖 *Bot de Manutenção Prescritiva — SENAI SC*\n\n"
        "Cole o *JSON de um evento* para diagnóstico e semáforo, "
        "ou faça uma *pergunta livre* sobre defeitos, pendências ou status do parque.\n\n"
        "Exemplos:\n"
        "  • `{\"rpm\": 1750, \"z_kurtosis\": 3.2}`\n"
        "  • `Quais são os pontos críticos do parque?`\n"
        "  • `Como corrigir cocked_rotor?`\n\n"
        "Use /myid para ver seu ID de usuário.",
        parse_mode="Markdown",
    )


async def _myid(update, context):
    """Retorna user_id e chat_id — útil para configurar ALLOWED_USER_IDS."""
    uid = update.effective_user.id if update.effective_user else "?"
    cid = update.effective_chat.id if update.effective_chat else "?"
    chat_type = update.effective_chat.type if update.effective_chat else "?"
    await update.message.reply_text(
        f"👤 Seu user\\_id: `{uid}`\n"
        f"💬 Chat id: `{cid}`\n"
        f"Tipo: {chat_type}\n\n"
        f"Adicione seu user\\_id em `ALLOWED_USER_IDS` no `.env` para restringir acesso.",
        parse_mode="Markdown",
    )


async def _handle(update, context):
    from core.backend import responder_evento, responder_duvida

    if not _autorizado(update):
        return  # ignora silenciosamente — não revela que o bot existe

    text = (update.message.text or "").strip()
    if not text:
        return

    try:
        if _is_json_event(text):
            event = json.loads(text)
            result = responder_evento(event, origem="telegram_chat")
            await update.message.reply_text(
                format_event_report(result), parse_mode="Markdown"
            )
        else:
            result = responder_duvida(text, origem="telegram_chat")
            await update.message.reply_text(
                format_duvida_response(result), parse_mode="Markdown"
            )
    except Exception as e:  # noqa: BLE001
        await update.message.reply_text(f"⚠️ Erro ao processar: {e}")


# ─── entrypoint ──────────────────────────────────────────────────────────────

def main() -> None:
    if not TELEGRAM_TOKEN:
        raise SystemExit("Defina TELEGRAM_TOKEN no ambiente.")
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", _start))
    app.add_handler(CommandHandler("myid", _myid))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle))
    print("Bot Telegram rodando...")
    app.run_polling()


if __name__ == "__main__":
    main()
