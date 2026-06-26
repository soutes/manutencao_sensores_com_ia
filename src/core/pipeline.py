"""Orquestrador: novo evento -> report completo (similaridade + gating + prescricao).

Este e o contrato que API, Streamlit e Telegram bot consomem. NAO mexer na forma
do dict de retorno sem alinhar com quem consome.
"""
from __future__ import annotations
from .config import ARTIFACTS_DIR
from .faults import normalize_fault
from .similarity import SimilarityIndex
from .rag import prescribe


def process_event(event: dict) -> dict:
    """Pipeline completo de um evento de sensor.

    Retorna dict com:
      event_id, defeito (canonico + legivel), is_problem,
      n_similar, frequency_per_week, last_occurrence, time_distribution,
      documented, instructions, sources.
    """
    sim = SimilarityIndex.load(ARTIFACTS_DIR)
    res = sim.query(event)

    canonical = res.canonical_fault
    info = normalize_fault(canonical)       # idempotente p/ rotulo ja canonico

    report: dict = {
        "event_id": event.get("id"),
        "created_at": event.get("created_at"),
        "defeito_canonico": canonical,
        "is_problem": info.is_problem,
        "n_similar": res.n_similar,
        "frequency_per_week": res.frequency_per_week,
        "last_occurrence": res.last_occurrence,
        "time_distribution": res.time_distribution,
        "mean_distance": res.mean_distance,
    }

    if not info.is_problem:
        report.update(documented=False,
                      instructions="Evento corresponde a ESTADO operacional "
                                   f"('{canonical}'), nao a defeito. Nenhuma acao.",
                      sources=[])
        return report

    presc = prescribe(canonical)
    report.update(documented=presc.documented,
                  instructions=presc.instructions,
                  sources=presc.sources)
    return report
