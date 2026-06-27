"""Testa backend.py: deteccao de intencao, semaforo e responder_* com mocks."""
import pytest
from unittest.mock import patch, MagicMock
from core.backend import (
    _classificar_semaforo,
    _detectar_intencao,
    _extrair_defeito_texto,
    responder_evento,
    responder_duvida,
)
from core.similarity import SimilarityResult


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


# ─── _detectar_intencao ────────────────────────────────────────────────────

@pytest.mark.parametrize("texto,esperado", [
    ("qual o status do parque?",       "status_parque"),
    ("pontos criticos agora",          "status_parque"),
    ("situacao das maquinas",          "status_parque"),
    ("quais as pendencias abertas?",   "pendencias"),
    ("listar pendentes",               "pendencias"),
    ("historico de cocked_rotor",      "historico"),
    ("quantas vezes esse defeito?",    "historico"),
    ("como corrigir rolamento_inner?", "tecnica"),
    ("procedimento para desalinhado",  "tecnica"),
])
def test_detectar_intencao(texto, esperado):
    assert _detectar_intencao(texto) == esperado


# ─── _extrair_defeito_texto ────────────────────────────────────────────────

def test_extrair_defeito_direto():
    assert _extrair_defeito_texto("cocked_rotor") == "cocked_rotor"


def test_extrair_defeito_typo():
    assert _extrair_defeito_texto("ddesbalanceado") == "desbalanceado"


def test_extrair_defeito_desconhecido():
    result = _extrair_defeito_texto("xyz_unknown_gibberish")
    assert isinstance(result, str)


# ─── responder_evento ─────────────────────────────────────────────────────

def _mock_process(fault="cocked_rotor", documented=True, freq=1.5):
    return {
        "event_id": 1, "created_at": "2026-06-27",
        "defeito_canonico": fault, "is_problem": True,
        "documented": documented, "n_similar": 10,
        "frequency_per_week": freq, "instructions": "instr",
        "sources": ["Doc6.pdf"] if documented else [],
    }


@patch("core.db.salvar_evento", return_value=42)
@patch("core.pipeline.process_event")
def test_responder_evento_campos_obrigatorios(mock_pe, mock_db):
    mock_pe.return_value = _mock_process()
    result = responder_evento(BASE_EVENT)
    assert "semaforo" in result
    assert "id_salvo" in result
    assert result["id_salvo"] == 42


@patch("core.db.salvar_evento", return_value=1)
@patch("core.pipeline.process_event")
def test_responder_evento_sem_doc_semaforo_vermelho(mock_pe, _):
    mock_pe.return_value = _mock_process(fault="eccentric_rotor", documented=False)
    result = responder_evento(BASE_EVENT)
    assert result["semaforo"] == "🔴"


@patch("core.db.salvar_evento", return_value=1)
@patch("core.pipeline.process_event")
def test_responder_evento_rpm_anormal_vermelho(mock_pe, _):
    mock_pe.return_value = _mock_process(documented=True, freq=1.0)
    result = responder_evento(dict(BASE_EVENT, rpm=100), origem="api")
    assert result["semaforo"] == "🔴"


# ─── responder_duvida ─────────────────────────────────────────────────────

def _mock_resumo():
    return {"vermelho": 2, "amarelo": 1, "verde": 5, "total": 8,
            "abertos": [{"id": 1, "event_id": 1, "defeito": "cocked_rotor",
                         "semaforo": "🔴", "frequency_per_week": 3.0, "documented": True,
                         "ts": "2026-06-27T00:00:00+00:00"}]}


@patch("core.db.salvar_consulta", return_value=None)
@patch("core.db.resumo_semaforo")
def test_responder_duvida_status_parque(mock_resumo, _):
    mock_resumo.return_value = _mock_resumo()
    result = responder_duvida("qual o status do parque?")
    assert "resposta" in result
    assert "fonte" in result
    assert result["fonte"] == "banco"
    assert "🔴" in result["resposta"] or "tico" in result["resposta"]


@patch("core.db.salvar_consulta", return_value=None)
@patch("core.db.listar_pendencias")
def test_responder_duvida_pendencias(mock_pend, _):
    mock_pend.return_value = [
        {"id": 1, "defeito": "cocked_rotor", "semaforo": "🔴",
         "frequency_per_week": 2.0, "documented": True}
    ]
    result = responder_duvida("quais as pendencias?")
    assert result["fonte"] == "banco"
    assert "pendencia" in result["resposta"].lower() or "📋" in result["resposta"]


@patch("core.db.salvar_consulta", return_value=None)
@patch("core.db.historico_defeito")
def test_responder_duvida_historico(mock_hist, _):
    mock_hist.return_value = [
        {"id": 1, "event_id": 1, "status": "pendente", "semaforo": "🔴",
         "documented": True, "ts": "2026-06-27T00:00:00+00:00"}
    ]
    result = responder_duvida("historico de cocked_rotor")
    assert result["fonte"] == "banco"


@patch("core.db.salvar_consulta", return_value=None)
@patch("core.rag.prescribe")
def test_responder_duvida_tecnica(mock_presc, _):
    mock_presc.return_value = MagicMock(
        instructions="Inspecione os mancais.",
        sources=["Doc6.pdf"],
        documented=True,
        canonical_fault="cocked_rotor",
    )
    result = responder_duvida("como corrigir cocked_rotor?")
    assert result["fonte"] == "RAG"
    assert "mancais" in result["resposta"].lower() or "Doc6" in result["resposta"]
