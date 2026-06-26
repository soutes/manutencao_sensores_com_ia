"""Busca por similaridade no historico de eventos (banner.csv).

Dado um novo evento (JSON), acha registros historicos parecidos e retorna defeito
provavel + estatisticas (qtd ocorrencias, distribuicao temporal, frequencia).
KNN sobre features escaladas (StandardScaler + sklearn NearestNeighbors).

Stack leve de proposito: sem faiss/torch (wheels indisponiveis no Python 3.14 e
desnecessario para 166k x 23 dims). NearestNeighbors resolve em ms.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from .config import FEATURE_COLS, DATA_DIR
from .faults import normalize_fault


@dataclass
class SimilarityResult:
    canonical_fault: str
    n_similar: int
    neighbor_ids: list[int]
    mean_distance: float
    time_distribution: dict[str, int] = field(default_factory=dict)
    frequency_per_week: float = 0.0
    last_occurrence: str | None = None


CLEAN_PARQUET = DATA_DIR / "banner_clean.parquet"


class SimilarityIndex:
    """Indice KNN persistente sobre o historico."""

    def __init__(self) -> None:
        self.scaler: StandardScaler | None = None
        self.nn: NearestNeighbors | None = None
        self.medians: np.ndarray | None = None       # imputacao de features faltantes
        self.meta: pd.DataFrame | None = None         # id, created_at, fault_canonical
        self._fault_counts: dict[str, int] = {}       # ocorrencias por canonical (historico)
        self._weeks_span: float = 1.0                 # duracao do dataset em semanas

    # ---------------- construcao (offline) ----------------
    def build(self, csv_path: Path | None = None) -> "SimilarityIndex":
        df = pd.read_parquet(CLEAN_PARQUET)
        if "fault_canonical" not in df.columns:
            df["fault_canonical"] = df["fault"].map(lambda r: normalize_fault(r).canonical)
        df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")

        X = df[FEATURE_COLS].astype(float)
        self.medians = X.median().to_numpy()
        X = X.fillna(X.median())

        self.scaler = StandardScaler()
        Xs = self.scaler.fit_transform(X.to_numpy())

        self.nn = NearestNeighbors(n_neighbors=50, algorithm="auto", metric="euclidean")
        self.nn.fit(Xs)

        self.meta = df[["id", "created_at", "fault_canonical"]].reset_index(drop=True)
        self._fault_counts = self.meta["fault_canonical"].value_counts().to_dict()
        span = (self.meta["created_at"].max() - self.meta["created_at"].min())
        self._weeks_span = max(span.total_seconds() / (7 * 86400), 1.0)
        return self

    def save(self, dir_path: Path) -> None:
        dir_path.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "scaler": self.scaler, "nn": self.nn, "medians": self.medians,
            "meta": self.meta, "fault_counts": self._fault_counts,
            "weeks_span": self._weeks_span,
        }, dir_path / "similarity.joblib")

    @classmethod
    def load(cls, dir_path: Path) -> "SimilarityIndex":
        d = joblib.load(dir_path / "similarity.joblib")
        obj = cls()
        obj.scaler = d["scaler"]; obj.nn = d["nn"]; obj.medians = d["medians"]
        obj.meta = d["meta"]; obj._fault_counts = d["fault_counts"]
        obj._weeks_span = d["weeks_span"]
        return obj

    # ---------------- consulta (online) ----------------
    def _vectorize(self, event: dict) -> np.ndarray:
        vals = []
        for i, col in enumerate(FEATURE_COLS):
            v = event.get(col)
            vals.append(float(v) if v is not None else float(self.medians[i]))
        return self.scaler.transform(np.array(vals, dtype=float).reshape(1, -1))

    def query(self, event: dict, k: int = 50) -> SimilarityResult:
        if self.nn is None:
            raise RuntimeError("Indice nao carregado. Rode build()/load().")
        x = self._vectorize(event)
        dist, idx = self.nn.kneighbors(x, n_neighbors=min(k, len(self.meta)))
        dist, idx = dist[0], idx[0]
        rows = self.meta.iloc[idx]

        # voto PONDERADO por distancia (1/dist): vizinhos proximos pesam mais.
        # Holdout mostrou que maioria simples de 50 degrada (acc 0.62 vs 0.74 p/
        # vizinho proximo); a ponderacao recupera a precisao sem perder as
        # estatisticas globais.
        faults = rows["fault_canonical"].tolist()
        weights = 1.0 / (dist + 1e-9)
        score: dict[str, float] = {}
        for f, w in zip(faults, weights):
            score[f] = score.get(f, 0.0) + w
        canonical = max(score, key=score.get)

        # estatisticas sobre TODAS as ocorrencias do defeito previsto (historico)
        same = self.meta[self.meta["fault_canonical"] == canonical].copy()
        n_similar = int(self._fault_counts.get(canonical, len(same)))
        months = same["created_at"].dt.strftime("%Y-%m").value_counts().sort_index()
        time_dist = {k_: int(v_) for k_, v_ in months.items()}
        freq_week = round(n_similar / self._weeks_span, 2)
        last = same["created_at"].max()
        last_iso = last.isoformat() if pd.notna(last) else None

        return SimilarityResult(
            canonical_fault=canonical,
            n_similar=n_similar,
            neighbor_ids=[int(i) for i in rows["id"].tolist()],
            mean_distance=float(np.mean(dist)),
            time_distribution=time_dist,
            frequency_per_week=freq_week,
            last_occurrence=last_iso,
        )
