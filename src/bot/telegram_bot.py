"""CONTRATO: bot Telegram - report de evento + chat. >>> AGENTE D preenche TODOs. <<<

Dois modos:
  1. push_report(event): recebe evento -> formata report -> envia ao TELEGRAM_CHAT_ID.
  2. handler de mensagem: operador manda JSON ou pergunta -> responde.

Formato do report: defeito, nº ocorrencias, frequencia, ultima ocorrencia,
acao recomendada (ou aviso 'registre documento'), fonte.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.pipeline import process_event
from core.config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID


def format_report(report: dict) -> str:
    """TODO(Agente D): formatar dict do process_event em texto Telegram (markdown)."""
    raise NotImplementedError


def push_report(event: dict) -> None:
    """TODO(Agente D): process_event -> format_report -> enviar via Bot."""
    raise NotImplementedError


def main() -> None:
    """TODO(Agente D): subir Application com handlers (python-telegram-bot)."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
