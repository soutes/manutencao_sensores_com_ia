"""RAG sobre os procedimentos (PDFs) + prescricao de correcao.

Pipeline: extrai texto (pdfplumber / OCR) -> chunk -> retriever TF-IDF (sklearn,
sem torch) -> LLM redige a acao com base SO no contexto recuperado (anti-alucinacao).

Gating: so prescreve defeito com documento (core.faults.FAULT_DOC_MAP). Defeito sem
doc -> documented=False com mensagem pedindo registro de novo documento.

Stack leve de proposito: TF-IDF + cosseno em vez de embeddings neurais. Corpus = 6
procedimentos curtos; recuperacao por sobreposicao lexical funciona bem e dispensa
torch/chromadb (indisponiveis no Python 3.14). Embedding neural fica como evolucao.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

import joblib

from .config import DOCS_DIR, ARTIFACTS_DIR
from .faults import FAULT_DOC_MAP
from .doc_extract import extract_doc
from .llm import llm_generate


@dataclass
class PrescriptionResult:
    canonical_fault: str
    documented: bool
    instructions: str
    sources: list[str] = field(default_factory=list)


_RAG_PATH = ARTIFACTS_DIR / "rag.joblib"


def _chunk(text: str, size: int = 800, overlap: int = 150) -> list[str]:
    words, chunks, cur, cur_len = text.split(), [], [], 0
    for w in words:
        cur.append(w); cur_len += len(w) + 1
        if cur_len >= size:
            chunks.append(" ".join(cur))
            keep = " ".join(cur)[-overlap:].split()
            cur, cur_len = keep[:], sum(len(x) + 1 for x in keep)
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def build_doc_index(docs_dir: Path = DOCS_DIR) -> None:
    """Extrai, chunka, vetoriza (TF-IDF) e persiste o indice de procedimentos."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    docs = sorted(p for p in Path(docs_dir).glob("Doc*.pdf"))
    chunks, metas = [], []
    for pdf in docs:
        text = extract_doc(pdf)
        c = _chunk(text)
        print(f"  {pdf.name}: {len(text)} chars -> {len(c)} chunks")
        chunks.extend(c)
        metas.extend([pdf.name] * len(c))

    vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1)
    matrix = vectorizer.fit_transform(chunks)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vectorizer, "matrix": matrix,
                 "chunks": chunks, "metas": metas}, _RAG_PATH)
    print(f"  RAG salvo: {len(chunks)} chunks, {matrix.shape[1]} termos")


def _retrieve(doc_name: str, query: str, top_k: int = 4) -> list[str]:
    from sklearn.metrics.pairwise import cosine_similarity
    d = joblib.load(_RAG_PATH)
    idx = [i for i, m in enumerate(d["metas"]) if m == doc_name]
    if not idx:
        return []
    sub = d["matrix"][idx]
    qv = d["vectorizer"].transform([query])
    sims = cosine_similarity(qv, sub)[0]
    order = sims.argsort()[::-1][:top_k]
    return [d["chunks"][idx[i]] for i in order]


_SYSTEM = (
    "Voce e um assistente de manutencao industrial. Responda SOMENTE com base no "
    "CONTEXTO fornecido (procedimento tecnico). Nao invente passos que nao estejam "
    "no contexto. Se a informacao nao estiver no contexto, diga que nao foi "
    "encontrada no procedimento. Responda em portugues, em passos objetivos."
)


def prescribe(canonical_fault: str, question: str | None = None) -> PrescriptionResult:
    doc = FAULT_DOC_MAP.get(canonical_fault)
    if doc is None:  # sem documento (ou defeito desconhecido) -> gating
        return PrescriptionResult(
            canonical_fault=canonical_fault, documented=False, sources=[],
            instructions=(f"Nao ha procedimento documentado para o defeito "
                          f"'{canonical_fault}'. Registre um novo documento "
                          f"descrevendo a correcao deste defeito para habilitar "
                          f"a prescricao."),
        )

    query = question or f"como corrigir o defeito {canonical_fault}"
    context_chunks = _retrieve(doc, query)
    context = "\n\n".join(context_chunks)

    prompt = (f"CONTEXTO (procedimento {doc}):\n{context}\n\n"
              f"PERGUNTA: {query}\n\n"
              f"Liste as acoes de inspecao/manutencao/correcao recomendadas, "
              f"citando que vieram do procedimento {doc}.")
    try:
        answer = llm_generate(prompt, system=_SYSTEM)
    except Exception as e:  # noqa: BLE001 -- LLM (Ollama) pode estar off
        answer = ("[LLM indisponivel - exibindo trechos do procedimento]\n\n"
                  + context + f"\n\n(erro LLM: {e})")

    return PrescriptionResult(canonical_fault=canonical_fault, documented=True,
                              instructions=answer, sources=[doc])
