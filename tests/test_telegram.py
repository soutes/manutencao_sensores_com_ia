"""Testa formatadores e helpers do bot Telegram (sem conexao real)."""
import pytest
import json
from bot.telegram_bot import (
    format_event_report,
    format_duvida_response,
    _is_json_event,
    _semaforo_titulo,
)


# ─── _semaforo_titulo ─────────────────────────────────────────────────────────

def test_titulo_vermelho():
    assert "CRITICO" in _semaforo_titulo("🔴").upper() or "🔴" in _semaforo_titulo("🔴")


def test_titulo_amarelo():
    assert "🟡" in _semaforo_titulo("🟡")


def test_titulo_verde():
    assert "🟢" in _semaforo_titulo("🟢")


def test_titulo_desconhecido():
    assert _semaforo_titulo("X") == "X"


# ─── _is_json_event ───────────────────────────────────────────────────────────

def test_is_json_event_verdadeiro():
    txt = json.dumps({"fault_type": "cocked_rotor", "rpm": 1000})
    assert _is_json_event(txt) is True


def test_is_json_event_texto_livre():
    assert _is_json_event("qual o status do parque?") is False


def test_is_json_event_json_invalido():
    assert _is_json_event("{invalido: json}") is False


def test_is_json_event_vazio():
    assert _is_json_event("") is False


def test_is_json_event_json_sem_chaves():
    assert _is_json_event("[1,2,3]") is False


# ─── format_event_report ─────────────────────────────────────────────────────

RESULT_DEFEITO = {
    "semaforo": "🔴",
    "event_id": 42,
    "created_at": "2026-06-27",
    "defeito_canonico": "cocked_rotor",
    "is_problem": True,
    "documented": True,
    "n_similar": 8,
    "frequency_per_week": 2.0,
    "last_occurrence": "2026-06-20T12:00:00+00:00",
    "instructions": "Inspecione os mancais e substitua o rotor.",
    "sources": ["Doc6.pdf"],
    "id_salvo": 99,
}

RESULT_NORMAL = {
    "semaforo": "🟢",
    "event_id": 7,
    "created_at": "2026-06-27",
    "defeito_canonico": "normal",
    "is_problem": False,
    "documented": False,
}


def test_format_event_report_contem_semaforo():
    msg = format_event_report(RESULT_DEFEITO)
    assert "🔴" in msg


def test_format_event_report_contem_defeito():
    msg = format_event_report(RESULT_DEFEITO)
    assert "cocked_rotor" in msg


def test_format_event_report_contem_instrucoes():
    msg = format_event_report(RESULT_DEFEITO)
    assert "mancais" in msg.lower() or "rotor" in msg.lower()


def test_format_event_report_normal_nao_acao():
    msg = format_event_report(RESULT_NORMAL)
    assert "🟢" in msg
    assert "normal" in msg.lower() or "nao" in msg.lower() or "não" in msg.lower()


def test_format_event_report_sem_doc_alerta():
    result = {**RESULT_DEFEITO, "documented": False, "sources": [], "semaforo": "🔴"}
    msg = format_event_report(result)
    assert "Sem procedimento" in msg or "sem manual" in msg.lower() \
        or "registre" in msg.lower() or "❌" in msg


def test_format_event_report_id_salvo_presente():
    msg = format_event_report(RESULT_DEFEITO)
    assert "99" in msg or "evento" in msg.lower() or "💾" in msg


# ─── format_duvida_response ──────────────────────────────────────────────────

def test_format_duvida_response_contem_resposta():
    result = {"resposta": "Troque o rolamento.", "fonte": "RAG", "contexto": {}}
    msg = format_duvida_response(result)
    assert "Troque o rolamento" in msg


def test_format_duvida_response_contem_fonte():
    result = {"resposta": "OK.", "fonte": "banco", "contexto": {}}
    msg = format_duvida_response(result)
    assert "banco" in msg


def test_format_duvida_response_sem_fonte():
    result = {"resposta": "OK.", "fonte": "", "contexto": {}}
    msg = format_duvida_response(result)
    assert "OK." in msg
