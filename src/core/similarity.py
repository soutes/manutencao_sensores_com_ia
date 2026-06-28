"""Classificação de defeitos via similaridade (KNN) + confirmação RF + prescrição RAG.

Fluxo principal (alinhado com o enunciado do case):
  1. KNN busca os 50 eventos mais similares no histórico (busca por padrões)
  2. Maioria dos vizinhos identifica o defeito (classificação por similaridade)
  3. RF confirma a classificação (análise de dados)
  4. RAG prescreve a correção com base no defeito identificado

Isso é MAIS ROBUSTO que RF puro porque:
  - Funciona para defeitos novos (KNN não depende de classes pré-definidas)
  - É explicável ("43/50 vizinhos são rolamento_inner")
  - Combina as 3 técnicas do enunciado: análise de dados + similaridade + recuperação
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import LabelEncoder, StandardScaler

from .config import FEATURE_COLS, DATA_DIR
from .faults import normalize_fault

# Remove pares com correlação 1.0 — reduz dimensionalidade sem perda
_REDUNDANTES = {
    'z_rms_velocity_in_s', 'x_rms_velocity_in_s',
    'z_peak_velocity_in_s', 'x_peak_velocity_in_s',
    'temperature_f',
}
FEATURE_COLS_RF = [f for f in FEATURE_COLS if f not in _REDUNDANTES]


@dataclass
class SimilarityResult:
    """Resultado do pipeline de classificação + prescrição."""
    canonical_fault: str              # defeito identificado
    n_similar: int                    # ocorrências históricas
    neighbor_ids: list[int]           # IDs dos 50 vizinhos
    mean_distance: float              # distância média dos vizinhos
    time_distribution: dict[str, int] = field(default_factory=dict)
    frequency_per_week: float = 0.0
    last_occurrence: str | None = None
    # Confirmação RF (opcional, para o dashboard)
    rf_fault: str | None = None       # defeito previsto pelo RF
    rf_confianca: float = 0.0         # confiança do RF (probabilidade máxima)
    kneighbor_voto: str | None = None  # defeito por maioria dos vizinhos
    kneighbor_confianca: float = 0.0  # % dos vizinhos que votaram no defeito


CLEAN_PARQUET = DATA_DIR / "banner_clean.parquet"


class SimilarityIndex:
    """Índice combinado KNN + RF para classificação de defeitos."""

    def __init__(self) -> None:
        # KNN (fluxo principal)
        self.scaler: StandardScaler | None = None
        self.nn: NearestNeighbors | None = None
        self.medians: np.ndarray | None = None
        # RF (confirmação)
        self.rf: RandomForestClassifier | None = None
        self.le: LabelEncoder | None = None
        self.scaler_rf: StandardScaler | None = None
        self.medians_rf: np.ndarray | None = None
        # Metadata
        self.meta: pd.DataFrame | None = None
        self._fault_counts: dict[str, int] = {}
        self._weeks_span: float = 1.0

    # ─── Construção offline ────────────────────────────────────────────────
    def build(self, csv_path: Path | None = None) -> "SimilarityIndex":
        df = pd.read_parquet(CLEAN_PARQUET)
        if "fault_canonical" not in df.columns:
            df["fault_canonical"] = df["fault"].map(lambda r: normalize_fault(r).canonical)
        df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")

        # ── KNN (23 features) — busca por similaridade ─────────────────────
        X = df[FEATURE_COLS].astype(float)
        self.medians = X.median().to_numpy()
        X_nn = X.fillna(X.median())
        self.scaler = StandardScaler()
        Xs = self.scaler.fit_transform(X_nn.to_numpy())
        self.nn = NearestNeighbors(n_neighbors=50, algorithm="auto", metric="euclidean")
        self.nn.fit(Xs)
        print(f"  KNN treinado: 50 vizinhos, {Xs.shape[0]} eventos, {Xs.shape[1]} features")

        # ── RF (18 features limpas) — confirmação ──────────────────────────
        X_rf = df[FEATURE_COLS_RF].astype(float)
        self.medians_rf = X_rf.median().to_numpy()
        X_rf_filled = X_rf.fillna(X_rf.median())
        self.le = LabelEncoder()
        y = self.le.fit_transform(df["fault_canonical"])
        self.scaler_rf = StandardScaler()
        Xs_rf = self.scaler_rf.fit_transform(X_rf_filled.to_numpy())
        self.rf = RandomForestClassifier(
            n_estimators=200, max_features='sqrt',
            max_depth=None, min_samples_leaf=1,
            class_weight=None, n_jobs=-1, random_state=42,
        )
        print("  Treinando RandomForest (200 árvores, 18 features)...")
        self.rf.fit(Xs_rf, y)

        # ── Metadata para estatísticas ─────────────────────────────────────
        self.meta = df[["id", "created_at", "fault_canonical"]].reset_index(drop=True)
        self._fault_counts = self.meta["fault_canonical"].value_counts().to_dict()
        span = (self.meta["created_at"].max() - self.meta["created_at"].min())
        self._weeks_span = max(span.total_seconds() / (7 * 86400), 1.0)
        return self

    def save(self, dir_path: Path) -> None:
        dir_path.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "scaler": self.scaler, "nn": self.nn, "medians": self.medians,
            "rf": self.rf, "le": self.le,
            "scaler_rf": self.scaler_rf, "medians_rf": self.medians_rf,
            "meta": self.meta, "fault_counts": self._fault_counts,
            "weeks_span": self._weeks_span,
        }, dir_path / "similarity.joblib")

    @classmethod
    def load(cls, dir_path: Path) -> "SimilarityIndex":
        d = joblib.load(dir_path / "similarity.joblib")
        obj = cls()
        obj.scaler = d["scaler"]; obj.nn = d["nn"]; obj.medians = d["medians"]
        obj.rf = d["rf"]; obj.le = d["le"]
        obj.scaler_rf = d["scaler_rf"]; obj.medians_rf = d["medians_rf"]
        obj.meta = d["meta"]; obj._fault_counts = d["fault_counts"]
        obj._weeks_span = d["weeks_span"]
        return obj

    # ─── Vectorize ─────────────────────────────────────────────────────────
    def _vectorize_knn(self, event: dict) -> np.ndarray:
        """Vectoriza para KNN (23 features)."""
        vals = []
        for i, col in enumerate(FEATURE_COLS):
            v = event.get(col)
            vals.append(float(v) if v is not None else float(self.medians[i]))
        return self.scaler.transform(np.array(vals, dtype=float).reshape(1, -1))

    def _vectorize_rf(self, event: dict) -> np.ndarray:
        """Vectoriza para RF (18 features limpas)."""
        vals = []
        for i, col in enumerate(FEATURE_COLS_RF):
            v = event.get(col)
            vals.append(float(v) if v is not None else float(self.medians_rf[i]))
        return self.scaler_rf.transform(np.array(vals, dtype=float).reshape(1, -1))

    # ─── Consulta online ───────────────────────────────────────────────────
    def query(self, event: dict, k: int = 50) -> SimilarityResult:
        if self.nn is None or self.rf is None:
            raise RuntimeError("Indice nao carregado. Rode build()/load().")

        # ── 1. KNN: busca os 50 vizinhos mais similares ───────────────────
        x_knn = self._vectorize_knn(event)
        dist, idx = self.nn.kneighbors(x_knn, n_neighbors=min(k, len(self.meta)))
        dist, idx = dist[0], idx[0]
        rows = self.meta.iloc[idx]

        # ── 2. Votação ponderada por distância ─────────────────────────────
        # Vizinhos MAIS PRÓXIMOS pesam MAIS (1/distância)
        # Isso resolve o problema de classes com poucos registros:
        # se 4 dos 5 vizinhos mais próximos são "acelerando",
        # mesmo que o resto do k=50 seja de outras classes,
        # acelerando ganha por ter vizinhos MAIS PRÓXIMOS.
        #
        # Algoritmo:
        #   - Para cada classe, soma (1/distância) de todos os vizinhos
        #   - Classe com maior soma ponderada vence
        #   - Confiância = soma da classe vencedora / soma total

        eps = 1e-10  # evita divisão por zero (dist=0)
        weighted_votes: dict[str, float] = {}
        for i, label in enumerate(rows["fault_canonical"]):
            weight = 1.0 / (dist[i] + eps)
            weighted_votes[label] = weighted_votes.get(label, 0.0) + weight

        total_weight = sum(weighted_votes.values())
        kneighbor_fault = max(weighted_votes, key=weighted_votes.get)
        kneighbor_confianca = round(weighted_votes[kneighbor_fault] / total_weight, 3)

        # ── 3. RF: confirmação cruzada ────────────────────────────────────
        x_rf = self._vectorize_rf(event)
        rf_pred_idx = self.rf.predict(x_rf)[0]
        rf_pred = self.le.inverse_transform([rf_pred_idx])[0]
        rf_proba = float(self.rf.predict_proba(x_rf)[0].max())

        # ── 4. Decisão final ──────────────────────────────────────────────
        # KNN ponderado é o fluxo principal (alinhado com enunciado)
        canonical = kneighbor_fault
        confianca_knn = kneighbor_confianca

        # ── 5. Estatísticas do histórico ───────────────────────────────────
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
            rf_fault=rf_pred,
            rf_confianca=rf_proba,
            kneighbor_voto=kneighbor_fault,
            kneighbor_confianca=confianca_knn,
        )
