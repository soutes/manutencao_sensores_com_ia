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
        # Classificação por similaridade (KNN — fluxo principal)
        "kneighbor_voto": res.kneighbor_voto,
        "kneighbor_confianca": res.kneighbor_confianca,
        # Confirmação RF (análise de dados)
        "rf_fault": res.rf_fault,
        "rf_confianca": res.rf_confianca,
    }

    _eval_defaults = dict(
        retrieval_score=0.0, retrieval_nota="N/A", retrieval_parecer="",
        retrieval_ok=True, hallucination_score=0.0,
        hallucination_nota="N/A", hallucination_parecer="", hallucination_ok=True,
    )

    if not info.is_problem:
        report.update(documented=False,
                      instructions="Evento corresponde a ESTADO operacional "
                                   f"('{canonical}'), nao a defeito. Nenhuma acao.",
                      sources=[], **_eval_defaults)
        return report

    presc = prescribe(canonical)
    report.update(
        documented=presc.documented,
        instructions=presc.instructions,
        sources=presc.sources,
        retrieval_score=getattr(presc, "retrieval_score", 0.0),
        retrieval_nota=getattr(presc, "retrieval_nota", "N/A"),
        retrieval_parecer=getattr(presc, "retrieval_parecer", ""),
        retrieval_ok=getattr(presc, "retrieval_ok", True),
        hallucination_score=getattr(presc, "hallucination_score", 0.0),
        hallucination_nota=getattr(presc, "hallucination_nota", "N/A"),
        hallucination_parecer=getattr(presc, "hallucination_parecer", ""),
        hallucination_ok=getattr(presc, "hallucination_ok", True),
    )
    return report
