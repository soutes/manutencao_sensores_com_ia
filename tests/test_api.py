"""Testa endpoints FastAPI: /health, /event, /chat."""
import pytest
from types import SimpleNamespace
from unittest.mock import patch
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app, raise_server_exceptions=False)


BASE_EVENT = {
    "id": 1, "created_at": "2026-06-27",
    "z_rms_velocity_in_s": 0.06, "z_rms_velocity_mm_s": 1.5,
    "temperature_f": 76.0, "temperature_c": 24.0,
    "x_rms_velocity_in_s": 0.08, "x_rms_velocity_mm_s": 2.0,
    "z_peak_acceleration_g": 0.5, "x_peak_acceleration_g": 0.6,
    "z_peak_vel_comp_freq_hz": 60.0, "x_peak_vel_comp_freq_hz": 60.0,
    "z_rms_acceleration_g": 0.09, "x_rms_acceleration_g": 0.11,
    "z_kurtosis": 2.4, "x_kurtosis": 2.8,
    "z_crest_factor": 3.7, "x_crest_factor": 4.3,
    "z_peak_velocity_in_s": 0.08, "z_peak_velocity_mm_s": 2.1,
    "x_peak_velocity_in_s": 0.11, "x_peak_velocity_mm_s": 2.8,
    "z_high_freq_rms_accel_g": 0.13, "x_high_freq_rms_accel_g": 0.15,
    "rpm": 1000.0,
}

MOCK_REPORT = {
    "event_id": 1, "created_at": "2026-06-27",
    "defeito_canonico": "cocked_rotor", "is_problem": True,
    "documented": True, "n_similar": 10, "frequency_per_week": 1.5,
    "instructions": "Inspecione mancais.", "sources": ["Doc6.pdf"],
    "last_occurrence": None,
}


# ─── /health ──────────────────────────────────────────────────────────────────

def test_health_200():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ─── /event ───────────────────────────────────────────────────────────────────

@patch("api.main.process_event", return_value=MOCK_REPORT)
def test_event_200(mock_pe):
    r = client.post("/event", json=BASE_EVENT)
    assert r.status_code == 200
    data = r.json()
    assert data["defeito_canonico"] == "cocked_rotor"
    assert data["is_problem"] is True


@patch("api.main.process_event", return_value=MOCK_REPORT)
def test_event_campos_obrigatorios(mock_pe):
    r = client.post("/event", json=BASE_EVENT)
    data = r.json()
    for campo in ("defeito_canonico", "is_problem", "documented", "n_similar", "instructions"):
        assert campo in data, f"Campo '{campo}' ausente"


def test_event_payload_vazio_aceita():
    with patch("api.main.process_event", return_value={**MOCK_REPORT, "defeito_canonico": "normal"}):
        r = client.post("/event", json={})
        assert r.status_code == 200


# ─── /chat ────────────────────────────────────────────────────────────────────

def _presc(instructions="sem instrucao", sources=None, documented=False, fault="desconhecido"):
    return SimpleNamespace(
        instructions=instructions,
        sources=sources or [],
        documented=documented,
        canonical_fault=fault,
    )


def test_chat_sem_fault():
    with patch("api.main.prescribe", return_value=_presc()):
        r = client.post("/chat", json={"fault": "", "question": "o que e isso?"})
        assert r.status_code == 200


def test_chat_com_fault_valido():
    with patch("api.main.prescribe",
               return_value=_presc("Troque o rolamento.", ["Doc1.pdf"], True, "rolamento_inner")):
        r = client.post("/chat", json={"fault": "rolamento_inner", "question": "como corrigir?"})
        assert r.status_code == 200
        data = r.json()
        assert "instructions" in data


def test_chat_retorna_dict():
    with patch("api.main.prescribe", return_value=_presc()):
        r = client.post("/chat", json={"fault": "desalinhado"})
        assert r.status_code == 200
