"""Camada de persistencia trocavel (SQLAlchemy).

Mesmo codigo roda em SQLite (on-prem/offline) ou Postgres/Supabase (cloud),
decidido por DATABASE_URL. Tabelas:
  - eventos:        cada evento analisado + diagnostico + semaforo + status
  - consultas:      log de perguntas/respostas (chat Telegram/Streamlit)
  - status_historico: auditoria de mudancas de status (quem, quando, de/para)

Pendencia = evento com status='pendente' (defeito sem doc ou ainda nao tratado).
Semaforo:  🔴 critico | 🟡 atencao | 🟢 ok/normal
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
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
    semaforo: Mapped[str] = mapped_column(String(5), default="🟢", index=True)
    status: Mapped[str] = mapped_column(String(20), default="pendente", index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    report_json: Mapped[str] = mapped_column(Text, default="{}")
    origem: Mapped[str] = mapped_column(String(20), default="api")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Consulta(Base):
    __tablename__ = "consultas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pergunta: Mapped[str] = mapped_column(Text)
    resposta: Mapped[str] = mapped_column(Text)
    defeito: Mapped[str | None] = mapped_column(String(60))
    origem: Mapped[str] = mapped_column(String(20), default="api")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StatusHistorico(Base):
    __tablename__ = "status_historico"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evento_id: Mapped[int] = mapped_column(Integer, index=True)
    status_anterior: Mapped[str] = mapped_column(String(20))
    status_novo: Mapped[str] = mapped_column(String(20))
    responsavel: Mapped[str | None] = mapped_column(String(100))
    comentario: Mapped[str | None] = mapped_column(Text)
    data: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


_engine = create_engine(DATABASE_URL, future=True,
                        connect_args={"check_same_thread": False}
                        if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)


def _apply_migrations() -> None:
    """Adiciona colunas novas em DBs existentes (additive only)."""
    from sqlalchemy import inspect, text
    inspector = inspect(_engine)
    if "eventos" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("eventos")}
    with _engine.connect() as conn:
        if "semaforo" not in existing:
            conn.execute(text("ALTER TABLE eventos ADD COLUMN semaforo VARCHAR(5) DEFAULT '🟢'"))
            conn.commit()


def init_db() -> None:
    Base.metadata.create_all(_engine)
    _apply_migrations()


def backend_name() -> str:
    return "SQLite" if DATABASE_URL.startswith("sqlite") else "Postgres/Supabase"


# ---------------- operacoes de alto nivel ----------------

def salvar_evento(report: dict, payload: dict, origem: str = "api",
                  semaforo: str = "🟢") -> int:
    """Grava evento analisado. Status inicial: pendente se for problema."""
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
            semaforo=semaforo,
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
        rows = (s.query(Evento)
                .filter(Evento.status.in_(["pendente", "resolvido"]))
                .order_by(Evento.ts.desc())
                .limit(limit).all())
        return [{"id": r.id, "event_id": r.event_id, "defeito": r.defeito,
                 "documented": r.documented, "n_similar": r.n_similar,
                 "semaforo": r.semaforo, "frequency_per_week": r.frequency_per_week,
                 "status": r.status,
                 "ts": r.ts.isoformat() if r.ts else None} for r in rows]


def buscar_evento(evento_id: int) -> dict | None:
    """Busca um evento por PK e retorna dict com report_json parsed."""
    init_db()
    with SessionLocal() as s:
        r = s.query(Evento).get(evento_id)
        if r is None:
            return None
        import json as _json
        report = _json.loads(r.report_json) if r.report_json else {}
        return {"id": r.id, "event_id": r.event_id, "defeito": r.defeito,
                "is_problem": r.is_problem, "documented": r.documented,
                "n_similar": r.n_similar, "frequency_per_week": r.frequency_per_week,
                "semaforo": r.semaforo, "status": r.status, "origem": r.origem,
                "payload_json": r.payload_json, "report": report,
                "ts": r.ts.isoformat() if r.ts else None}


def listar_eventos(limit: int = 100, status_filter: str | None = None,
                   semaforo_filter: str | None = None,
                   defeito_filter: str | None = None) -> list[dict]:
    """Lista eventos com filtros opcionais. Ordem: 🔴 → 🟡 → 🟢."""
    init_db()
    _ordem = {"🔴": 0, "🟡": 1, "🟢": 2}
    with SessionLocal() as s:
        q = s.query(Evento)
        if status_filter:
            q = q.filter(Evento.status == status_filter)
        if semaforo_filter:
            q = q.filter(Evento.semaforo == semaforo_filter)
        if defeito_filter:
            q = q.filter(Evento.defeito == defeito_filter)
        rows = q.order_by(Evento.ts.desc()).limit(limit).all()
        result = [{"id": r.id, "event_id": r.event_id, "defeito": r.defeito,
                   "is_problem": r.is_problem, "documented": r.documented,
                   "n_similar": r.n_similar, "frequency_per_week": r.frequency_per_week,
                   "semaforo": r.semaforo, "status": r.status, "origem": r.origem,
                   "ts": r.ts.isoformat() if r.ts else None} for r in rows]
        result.sort(key=lambda x: _ordem.get(x["semaforo"], 3))
        return result


def historico_defeito(defeito: str, limit: int = 50) -> list[dict]:
    init_db()
    with SessionLocal() as s:
        rows = (s.query(Evento).filter(Evento.defeito == defeito)
                .order_by(Evento.ts.desc()).limit(limit).all())
        return [{"id": r.id, "event_id": r.event_id, "status": r.status,
                 "semaforo": r.semaforo, "documented": r.documented,
                 "ts": r.ts.isoformat() if r.ts else None} for r in rows]


def resumo_semaforo() -> dict:
    """Contagem por semáforo + listas de eventos críticos/atenção abertos."""
    init_db()
    with SessionLocal() as s:
        def _count(sem: str) -> int:
            return (s.query(func.count(Evento.id))
                    .filter(Evento.semaforo == sem).scalar() or 0)

        vermelho = int(_count("🔴"))
        amarelo = int(_count("🟡"))
        verde = int(_count("🟢"))

        # eventos abertos (pendente) em critico/atencao para lista de pontos
        abertos = (s.query(Evento)
                   .filter(Evento.status == "pendente",
                           Evento.semaforo.in_(["🔴", "🟡"]))
                   .order_by(Evento.frequency_per_week.desc())
                   .limit(10).all())
        lista_abertos = [{"id": r.id, "event_id": r.event_id, "defeito": r.defeito,
                          "semaforo": r.semaforo, "frequency_per_week": r.frequency_per_week,
                          "documented": r.documented,
                          "ts": r.ts.isoformat() if r.ts else None}
                         for r in abertos]

        return {"vermelho": vermelho, "amarelo": amarelo, "verde": verde,
                "total": vermelho + amarelo + verde,
                "abertos": lista_abertos}


def serie_temporal_resolvidos(dias: int = 30) -> list[dict]:
    """Série temporal: eventos resolvidos (🟢/status=ok) por dia nos últimos `dias` dias."""
    init_db()
    from sqlalchemy import text
    cutoff = datetime.now(timezone.utc) - timedelta(days=dias)
    with SessionLocal() as s:
        # SQLite-compatible: DATE(ts)
        if DATABASE_URL.startswith("sqlite"):
            sql = text("""
                SELECT DATE(ts) as dia,
                       SUM(CASE WHEN status IN ('ok','resolvido') THEN 1 ELSE 0 END) as resolvidos,
                       SUM(CASE WHEN status = 'pendente' THEN 1 ELSE 0 END) as abertos
                FROM eventos
                WHERE ts >= :cutoff
                GROUP BY DATE(ts)
                ORDER BY dia
            """)
        else:
            sql = text("""
                SELECT DATE(ts) as dia,
                       SUM(CASE WHEN status IN ('ok','resolvido') THEN 1 ELSE 0 END) as resolvidos,
                       SUM(CASE WHEN status = 'pendente' THEN 1 ELSE 0 END) as abertos
                FROM eventos
                WHERE ts >= :cutoff
                GROUP BY DATE(ts)
                ORDER BY dia
            """)
        rows = s.execute(sql, {"cutoff": cutoff.isoformat()}).fetchall()
        return [{"dia": str(r[0]), "resolvidos": int(r[1] or 0),
                 "abertos": int(r[2] or 0)} for r in rows]


def atualizar_status(evento_id: int, status: str, comentario: str = "",
                     responsavel: str = "") -> bool:
    """Atualiza status de manutenção e grava auditoria em status_historico.

    Retorna True se o evento foi encontrado e atualizado.
    """
    init_db()
    with SessionLocal() as s:
        ev = s.get(Evento, evento_id)
        if ev is None:
            return False
        anterior = ev.status
        ev.status = status
        # se resolvido, atualiza semaforo para verde
        if status in ("ok", "resolvido"):
            ev.semaforo = "🟢"
        hist = StatusHistorico(
            evento_id=evento_id,
            status_anterior=anterior,
            status_novo=status,
            responsavel=responsavel or None,
            comentario=comentario or None,
            data=datetime.now(timezone.utc),
        )
        s.add(hist); s.commit()
        return True


def resumo_geral() -> dict:
    init_db()
    with SessionLocal() as s:
        total = s.query(func.count(Evento.id)).scalar() or 0
        pend = s.query(func.count(Evento.id)).filter(Evento.status == "pendente").scalar() or 0
        consultas = s.query(func.count(Consulta.id)).scalar() or 0
        return {"eventos": int(total), "pendencias": int(pend),
                "consultas": int(consultas), "backend": backend_name()}


def top_defeitos(limit: int = 5) -> list[dict]:
    """Ranking de defeitos mais frequentes (is_problem=True). Usado no Overview."""
    init_db()
    with SessionLocal() as s:
        rows = (
            s.query(Evento.defeito, Evento.documented,
                    func.count(Evento.id).label("cnt"))
            .filter(Evento.is_problem == True)
            .group_by(Evento.defeito, Evento.documented)
            .order_by(func.count(Evento.id).desc())
            .limit(limit)
            .all()
        )
        return [{"defeito": r[0], "documented": bool(r[1]), "count": int(r[2])}
                for r in rows]


def listar_recentes(limit: int = 4) -> list[dict]:
    """Lista eventos mais recentes por timestamp, sem reordenar por semáforo."""
    init_db()
    with SessionLocal() as s:
        rows = (s.query(Evento).order_by(Evento.ts.desc()).limit(limit).all())
        return [{"id": r.id, "defeito": r.defeito, "semaforo": r.semaforo,
                 "status": r.status, "is_problem": r.is_problem,
                 "documented": r.documented,
                 "ts": r.ts.isoformat() if r.ts else None}
                for r in rows]


def listar_eventos_periodo(inicio: str, fim: str) -> list[dict]:
    """Eventos entre inicio e fim inclusive (YYYY-MM-DD). Usado em Relatório IA."""
    init_db()
    with SessionLocal() as s:
        rows = (
            s.query(Evento)
            .filter(Evento.ts >= f"{inicio} 00:00:00",
                    Evento.ts <= f"{fim} 23:59:59")
            .order_by(Evento.ts.desc())
            .all()
        )
        return [{"id": r.id, "defeito": r.defeito, "is_problem": r.is_problem,
                 "documented": r.documented, "semaforo": r.semaforo,
                 "status": r.status, "frequency_per_week": r.frequency_per_week,
                 "ts": r.ts.isoformat() if r.ts else None}
                for r in rows]
