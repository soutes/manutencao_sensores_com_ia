"""Testa camada de persistencia db.py usando SQLite in-memory via env."""
import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


import importlib
import core.db as db_mod


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch, tmp_path):
    """Banco SQLite isolado por teste."""
    db_file = tmp_path / "test.db"
    url = f"sqlite:///{db_file.as_posix()}"
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(url, connect_args={"check_same_thread": False})
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    monkeypatch.setattr(db_mod, "_engine", engine)
    monkeypatch.setattr(db_mod, "SessionLocal", session_factory)
    db_mod.Base.metadata.create_all(engine)
    yield


def _report(fault="cocked_rotor", is_problem=True, documented=True, freq=1.5):
    return {
        "event_id": 1, "created_at": "2026-06-27",
        "defeito_canonico": fault, "is_problem": is_problem,
        "documented": documented, "n_similar": 5, "frequency_per_week": freq,
        "instructions": "...", "sources": ["Doc6.pdf"],
    }


# ─── salvar_evento ─────────────────────────────────────────────────────────────

def test_salvar_evento_retorna_id():
    rid = db_mod.salvar_evento(_report(), {}, semaforo="🟡")
    assert isinstance(rid, int) and rid >= 1


def test_salvar_evento_problema_status_pendente():
    rid = db_mod.salvar_evento(_report(is_problem=True), {}, semaforo="🔴")
    with db_mod.SessionLocal() as s:
        ev = s.get(db_mod.Evento, rid)
        assert ev.status == "pendente"
        assert ev.semaforo == "🔴"


def test_salvar_evento_normal_status_ok():
    rid = db_mod.salvar_evento(_report(is_problem=False, documented=False), {}, semaforo="🟢")
    with db_mod.SessionLocal() as s:
        ev = s.get(db_mod.Evento, rid)
        assert ev.status == "ok"


# ─── listar_pendencias ────────────────────────────────────────────────────────

def test_listar_pendencias_vazio():
    assert db_mod.listar_pendencias() == []


def test_listar_pendencias_retorna_pendentes():
    db_mod.salvar_evento(_report(is_problem=True), {}, semaforo="🔴")
    db_mod.salvar_evento(_report(fault="correia", is_problem=True), {}, semaforo="🟡")
    pends = db_mod.listar_pendencias()
    assert len(pends) == 2
    assert all(p.get("defeito") for p in pends)


def test_listar_pendencias_nao_inclui_ok():
    db_mod.salvar_evento(_report(is_problem=False), {}, semaforo="🟢")
    assert db_mod.listar_pendencias() == []


# ─── atualizar_status ────────────────────────────────────────────────────────

def test_atualizar_status_retorna_true():
    rid = db_mod.salvar_evento(_report(), {}, semaforo="🔴")
    assert db_mod.atualizar_status(rid, "resolvido", comentario="ok", responsavel="eng") is True


def test_atualizar_status_id_inexistente():
    assert db_mod.atualizar_status(99999, "resolvido") is False


def test_atualizar_status_resolvido_vira_verde():
    rid = db_mod.salvar_evento(_report(), {}, semaforo="🔴")
    db_mod.atualizar_status(rid, "resolvido")
    with db_mod.SessionLocal() as s:
        ev = s.get(db_mod.Evento, rid)
        assert ev.semaforo == "🟢"
        assert ev.status == "resolvido"


def test_atualizar_status_grava_historico():
    rid = db_mod.salvar_evento(_report(), {}, semaforo="🔴")
    db_mod.atualizar_status(rid, "resolvido", comentario="peça trocada")
    with db_mod.SessionLocal() as s:
        hist = s.query(db_mod.StatusHistorico).filter_by(evento_id=rid).first()
        assert hist is not None
        assert hist.status_anterior == "pendente"
        assert hist.status_novo == "resolvido"
        assert hist.comentario == "peça trocada"


# ─── resumo_semaforo ─────────────────────────────────────────────────────────

def test_resumo_semaforo_vazio():
    r = db_mod.resumo_semaforo()
    assert r["vermelho"] == 0 and r["amarelo"] == 0 and r["verde"] == 0


def test_resumo_semaforo_contagens():
    db_mod.salvar_evento(_report(), {}, semaforo="🔴")
    db_mod.salvar_evento(_report(fault="correia"), {}, semaforo="🟡")
    db_mod.salvar_evento(_report(is_problem=False), {}, semaforo="🟢")
    r = db_mod.resumo_semaforo()
    assert r["vermelho"] == 1
    assert r["amarelo"] == 1
    assert r["verde"] == 1
    assert r["total"] == 3


# ─── serie_temporal_resolvidos ────────────────────────────────────────────────

def test_serie_temporal_retorna_lista():
    result = db_mod.serie_temporal_resolvidos(dias=30)
    assert isinstance(result, list)


def test_serie_temporal_campos():
    db_mod.salvar_evento(_report(), {}, semaforo="🔴")
    result = db_mod.serie_temporal_resolvidos(dias=30)
    if result:
        assert "dia" in result[0]
        assert "resolvidos" in result[0]
        assert "abertos" in result[0]


# ─── historico_defeito ────────────────────────────────────────────────────────

def test_historico_defeito_vazio():
    assert db_mod.historico_defeito("cocked_rotor") == []


def test_historico_defeito_retorna_registros():
    db_mod.salvar_evento(_report(), {}, semaforo="🔴")
    db_mod.salvar_evento(_report(), {}, semaforo="🔴")
    hist = db_mod.historico_defeito("cocked_rotor")
    assert len(hist) == 2
    assert all("status" in h for h in hist)


# ─── salvar_consulta ────────────────────────────────────────────────────────

def test_salvar_consulta_nao_levanta():
    db_mod.salvar_consulta("como corrigir rolamento?", "troque o rolamento", defeito="rolamento")
