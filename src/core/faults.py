"""Normalizacao de rotulos de falha (coluna `fault` do banner.csv).

O dataset tem rotulos sujos: variantes (`rolamento_inner`, `rolamento_inner_2`,
`new_rolamento_inner_0`...), sufixos de contexto (`_carga`, `_pos_2`, `_adxl_0`,
`_novo`...) e ERROS de digitacao (`mortor_desligado`, `cockecocked_adxl_0`,
`ddesbalanceado`, `normla_carga`...).

Este modulo colapsa tudo em um rotulo CANONICO e classifica:
  - is_problem: True se e um defeito (precisa prescricao), False se e estado.
  - doc: arquivo de procedimento que cobre o defeito (None se nao documentado).

Os estados `normal`, `baseline`, `teste`, `acelerando`, `motor_desligado` NAO sao
problemas (enunciado, secao 6).
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class FaultInfo:
    raw: str            # rotulo original
    canonical: str      # rotulo canonico (familia)
    is_problem: bool    # True = defeito, False = estado operacional
    documented: bool    # True = existe procedimento
    doc: str | None     # arquivo do procedimento ou None


# Defeito canonico -> documento de procedimento (None = sem documentacao).
# Doc1 e PDF escaneado (precisa OCR); pela cobertura de falhas e o de rolamentos.
FAULT_DOC_MAP: dict[str, str | None] = {
    "rolamento":        "Doc1.pdf",   # rolamento generico
    "rolamento_inner":  "Doc1.pdf",
    "rolamento_outer":  "Doc1.pdf",
    "rolamento_ball":   "Doc1.pdf",
    "rolamento_combination": "Doc1.pdf",
    "desalinhado":      "Doc2.pdf",
    "desbalanceado":    "Doc3.pdf",
    "correia":          "Doc4.pdf",
    "polia":            "Doc5.pdf",
    "cocked_rotor":     "Doc6.pdf",
    # defeitos SEM procedimento -> sistema deve pedir registro de documento
    "eccentric_rotor":  None,
    "ventoinha":        None,
    "falta_fase":       None,
}

# Rotulos canonicos que representam ESTADO operacional (nao defeito).
STATES = {"normal", "baseline", "teste", "acelerando", "motor_desligado"}


def _canonical(raw: str) -> str:
    """Mapeia rotulo bruto -> canonico via deteccao por palavra-chave (robusta a typos)."""
    s = raw.strip().lower()

    # --- ESTADOS (nao-problema) ---
    if "acelerando" in s:
        return "acelerando"
    if "deslig" in s:                       # motor_desligado, mortor_desligado, motor_desligado_novo
        return "motor_desligado"
    if "baseline" in s:
        return "baseline"
    if "test" in s or s.startswith("new_tes"):  # teste, new_teste, new_tes
        return "teste"
    if "normal" in s or "normla" in s:      # normal*, normla (typo)
        return "normal"

    # --- DEFEITOS (ordem importa: chaves mais especificas primeiro) ---
    if "alinhad" in s:                      # desalinhado, new_desalinhado
        return "desalinhado"
    if any(t in s for t in ("balanc", "banceado", "banlanc", "banlance")):
        return "desbalanceado"              # desbalanceado, desabalanceado, ddesbalanceado, desbanlanceado...
    if "rolamento" in s:
        if "inner" in s:       return "rolamento_inner"
        if "outer" in s:       return "rolamento_outer"
        if "ball" in s:        return "rolamento_ball"
        if "comb" in s:        return "rolamento_combination"
        return "rolamento"
    if "eccentric" in s:
        return "eccentric_rotor"
    if "cocked" in s:                       # cocked_rotor, cockecocked (typo)
        return "cocked_rotor"
    if "ventoinha" in s:
        return "ventoinha"
    if "polia" in s:
        return "polia"
    if "correia" in s:
        return "correia"
    if "fase" in s:                         # falta_fase, new_falta_fase
        return "falta_fase"

    return "desconhecido"


def normalize_fault(raw: str) -> FaultInfo:
    """Ponto de entrada: rotulo bruto -> FaultInfo classificado."""
    canon = _canonical(raw)
    is_problem = canon not in STATES and canon != "desconhecido"
    doc = FAULT_DOC_MAP.get(canon)
    documented = doc is not None
    return FaultInfo(raw=raw, canonical=canon, is_problem=is_problem,
                     documented=documented, doc=doc)
