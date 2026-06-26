"""Camada de persistencia trocavel (SQLAlchemy).

Mesmo codigo roda em SQLite (on-prem/offline) ou Postgres/Supabase (cloud),
decidido por DATABASE_URL. Tabelas:
  - eventos:    cada evento analisado + diagnostico + status (pendente/resolvido)
  - consultas:  log de perguntas/respostas (chat Telegram/Streamlit)

Pendencia = evento com status='pendente' (defeito sem doc ou ainda nao tratado).
"""
from __future__ import annotations
from datetime import datetime, timezone
import json

from sqlalchemy import (create_engine, String, Integer, Float, Boolean, Text,
                        DateTime, func)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class Evento(Base):
    __tablename__ = "eventos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int | None] = mapped_column(Integer, index=True)
    created_at: Mapped[str | None] = mapped_column(String(40))
    defeito: Mapped[str] = mapped_column(String(60), index=True)
    is_problem: Mapped[bool] = mapped_column(Boolean, default=False)
    documented: Mapped[bool] = mapped_column(Boolean, default=False)
    n_similar: Mapped[int] = mapped_column(Integer, default=0)
    frequency_per_week: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="pendente", index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")   # evento bruto
    report_json: Mapped[str] = mapped_column(Text, default="{}")    # report completo
    origem: Mapped[str] = mapped_column(String(20), default="api")  # api|telegram|streamlit
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Consulta(Base):
    __tablename__ = "consultas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pergunta: Mapped[str] = mapped_column(Text)
    resposta: Mapped[str] = mapped_column(Text)
    defeito: Mapped[str | None] = mapped_column(String(60))
    origem: Mapped[str] = mapped_column(String(20), default="api")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


_engine = create_engine(DATABASE_URL, future=True,
                        connect_args={"check_same_thread": False}
                        if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(_engine)


def backend_name() -> str:
    return "SQLite" if DATABASE_URL.startswith("sqlite") else "Postgres/Supabase"


# ---------------- operacoes de alto nivel ----------------
def salvar_evento(report: dict, payload: dict, origem: str = "api") -> int:
    """Grava um evento analisado. Status inicial: pendente se for problema."""
    init_db()
    with SessionLocal() as s:
        ev = Evento(
            event_id=report.get("event_id"),
            created_at=str(report.get("created_at") or ""),
            defeito=report.get("defeito_canonico", "?"),
            is_problem=bool(report.get("is_problem")),
            documented=bool(report.get("documented")),
            n_similar=int(report.get("n_similar", 0)),
            frequency_per_week=float(report.get("frequency_per_week", 0.0)),
            status="pendente" if report.get("is_problem") else "ok",
            payload_json=json.dumps(payload, ensure_ascii=False, default=str),
            report_json=json.dumps(report, ensure_ascii=False, default=str),
            origem=origem,
        )
        s.add(ev); s.commit()
        return ev.id


def salvar_consulta(pergunta: str, resposta: str, defeito: str | None = None,
                    origem: str = "api") -> None:
    init_db()
    with SessionLocal() as s:
        s.add(Consulta(pergunta=pergunta, resposta=resposta, defeito=defeito, origem=origem))
        s.commit()


def listar_pendencias(limit: int = 20) -> list[dict]:
    init_db()
    with SessionLocal() as s:
        rows = (s.query(Evento).filter(Evento.status == "pendente")
                .order_by(Evento.ts.desc()).limit(limit).all())
        return [{"id": r.id, "event_id": r.event_id, "defeito": r.defeito,
                 "documented": r.documented, "n_similar": r.n_similar,
                 "ts": r.ts.isoformat() if r.ts else None} for r in rows]


def historico_defeito(defeito: str, limit: int = 50) -> list[dict]:
    init_db()
    with SessionLocal() as s:
        rows = (s.query(Evento).filter(Evento.defeito == defeito)
                .order_by(Evento.ts.desc()).limit(limit).all())
        return [{"id": r.id, "event_id": r.event_id, "status": r.status,
                 "ts": r.ts.isoformat() if r.ts else None} for r in rows]


def resumo_geral() -> dict:
    init_db()
    with SessionLocal() as s:
        total = s.query(func.count(Evento.id)).scalar() or 0
        pend = s.query(func.count(Evento.id)).filter(Evento.status == "pendente").scalar() or 0
        consultas = s.query(func.count(Consulta.id)).scalar() or 0
        return {"eventos": int(total), "pendencias": int(pend),
                "consultas": int(consultas), "backend": backend_name()}
