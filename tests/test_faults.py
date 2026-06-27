"""Testa normalize_fault: typos, variantes de 17 canônicos e estados (0 desconhecidos)."""
import pytest
from core.faults import normalize_fault, FAULT_DOC_MAP, STATES


# ─── Defeitos canônicos ────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    # cocked_rotor — typo do dataset
    ("cocked_rotor_2",           "cocked_rotor"),
    ("cockecocked_adxl_0",       "cocked_rotor"),
    # desbalanceado — vários typos documentados
    ("desbalanceado_carga",      "desbalanceado"),
    ("ddesbalanceado",           "desbalanceado"),
    ("desbanlanceado",           "desbalanceado"),
    ("desabalanceado",           "desbalanceado"),
    # rolamento — subfamílias
    ("rolamento_inner_2",        "rolamento_inner"),
    ("rolamento_outer_novo",     "rolamento_outer"),
    ("rolamento_ball_0",         "rolamento_ball"),
    ("new_rolamento_inner_0",    "rolamento_inner"),
    ("rolamento_carga",          "rolamento"),
    # outros defeitos
    ("desalinhado_carga",        "desalinhado"),
    ("new_desalinhado",          "desalinhado"),
    ("correia_pos_2",            "correia"),
    ("polia_adxl_0",             "polia"),
    # SEM doc
    ("eccentric_rotor_adxl_0",   "eccentric_rotor"),
    ("ventoinha_0",              "ventoinha"),
    ("falta_fase",               "falta_fase"),
    ("new_falta_fase",           "falta_fase"),
])
def test_canonical_defeitos(raw, expected):
    fi = normalize_fault(raw)
    assert fi.canonical == expected, f"{raw!r} → {fi.canonical!r} (esperado {expected!r})"
    assert fi.is_problem is True


# ─── Estados operacionais (is_problem=False) ──────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("normal_carga",             "normal"),
    ("normla_carga",             "normal"),        # typo normla
    ("baseline_adxl_0",         "baseline"),
    ("teste_0",                  "teste"),
    ("new_teste",                "teste"),
    ("acelerando_0",             "acelerando"),
    ("motor_desligado_novo",     "motor_desligado"),
    ("mortor_desligado",         "motor_desligado"),  # typo mortor
])
def test_estados_nao_sao_problemas(raw, expected):
    fi = normalize_fault(raw)
    assert fi.canonical == expected, f"{raw!r} → {fi.canonical!r}"
    assert fi.is_problem is False
    assert fi.documented is False


# ─── Campos is_problem e documented ──────────────────────────────────────────

def test_cocked_rotor_tem_doc():
    fi = normalize_fault("cocked_rotor")
    assert fi.is_problem is True
    assert fi.documented is True
    assert fi.doc == "Doc6.pdf"


def test_eccentric_rotor_sem_doc():
    fi = normalize_fault("eccentric_rotor")
    assert fi.is_problem is True
    assert fi.documented is False
    assert fi.doc is None


def test_ventoinha_sem_doc():
    fi = normalize_fault("ventoinha")
    assert fi.is_problem is True
    assert fi.documented is False


def test_normal_nao_problema():
    fi = normalize_fault("normal")
    assert fi.is_problem is False


# ─── Zero desconhecidos para todos os 17 canônicos esperados ─────────────────

@pytest.mark.parametrize("raw", [
    "cocked_rotor", "eccentric_rotor", "ventoinha", "falta_fase",
    "rolamento", "rolamento_inner", "rolamento_outer", "rolamento_ball",
    "rolamento_combination", "desalinhado", "desbalanceado", "correia", "polia",
    "normal", "baseline", "teste", "acelerando", "motor_desligado",
])
def test_nao_desconhecido(raw):
    fi = normalize_fault(raw)
    assert fi.canonical != "desconhecido", f"{raw!r} → 'desconhecido'"


# ─── FAULT_DOC_MAP cobre exatamente os defeitos esperados ────────────────────

def test_fault_doc_map_tem_seis_documentados():
    """6 defeitos devem ter manual (Doc1..Doc6)."""
    documentados = [k for k, v in FAULT_DOC_MAP.items() if v is not None]
    assert len(documentados) == 6, f"Esperado 6, obtido {len(documentados)}: {documentados}"


def test_fault_doc_map_tem_tres_sem_doc():
    """3 defeitos sem manual: eccentric_rotor, ventoinha, falta_fase."""
    sem_doc = [k for k, v in FAULT_DOC_MAP.items() if v is None]
    assert set(sem_doc) == {"eccentric_rotor", "ventoinha", "falta_fase"}
