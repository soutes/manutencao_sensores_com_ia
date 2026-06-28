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
    eid = result.get("id_salvo", result.get("event_id", "?"))
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


# ─── guardrails ──────────────────────────────────────────────────────────────

_INJECTION_PATTERNS = [
    "ignore previous", "ignore as instruções", "esquece tudo", "esqueça tudo",
    "system:", "you are now", "act as", "pretend you", "novo prompt",
    "ignore o sistema", "ignore seu contexto", "instrução anterior",
]

_MAINTENANCE_KEYWORDS = [
    # ── defeitos canônicos e variações ───────────────────────────────────────
    "rolamento", "desalinhado", "desalinhamento", "desbalanceado", "desbalanceamento",
    "correia", "polia", "cocked_rotor", "cocked rotor", "eccentric_rotor",
    "eccentric rotor", "ventoinha", "falta_fase", "falta fase",
    "rolamento_inner", "rolamento_outer", "rolamento_ball", "rolamento_combination",
    "inner race", "outer race", "ball fault",

    # ── equipamentos e partes mecânicas ──────────────────────────────────────
    "motor", "moto",           # moto = abrev. coloquial de motor
    "maquina", "máquina", "maquinas", "máquinas",
    "equipamento", "equipamentos", "equip",
    "rotor", "estator", "eixo", "eixos", "flange",
    "mancal", "bucha", "anel", "vedação", "vedacao", "gaxeta", "retentor",
    "acoplamento", "engrenagem", "redutor", "caixa de redução", "caixa reducao",
    "bomba", "compressor", "ventilador", "turbina", "exaustor",
    "correia transportadora", "polias", "pinhão", "pinhao", "cremalheira",
    "carcaça", "carcaca", "tampa", "parafuso", "chaveta", "pino",
    "lubrificação", "lubrificacao", "lubrificante", "graxa", "óleo", "oleo",

    # ── instalação e local ────────────────────────────────────────────────────
    "fábrica", "fabrica", "fab",
    "parque", "planta", "instalação", "instalacao",
    "chao de fabrica", "chão de fábrica",
    "linha de producao", "linha de produção",
    "setor", "linha", "célula", "celula", "posto",

    # ── sensores e sinais ────────────────────────────────────────────────────
    "sensor", "sensores",
    "acelerômetro", "acelerometro",
    "vibração", "vibracao", "vibrando", "vibra",
    "rpm", "rotação", "rotacao", "velocidade angular",
    "temperatura", "temp", "calor", "aquecimento", "superaquecimento",
    "frequência", "frequencia", "hz", "hertz",
    "aceleração", "aceleracao",
    "amplitude", "espectro", "harmônica", "harmonica",
    "rms", "kurtosis", "crest", "peak", "pico",
    "mm/s", "in/s", "g ", "g_",
    "sinal", "leitura", "medição", "medicao", "aquisição", "aquisicao",
    "dado", "dados", "telemetria", "iot", "iiot",

    # ── sintomas e anomalias ─────────────────────────────────────────────────
    "falha", "defeito", "anomalia", "irregularidade",
    "ruído", "ruido", "barulho", "trincado", "trinca", "rachadura",
    "folga", "desgaste", "desgastado", "erosão", "erosao",
    "quebrado", "quebrou", "quebra", "travado", "travou",
    "esquentando", "esquentou", "quente", "frio demais",
    "oscilando", "instável", "instavel", "pulsação", "pulsacao",
    "desligou", "parou", "parada", "trip", "desarme",

    # ── manutenção e ações ───────────────────────────────────────────────────
    "manutenção", "manutencao", "manut",
    "preventiva", "preditiva", "prescritiva", "corretiva",
    "inspeção", "inspecao", "inspecionar",
    "revisão", "revisao", "revisar",
    "troca", "trocar", "substituição", "substituicao", "substituir",
    "reparo", "reparar", "consertar",
    "alinhamento", "alinhar", "balanceamento", "balancear",
    "apertar", "afrouxar", "ajuste", "calibração", "calibracao",
    "corrigir", "correção", "correcao",
    "limpar", "limpeza",

    # ── gestão e status ──────────────────────────────────────────────────────
    "status", "semáforo", "semaforo",
    "crítico", "critico", "urgente", "emergência", "emergencia",
    "atenção", "atencao", "alerta", "aviso",
    "pendência", "pendencia", "pendente", "em aberto", "aberto",
    "resolvido", "em andamento",
    "ocorrência", "ocorrencia", "evento", "registro",
    "histórico", "historico",
    "frequência de falha", "frequencia de falha",
    "downtime", "parada não programada", "parada nao programada",

    # ── documentação e prescrição ────────────────────────────────────────────
    "procedimento", "manual", "documento", "doc",
    "prescrição", "prescricao", "diagnóstico", "diagnostico",
    "instrução", "instrucao", "recomendação", "recomendacao",
    "relatório", "relatorio", "análise", "analise",
]


def _is_injection(texto: str) -> bool:
    t = texto.lower()
    return any(p in t for p in _INJECTION_PATTERNS)


def _is_relevant(texto: str) -> bool:
    """Verifica se a mensagem é relacionada ao domínio de manutenção industrial."""
    t = texto.lower()
    return any(k in t for k in _MAINTENANCE_KEYWORDS)


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

    # ── Arquivo JSON anexado ─────────────────────────────────────────────────
    if update.message.document:
        try:
            file = await context.bot.get_file(update.message.document)
            file_bytes = await file.download_as_bytearray()
            text = file_bytes.decode("utf-8").strip()
        except Exception as e:
            await update.message.reply_text(f"⚠️ Erro ao ler arquivo: {e}")
            return
    else:
        text = (update.message.text or "").strip()
        if not text:
            return

    # ── guardrail 1: prompt injection ────────────────────────────────────────
    if _is_injection(text):
        await update.message.reply_text(
            "⛔ Mensagem bloqueada. Este bot responde apenas sobre "
            "manutenção industrial e eventos de sensor."
        )
        return

    try:
        if _is_json_event(text):
            event = json.loads(text)
            result = responder_evento(event, origem="telegram_chat")
            await update.message.reply_text(
                format_event_report(result), parse_mode="Markdown"
            )
        else:
            # ── guardrail 2: fora do domínio ─────────────────────────────────
            if not _is_relevant(text):
                await update.message.reply_text(
                    "🔧 Sou um assistente de *manutenção industrial*.\n\n"
                    "Posso ajudar com:\n"
                    "  • Diagnóstico de eventos de sensor (cole o JSON)\n"
                    "  • Status do parque e defeitos críticos\n"
                    "  • Procedimentos de correção por defeito\n"
                    "  • Pendências sem documentação\n\n"
                    "Sua pergunta não parece relacionada a este domínio.",
                    parse_mode="Markdown",
                )
                return
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
