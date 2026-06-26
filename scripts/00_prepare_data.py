"""Gera data/banner_clean.parquet a partir de docs/banner.csv (normaliza fault)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from core.faults import normalize_fault
from core.config import BANNER_CSV, DATA_DIR


def main() -> None:
    df = pd.read_csv(BANNER_CSV)
    fi = df["fault"].map(normalize_fault)
    df["fault_canonical"] = [x.canonical for x in fi]
    df["is_problem"] = [x.is_problem for x in fi]
    df["documented"] = [x.documented for x in fi]
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    out = DATA_DIR / "banner_clean.parquet"
    df.to_parquet(out, index=False)
    print(f"OK {len(df)} linhas -> {out}")
    print("canonicos:", df["fault_canonical"].nunique(),
          "| problemas:", int(df["is_problem"].sum()))


if __name__ == "__main__":
    main()
