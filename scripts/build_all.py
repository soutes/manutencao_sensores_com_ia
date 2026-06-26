"""Constroi todos os artefatos (similaridade + RAG). Rodar uma vez offline."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.config import BANNER_CSV, ARTIFACTS_DIR, DOCS_DIR
from core.similarity import SimilarityIndex
from core.rag import build_doc_index


def main() -> None:
    print("[1/2] Indice de similaridade...")
    idx = SimilarityIndex().build(BANNER_CSV)
    idx.save(ARTIFACTS_DIR)
    print("[2/2] Indice RAG (docs)...")
    build_doc_index(DOCS_DIR)
    print("OK - artefatos em", ARTIFACTS_DIR)


if __name__ == "__main__":
    main()
