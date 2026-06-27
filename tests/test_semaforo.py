"""Testa logica de classificacao do semaforo (verde/amarelo/vermelho)."""
import pytest
from core.backend import _classificar_semaforo


def _r(is_problem=True, documented=True, freq=1.0):
    return {"is_problem": is_problem, "documented": documented, "frequency_per_week": freq}


def test_verde_estado_normal():
    assert _classificar_semaforo(_r(is_problem=False)) == "🟢"


def test_amarelo_documentado_baixa_freq():
    assert _classificar_semaforo(_r(is_problem=True, documented=True, freq=1.0)) == "🟡"


def test_vermelho_sem_doc():
    assert _classificar_semaforo(_r(is_problem=True, documented=False, freq=0.5)) == "🔴"


def test_vermelho_alta_freq():
    assert _classificar_semaforo(_r(is_problem=True, documented=True, freq=6.0)) == "🔴"


def test_vermelho_freq_exata_limiar():
    assert _classificar_semaforo(_r(is_problem=True, documented=True, freq=5.0)) == "🟡"
    assert _classificar_semaforo(_r(is_problem=True, documented=True, freq=5.1)) == "🔴"


def test_vermelho_rpm_baixo():
    report = _r(is_problem=True, documented=True, freq=1.0)
    event = {"rpm": 200}
    assert _classificar_semaforo(report, event) == "🔴"


def test_vermelho_rpm_alto():
    report = _r(is_problem=True, documented=True, freq=1.0)
    event = {"rpm": 4500}
    assert _classificar_semaforo(report, event) == "🔴"


def test_amarelo_rpm_normal():
    report = _r(is_problem=True, documented=True, freq=1.0)
    event = {"rpm": 1000}
    assert _classificar_semaforo(report, event) == "🟡"


def test_verde_evento_sem_event_arg():
    assert _classificar_semaforo(_r(is_problem=False), None) == "🟢"
