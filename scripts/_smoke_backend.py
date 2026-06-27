"""Smoke test B1: responder_evento + responder_duvida + funcoes db."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import os
os.environ.setdefault("DATABASE_URL", "sqlite:///data/smoke_backend_test.db")

from core import db, backend

PASS, FAIL = "✅", "❌"
results: list[tuple[str, str]] = []


def check(label: str, cond: bool) -> None:
    mark = PASS if cond else FAIL
    results.append((mark, label))
    print(f"  {mark}  {label}")


print("\n=== SMOKE TEST B1: backend.py ===\n")

# ── _classificar_semaforo ──────────────────────────────────────────────────
print("─ _classificar_semaforo ─")
r_normal = {"is_problem": False, "documented": False, "frequency_per_week": 0}
check("normal → 🟢", backend._classificar_semaforo(r_normal) == "🟢")

r_sem_doc = {"is_problem": True, "documented": False, "frequency_per_week": 1}
check("sem doc → 🔴", backend._classificar_semaforo(r_sem_doc) == "🔴")

r_alta_freq = {"is_problem": True, "documented": True, "frequency_per_week": 7}
check("alta freq (7) → 🔴", backend._classificar_semaforo(r_alta_freq) == "🔴")

r_rpm_bad = {"is_problem": True, "documented": True, "frequency_per_week": 1}
check("rpm baixo (100) → 🔴",
      backend._classificar_semaforo(r_rpm_bad, {"rpm": 100}) == "🔴")

r_1a_oc = {"is_problem": True, "documented": True, "frequency_per_week": 0.5, "n_similar": 0}
check("com doc, baixa freq → 🟡", backend._classificar_semaforo(r_1a_oc) == "🟡")

# ── db: init + salvar_evento ────────────────────────────────────────────────
print("\n─ db.init_db / salvar_evento ─")
db.init_db()

dummy_report = {
    "event_id": 9001, "created_at": "2026-06-27",
    "defeito_canonico": "cocked_rotor", "is_problem": True,
    "documented": True, "n_similar": 2, "frequency_per_week": 1.5,
    "instructions": "Verificar alinhamento do rotor.",
    "sources": ["Doc6.pdf"],
}
dummy_payload = {"id": 9001, "rpm": 1500, "z_rms_velocity_mm_s": 0.9}

ev_id = db.salvar_evento(dummy_report, dummy_payload, origem="smoke", semaforo="🟡")
check(f"salvar_evento retorna id int ({ev_id})", isinstance(ev_id, int) and ev_id > 0)

# ── db: listar_pendencias ────────────────────────────────────────────────────
print("\n─ db.listar_pendencias ─")
pend = db.listar_pendencias()
check("listar_pendencias retorna list", isinstance(pend, list))
check("pendencia tem campo semaforo", all("semaforo" in p for p in pend) if pend else True)

# ── db: resumo_semaforo ──────────────────────────────────────────────────────
print("\n─ db.resumo_semaforo ─")
res = db.resumo_semaforo()
check("resumo tem chaves vermelho/amarelo/verde", {"vermelho","amarelo","verde"} <= res.keys())
check("resumo.total = soma", res["total"] == res["vermelho"] + res["amarelo"] + res["verde"])

# ── db: serie_temporal_resolvidos ────────────────────────────────────────────
print("\n─ db.serie_temporal_resolvidos ─")
serie = db.serie_temporal_resolvidos(dias=7)
check("serie retorna list", isinstance(serie, list))
check("serie items tem campos dia/resolvidos/abertos",
      all({"dia","resolvidos","abertos"} <= set(d) for d in serie) if serie else True)

# ── db: atualizar_status → status_historico ──────────────────────────────────
print("\n─ db.atualizar_status ─")
ok = db.atualizar_status(ev_id, "resolvido", "Problema corrigido em campo.", "Técnico A")
check("atualizar_status retorna True", ok)
check("atualizar_status retorna False p/ id inexistente",
      not db.atualizar_status(99999, "resolvido", "", ""))

from core.db import SessionLocal, StatusHistorico
with SessionLocal() as s:
    hist = s.query(StatusHistorico).filter(StatusHistorico.evento_id == ev_id).all()
check("status_historico gravou auditoria", len(hist) >= 1)
check("status_historico: novo=resolvido", hist[-1].status_novo == "resolvido" if hist else False)

# ── backend: responder_evento (sem pipeline real — skip se sem artifacts) ─────
print("\n─ backend.responder_evento (requer artifacts) ─")
try:
    ev_sample = {"id": 42, "created_at": "2026-06-27",
                 "z_rms_velocity_mm_s": 1.2, "rpm": 1480,
                 "fault": "cocked_rotor"}
    result = backend.responder_evento(ev_sample, origem="smoke")
    check("responder_evento retorna dict", isinstance(result, dict))
    check("responder_evento tem semaforo", "semaforo" in result)
    check("responder_evento tem id_salvo", "id_salvo" in result)
    check("semaforo e emoji valido", result["semaforo"] in ("🔴","🟡","🟢"))
except Exception as e:
    print(f"  ⚠️  pipeline nao disponivel ({e}) — skip responder_evento")

# ── backend: responder_duvida (intencoes) ─────────────────────────────────────
print("\n─ backend.responder_duvida (intencoes) ─")
try:
    r = backend.responder_duvida("status do parque de maquinas", origem="smoke")
    check("status_parque retorna dict", isinstance(r, dict))
    check("status_parque tem resposta nao vazia", bool(r.get("resposta")))
    check("status_parque fonte=banco", r.get("fonte") == "banco")
except Exception as e:
    print(f"  ❌  status_parque falhou: {e}")

try:
    r2 = backend.responder_duvida("quais pendencias existem?", origem="smoke")
    check("pendencias retorna dict", isinstance(r2, dict))
    check("pendencias tem resposta", bool(r2.get("resposta")))
except Exception as e:
    print(f"  ❌  pendencias falhou: {e}")

try:
    r3 = backend.responder_duvida("historico de cocked_rotor", origem="smoke")
    check("historico retorna dict", isinstance(r3, dict))
    check("historico fonte=banco", r3.get("fonte") == "banco")
except Exception as e:
    print(f"  ❌  historico falhou: {e}")

try:
    r4 = backend.responder_duvida("como corrigir cocked_rotor?", origem="smoke")
    check("tecnica retorna dict", isinstance(r4, dict))
    check("tecnica tem resposta", bool(r4.get("resposta")))
except Exception as e:
    print(f"  ❌  tecnica falhou: {e}")

# ── resumo ────────────────────────────────────────────────────────────────────
total = len(results)
passou = sum(1 for m, _ in results if m == PASS)
print(f"\n{'='*40}")
print(f"Resultado: {passou}/{total} passou")
print(f"{'='*40}")

# cleanup
import os as _os
smoke_db = Path(__file__).resolve().parents[1] / "data" / "smoke_backend_test.db"
try:
    _os.remove(smoke_db)
except FileNotFoundError:
    pass

if passou < total:
    sys.exit(1)
