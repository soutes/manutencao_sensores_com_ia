"""Seed de demonstração — popula `eventos` com mix realista de semáforo.

Gera ~30 eventos com distribuição ALEATÓRIA entre 🔴 crítico, 🟡 atenção e 🟢 normal,
cada um com payload/freq/rpm/status coerentes com a cor (mesma lógica de
backend._classificar_semaforo). Limpa a tabela antes (a menos que --append).

Uso:
    poetry run python scripts/seed_demo.py            # limpa e recria 30
    poetry run python scripts/seed_demo.py --n 40     # 40 eventos
    poetry run python scripts/seed_demo.py --append   # não apaga existentes
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core import db  # noqa: E402

# ── faixas (espelham backend._classificar_semaforo) ──────────────────────────
RPM_MIN, RPM_MAX = 400, 3800

DOC_FAULTS = [
    "rolamento", "rolamento_inner", "rolamento_outer", "rolamento_ball",
    "rolamento_combination", "desalinhado", "desbalanceado", "correia",
    "polia", "cocked_rotor",
]
NODOC_FAULTS = ["eccentric_rotor", "ventoinha", "falta_fase"]  # sem manual → sempre 🔴
NORMAL_STATES = ["normal", "baseline", "acelerando", "motor_desligado", "teste"]

INSTRUCTIONS = {
    "rolamento": "1. Bloquear e sinalizar (LOTO).\n2. Inspecionar rolamento e medir folga axial/radial.\n3. Substituir por modelo equivalente e lubrificar conforme especificação.\n4. Religar e validar espectro de vibração.",
    "rolamento_inner": "1. Confirmar pico em BPFI no espectro.\n2. Substituir rolamento — pista interna comprometida.\n3. Verificar ajuste do eixo e relubrificar.",
    "rolamento_outer": "1. Confirmar pico em BPFO no espectro.\n2. Substituir rolamento — pista externa comprometida.\n3. Verificar assentamento no alojamento.",
    "rolamento_ball": "1. Confirmar pico em BSF no espectro.\n2. Substituir rolamento — esfera/gaiola comprometida.\n3. Revisar plano de lubrificação.",
    "rolamento_combination": "1. Múltiplas frequências de falha detectadas.\n2. Substituir conjunto de rolamento.\n3. Investigar causa raiz (montagem, lubrificação, carga).",
    "desalinhado": "1. Parar e bloquear o equipamento.\n2. Executar alinhamento a laser eixo motor↔carga.\n3. Ajustar calços e reapertar base. Tolerância conforme manual.",
    "desbalanceado": "1. Medir vibração 1x RPM.\n2. Executar balanceamento dinâmico em campo.\n3. Verificar acúmulo de sujeira/incrustação no rotor.",
    "correia": "1. Inspecionar tensão e estado das correias.\n2. Substituir jogo completo se ressecado/trincado.\n3. Realinhar polias e ajustar tensão.",
    "polia": "1. Verificar alinhamento das polias com régua/laser.\n2. Corrigir desalinhamento angular/paralelo.\n3. Reapertar fixação e revisar chaveta.",
    "cocked_rotor": "1. Confirmar montagem inclinada do rotor.\n2. Reassentar rotor e verificar perpendicularidade.\n3. Revisar acoplamento e refazer alinhamento.",
}

SOURCES = {
    "rolamento": ["Doc1.pdf"], "rolamento_inner": ["Doc1.pdf"], "rolamento_outer": ["Doc1.pdf"],
    "rolamento_ball": ["Doc1.pdf"], "rolamento_combination": ["Doc1.pdf"],
    "desalinhado": ["Doc2.pdf"], "desbalanceado": ["Doc3.pdf"],
    "correia": ["Doc4.pdf"], "polia": ["Doc4.pdf"], "cocked_rotor": ["Doc5.pdf"],
}

ORIGENS = ["api", "streamlit", "telegram_chat", "telegram_push"]


def _payload(rpm: float) -> dict:
    return {
        "rpm": round(rpm),
        "z_rms_velocity_mm_s": round(random.uniform(1.5, 9.5), 2),
        "z_kurtosis": round(random.uniform(2.8, 7.5), 2),
        "temperature_c": round(random.uniform(45, 95), 1),
    }


def _make_event(color: str) -> dict:
    """Monta (report, payload, semaforo, status) coerentes com a cor desejada."""
    if color == "🟢":
        defeito = random.choice(NORMAL_STATES)
        rpm = random.uniform(600, 3600)
        report = {
            "defeito_canonico": defeito, "is_problem": False, "documented": False,
            "n_similar": random.randint(0, 4), "frequency_per_week": 0.0,
            "instructions": "", "sources": [],
        }
        return report, _payload(rpm), "🟢", "ok"

    if color == "🟡":
        defeito = random.choice(DOC_FAULTS)
        rpm = random.uniform(700, 3500)             # normal
        freq = round(random.uniform(0.5, 4.8), 1)   # baixa
        report = {
            "defeito_canonico": defeito, "is_problem": True, "documented": True,
            "n_similar": random.randint(1, 8), "frequency_per_week": freq,
            "instructions": INSTRUCTIONS.get(defeito, ""), "sources": SOURCES.get(defeito, []),
        }
        status = random.choices(["pendente", "em_andamento"], weights=[0.6, 0.4])[0]
        return report, _payload(rpm), "🟡", status

    # 🔴 — três causas possíveis de criticidade
    causa = random.choice(["sem_doc", "freq_alta", "rpm_anormal"])
    if causa == "sem_doc":
        defeito = random.choice(NODOC_FAULTS)
        rpm = random.uniform(700, 3500)
        freq = round(random.uniform(0.5, 4.5), 1)
        documented = False
        instr, srcs = "", []
    elif causa == "freq_alta":
        defeito = random.choice(DOC_FAULTS)
        rpm = random.uniform(700, 3500)
        freq = round(random.uniform(5.5, 12.0), 1)   # recorrente
        documented = True
        instr, srcs = INSTRUCTIONS.get(defeito, ""), SOURCES.get(defeito, [])
    else:  # rpm_anormal
        defeito = random.choice(DOC_FAULTS)
        rpm = random.choice([random.uniform(150, 380), random.uniform(3900, 5200)])
        freq = round(random.uniform(0.5, 4.5), 1)
        documented = True
        instr, srcs = INSTRUCTIONS.get(defeito, ""), SOURCES.get(defeito, [])

    report = {
        "defeito_canonico": defeito, "is_problem": True, "documented": documented,
        "n_similar": random.randint(2, 12), "frequency_per_week": freq,
        "instructions": instr, "sources": srcs,
    }
    status = random.choices(["pendente", "em_andamento", "descartado"],
                            weights=[0.6, 0.3, 0.1])[0]
    return report, _payload(rpm), "🔴", status


def _spread_dias(n: int, span: int) -> list[float]:
    """Gera `n` idades em dias dentro de [0, span], com viés p/ datas recentes
    e densidade garantida nos últimos 7 dias (alimenta o gráfico de 7 dias).

    ~35% caem em [0,7]; o resto espalha por todo o span com viés recente
    (random**1.6 → mais perto de hoje), pra que janelas de 60/90 dias também
    tenham pontos e exista tendência temporal nos gráficos de série.
    """
    dias = []
    n_recente = max(4, round(n * 0.35))
    for _ in range(n_recente):
        dias.append(random.uniform(0, 7))
    for _ in range(n - n_recente):
        dias.append(span * (random.random() ** 1.6))
    random.shuffle(dias)
    return dias


def seed(n: int, append: bool, span: int = 90) -> None:
    db.init_db()
    from core.db import SessionLocal, Evento, StatusHistorico

    with SessionLocal() as s:
        if not append:
            s.query(StatusHistorico).delete()
            s.query(Evento).delete()
            s.commit()
            print("Tabela `eventos` limpa.")

        # distribuição aleatória, garantindo ao menos alguns de cada cor
        n_red = random.randint(max(3, n // 6), max(4, n // 4))
        n_green = random.randint(max(3, n // 5), max(5, n // 3))
        n_yellow = n - n_red - n_green
        if n_yellow < 0:
            n_yellow, n_red, n_green = n, 0, 0
        cores = ["🔴"] * n_red + ["🟡"] * n_yellow + ["🟢"] * n_green
        random.shuffle(cores)

        idades = _spread_dias(len(cores), span)
        now = datetime.now(timezone.utc)
        n_resolvidos = 0
        for i, (cor, dias_ago) in enumerate(zip(cores, idades), start=1):
            report, payload, semaforo, status = _make_event(cor)
            ts = now - timedelta(days=dias_ago, hours=random.uniform(0, 24))

            # eventos antigos tendem a já estar resolvidos (vira 🟢, igual à UI).
            # recentes ficam abertos → backlog resolvido cresce ao longo do tempo.
            if report["is_problem"] and status != "descartado":
                p_res = min(0.9, max(0.0, (dias_ago - 7) / max(1, span - 7)))
                if random.random() < p_res:
                    status = "resolvido"
                    semaforo = "🟢"
                    n_resolvidos += 1

            ev = Evento(
                event_id=1000 + i,
                created_at=ts.isoformat(),
                defeito=report["defeito_canonico"],
                is_problem=report["is_problem"],
                documented=report["documented"],
                n_similar=report["n_similar"],
                frequency_per_week=report["frequency_per_week"],
                semaforo=semaforo,
                status=status,
                payload_json=json.dumps(payload, ensure_ascii=False),
                report_json=json.dumps(report, ensure_ascii=False),
                origem=random.choice(ORIGENS),
                ts=ts,
            )
            s.add(ev)
        s.commit()

    print(f"Inseridos {len(cores)} eventos em ~{span} dias.")
    print(f"  diagnostico: CRITICO {n_red}  ATENCAO {n_yellow}  NORMAL {n_green}")
    print(f"  {n_resolvidos} problemas antigos marcados resolvido (viram NORMAL/verde).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30, help="total de eventos (default 30)")
    ap.add_argument("--span", type=int, default=90, help="janela de datas em dias (default 90)")
    ap.add_argument("--append", action="store_true", help="não apaga eventos existentes")
    ap.add_argument("--seed", type=int, default=None, help="semente RNG p/ reprodutibilidade")
    args = ap.parse_args()
    if args.seed is not None:
        random.seed(args.seed)
    seed(args.n, args.append, args.span)
