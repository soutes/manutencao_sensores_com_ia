"""CONTRATO: busca por similaridade no historico de eventos (banner.csv).

>>> AGENTE A preenche os corpos marcados com TODO. Nao mude as assinaturas. <<<

Objetivo: dado um novo evento (JSON), achar registros historicos parecidos e
retornar defeito provavel + estatisticas (qtd ocorrencias, distribuicao temporal,
frequencia). Usar KNN sobre features escaladas (StandardScaler + FAISS ou sklearn).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SimilarityResult:
    canonical_fault: str               # defeito previsto (voto majoritario dos vizinhos)
    n_similar: int                     # nº de ocorrencias do MESMO defeito no historico
    neighbor_ids: list[int]            # ids dos K vizinhos
    mean_distance: float               # distancia media aos vizinhos (confianca)
    time_distribution: dict[str, int] = field(default_factory=dict)  # {"2026-05": 12, ...}
    frequency_per_week: float = 0.0    # ocorrencias/semana (janela recente)
    last_occurrence: str | None = None # created_at da ultima ocorrencia


class SimilarityIndex:
    """Indice KNN persistente sobre o historico."""

    def __init__(self) -> None:
        self.scaler = None
        self.index = None
        self.meta = None  # DataFrame: id, created_at, canonical_fault

    # --- construcao (offline, roda em scripts/02_build_data.py) ---
    def build(self, csv_path: Path) -> "SimilarityIndex":
        """TODO(Agente A): carregar csv, normalizar fault (core.faults.normalize_fault),
        escalar FEATURE_COLS, montar indice FAISS. Guardar scaler/index/meta."""
        raise NotImplementedError

    def save(self, dir_path: Path) -> None:
        """TODO(Agente A): persistir scaler + index + meta em ARTIFACTS_DIR."""
        raise NotImplementedError

    @classmethod
    def load(cls, dir_path: Path) -> "SimilarityIndex":
        """TODO(Agente A): recarregar artefatos."""
        raise NotImplementedError

    # --- consulta (online) ---
    def query(self, event: dict, k: int = 50) -> SimilarityResult:
        """TODO(Agente A): escalar evento, buscar K vizinhos, voto majoritario,
        calcular time_distribution / frequency_per_week / last_occurrence."""
        raise NotImplementedError
