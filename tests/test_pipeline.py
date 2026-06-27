"""Testa process_event end-to-end nos 3 casos chave (com mock do índice KNN)."""
import pytest
from unittest.mock import patch, MagicMock
from core.pipeline import process_event
from core.similarity import SimilarityResult


# ─── Fixtures / helpers ───────────────────────────────────────────────────────

def _mock_index(fault: str, n_similar: int = 12, freq: float = 1.5):
    """Mock de SimilarityIndex que retorna um defeito fixo."""
    idx = MagicMock()
    idx.query.return_value = SimilarityResult(
        canonical_fault=fault,
        n_similar=n_similar,
        neighbor_ids=list(range(min(n_similar, 10))),
        mean_distance=0.45,
        frequency_per_week=freq,
        last_occurrence="2026-06-01T00:00:00+00:00",
    )
    return idx


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


# ─── Caso 1: defeito COM doc ──────────────────────────────────────────────────

@patch("core.pipeline.SimilarityIndex")
def test_cocked_rotor_com_doc(mock_cls):
    """cocked_rotor → is_problem=True, documented=True, Doc6 nas fontes."""
    mock_cls.load.return_value = _mock_index("cocked_rotor")
    r = process_event(dict(BASE_EVENT, id=1))

    assert r["defeito_canonico"] == "cocked_rotor"
    assert r["is_problem"] is True
    assert r["documented"] is True
    assert "Doc6" in " ".join(r.get("sources", []))
    assert isinstance(r["n_similar"], int) and r["n_similar"] > 0


# ─── Caso 2: defeito SEM doc ──────────────────────────────────────────────────

@patch("core.pipeline.SimilarityIndex")
def test_eccentric_rotor_sem_doc(mock_cls):
    """eccentric_rotor → documented=False, sources vazio, instrução pede registro."""
    mock_cls.load.return_value = _mock_index("eccentric_rotor")
    r = process_event(dict(BASE_EVENT, id=2))

    assert r["defeito_canonico"] == "eccentric_rotor"
    assert r["is_problem"] is True
    assert r["documented"] is False
    assert r.get("sources") in ([], None, [])
    assert "registre" in r.get("instructions", "").lower() \
        or "nao ha" in r.get("instructions", "").lower() \
        or "não há" in r.get("instructions", "").lower()


# ─── Caso 3: estado normal ────────────────────────────────────────────────────

@patch("core.pipeline.SimilarityIndex")
def test_estado_normal_nao_problema(mock_cls):
    """normal → is_problem=False, nenhuma ação necessária."""
    mock_cls.load.return_value = _mock_index("normal", n_similar=5000, freq=100.0)
    r = process_event(dict(BASE_EVENT, id=3))

    assert r["defeito_canonico"] == "normal"
    assert r["is_problem"] is False
    assert r.get("documented") is False


# ─── Campos obrigatórios no retorno ──────────────────────────────────────────

@patch("core.pipeline.SimilarityIndex")
def test_campos_obrigatorios_presentes(mock_cls):
    """Retorno deve ter todos os campos do contrato do pipeline."""
    mock_cls.load.return_value = _mock_index("cocked_rotor")
    r = process_event(BASE_EVENT)

    campos = ["event_id", "defeito_canonico", "is_problem", "n_similar",
              "frequency_per_week", "documented", "instructions", "sources"]
    for campo in campos:
        assert campo in r, f"Campo '{campo}' ausente no report"
