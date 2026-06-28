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
    # Avaliador de Retrieval — qualidade dos chunks antes do LLM
    retrieval_score: float = 0.0
    retrieval_nota: str = "N/A"
    retrieval_parecer: str = ""
    retrieval_ok: bool = True
    # Avaliador de Alucinação — resposta ancorada no contexto?
    hallucination_score: float = 0.0
    hallucination_nota: str = "N/A"
    hallucination_parecer: str = ""
    hallucination_ok: bool = True


_RAG_PATH = ARTIFACTS_DIR / "rag.joblib"


def _docs_fingerprint(docs_dir: Path = DOCS_DIR) -> str:
    """Gera fingerprint dos PDFs para detectar mudanças.

    Combina nomes + tamanhos + datas de modificação dos arquivos.
    Se qualquer PDF mudar (novo, editado, removido), o fingerprint muda
    e o índice é rebuildado automaticamente.
    """
    import hashlib, os
    h = hashlib.md5()
    for pdf in sorted(Path(docs_dir).glob("Doc*.pdf")):
        stat = os.stat(pdf)
        h.update(f"{pdf.name}:{stat.st_size}:{stat.st_mtime:.0f}".encode())
    return h.hexdigest()


def _ensure_rag_index(docs_dir: Path = DOCS_DIR) -> None:
    """Verifica se o índice RAG está atualizado. Se não, rebuilda.

    Detecta automaticamente:
    - PDFs novos adicionados
    - PDFs modificados
    - PDFs removidos
    """
    current_fp = _docs_fingerprint(docs_dir)

    # Carrega fingerprint salvo (se existe)
    saved_fp = None
    if _RAG_PATH.exists():
        try:
            d = joblib.load(_RAG_PATH)
            saved_fp = d.get("fingerprint")
        except Exception:
            pass

    if saved_fp != current_fp:
        print(f"[RAG] Fingerprint mudou — rebuildando índice...")
        build_doc_index(docs_dir)
        # Salva o fingerprint no índice
        d = joblib.load(_RAG_PATH)
        d["fingerprint"] = current_fp
        joblib.dump(d, _RAG_PATH)
        print(f"[RAG] Índice reconstruído com sucesso.")


# ─── avaliadores (professor) ──────────────────────────────────────────────────

def _grade_retrieval(score: float) -> dict:
    """Professor que avalia qualidade da busca ANTES de chamar o LLM.

    Nota F bloqueia a chamada ao LLM — sem contexto relevante não há prescrição.
    """
    if score >= 0.30:
        return {"nota": "A", "parecer": "Excelente — contexto altamente relevante para a query", "ok": True}
    if score >= 0.15:
        return {"nota": "B", "parecer": "Bom — contexto relevante recuperado", "ok": True}
    if score >= 0.05:
        return {"nota": "C", "parecer": "Satisfatório — contexto parcialmente relacionado", "ok": True}
    return {"nota": "F", "parecer": "Insuficiente — chunks recuperados não relacionados à query", "ok": False}


def _grade_hallucination(response: str, context: str) -> dict:
    """Professor que verifica se resposta do LLM está ancorada no contexto.

    Usa TF-IDF cosine similarity entre resposta e contexto recuperado.
    Score baixo = LLM extrapolou ou inventou além do documento.
    """
    if not context.strip() or not response.strip():
        return {"score": 0.0, "nota": "N/A", "parecer": "Sem contexto ou resposta para avaliar", "ok": True}
    try:
        from sklearn.metrics.pairwise import cosine_similarity as _cos
        d = joblib.load(_RAG_PATH)
        vecs = d["vectorizer"].transform([response, context])
        score = float(_cos(vecs[0:1], vecs[1:2])[0][0])
    except Exception:
        return {"score": 0.0, "nota": "N/A", "parecer": "Avaliação indisponível (índice não carregado)", "ok": True}

    if score >= 0.25:
        return {"score": score, "nota": "A", "parecer": "Aprovado — resposta bem ancorada no documento", "ok": True}
    if score >= 0.12:
        return {"score": score, "nota": "B", "parecer": "Bom — resposta majoritariamente ancorada", "ok": True}
    if score >= 0.05:
        return {"score": score, "nota": "C", "parecer": "Atenção — possível extrapolação do contexto", "ok": False}
    return {"score": score, "nota": "F", "parecer": "Reprovado — resposta possivelmente alucinada (baixa cobertura)", "ok": False}


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
                 "chunks": chunks, "metas": metas,
                 "fingerprint": _docs_fingerprint(docs_dir)}, _RAG_PATH)
    print(f"  RAG salvo: {len(chunks)} chunks, {matrix.shape[1]} termos")


def _retrieve(doc_name: str, query: str, top_k: int = 4) -> tuple[list[str], float]:
    """Retorna (chunks, max_score). max_score alimenta o avaliador de retrieval."""
    from sklearn.metrics.pairwise import cosine_similarity
    d = joblib.load(_RAG_PATH)
    idx = [i for i, m in enumerate(d["metas"]) if m == doc_name]
    if not idx:
        return [], 0.0
    sub = d["matrix"][idx]
    qv = d["vectorizer"].transform([query])
    sims = cosine_similarity(qv, sub)[0]
    order = sims.argsort()[::-1][:top_k]
    max_score = float(sims[order[0]]) if len(order) > 0 else 0.0
    return [d["chunks"][idx[i]] for i in order], max_score


def search_all(query: str, top_k: int = 5,
               min_score: float = 0.05) -> list[tuple[str, str, float]]:
    """Busca livre em todos os chunks (sem filtro por documento).

    Retorna lista de (chunk, doc_name, score) ordenada por relevância.
    Útil para perguntas de texto livre sem defeito canônico identificado.
    """
    from sklearn.metrics.pairwise import cosine_similarity
    if not _RAG_PATH.exists():
        return []
    d = joblib.load(_RAG_PATH)
    qv = d["vectorizer"].transform([query])
    sims = cosine_similarity(qv, d["matrix"])[0]
    order = sims.argsort()[::-1][:top_k]
    return [
        (d["chunks"][i], d["metas"][i], float(sims[i]))
        for i in order
        if sims[i] >= min_score
    ]


_SYSTEM = (
    "Voce e um assistente de manutencao industrial. Responda SOMENTE com base no "
    "CONTEXTO fornecido (procedimento tecnico). Nao invente passos que nao estejam "
    "no contexto. Se a informacao nao estiver no contexto, diga que nao foi "
    "encontrada no procedimento. Responda em portugues, em passos objetivos."
)


_QUERY_ENRIQUECIDA: dict[str, str] = {
    "rolamento":               "rolamento defeito manutenção inspeção substituição lubrificação",
    "rolamento_inner":         "rolamento pista interna defeito manutenção inspeção substituição lubrificação",
    "rolamento_outer":         "rolamento pista externa defeito manutenção inspeção substituição lubrificação",
    "rolamento_ball":          "rolamento esfera rolante defeito manutenção inspeção substituição lubrificação",
    "rolamento_combination":   "rolamento combinado defeito manutenção inspeção substituição lubrificação",
    "desalinhado":             "desalinhamento alinhamento angular paralelo acoplamento manutenção correção",
    "desbalanceado":           "desbalanceamento roda balanceamento estático dinâmico vibração manutenção",
    "correia":                 "correia transmissão desgaste substituição tensão polia manutenção",
    "polia":                   "polia roda dentada desgaste substituição alinhamento manutenção",
    "cocked_rotor":            "rotor inclinado desalinhamento angular manutenção correção",
    "eccentric_rotor":         "rotor excêntrico desbalanceamento vibração manutenção",
    "ventoinha":               "ventoinha cooling fan defeito vibração manutenção substituição",
    "falta_fase":              "falta fase elétrico motor manutenção inspeção elétrica",
}


def prescribe(canonical_fault: str, question: str | None = None) -> PrescriptionResult:
    # Auto-rebuild: detecta PDFs novos/modificados/removidos
    _ensure_rag_index()

    doc = FAULT_DOC_MAP.get(canonical_fault)
    if doc is None:  # sem documento (ou defeito desconhecido) -> gating
        return PrescriptionResult(
            canonical_fault=canonical_fault, documented=False, sources=[],
            retrieval_ok=False, retrieval_nota="F",
            retrieval_parecer="Sem documento cadastrado para este defeito",
            hallucination_ok=True, hallucination_nota="N/A",
            hallucination_parecer="Gating ativo — LLM não foi chamado",
            instructions=(f"Nao ha procedimento documentado para o defeito "
                          f"'{canonical_fault}'. Registre um novo documento "
                          f"descrevendo a correcao deste defeito para habilitar "
                          f"a prescricao."),
        )

    # Query enriquecida com termos técnicos relevantes para melhorar matching TF-IDF
    query = question or _QUERY_ENRIQUECIDA.get(
        canonical_fault,
        f"como corrigir o defeito {canonical_fault}"
    )
    context_chunks, max_score = _retrieve(doc, query)
    context = "\n\n".join(context_chunks)

    # ── Avaliador 1: Retrieval ──────────────────────────────────────────────
    ret = _grade_retrieval(max_score)

    if not ret["ok"]:
        # Retrieval reprovado: não aciona LLM, retorna falha explicada
        return PrescriptionResult(
            canonical_fault=canonical_fault, documented=True, sources=[doc],
            retrieval_score=max_score, retrieval_nota=ret["nota"],
            retrieval_parecer=ret["parecer"], retrieval_ok=False,
            hallucination_nota="N/A",
            hallucination_parecer="Retrieval reprovado — LLM não acionado",
            hallucination_ok=True,
            instructions=(f"[Retrieval insuficiente — nota {ret['nota']}] "
                          f"{ret['parecer']}. Nenhuma prescrição gerada."),
        )

    prompt = (f"CONTEXTO (procedimento {doc}):\n{context}\n\n"
              f"PERGUNTA: {query}\n\n"
              f"Liste as acoes de inspecao/manutencao/correcao recomendadas, "
              f"citando que vieram do procedimento {doc}.")
    try:
        answer = llm_generate(prompt, system=_SYSTEM)
    except Exception as e:  # noqa: BLE001 -- LLM (Ollama) pode estar off
        answer = ("[LLM indisponivel - exibindo trechos do procedimento]\n\n"
                  + context + f"\n\n(erro LLM: {e})")
        return PrescriptionResult(
            canonical_fault=canonical_fault, documented=True, sources=[doc],
            retrieval_score=max_score, retrieval_nota=ret["nota"],
            retrieval_parecer=ret["parecer"], retrieval_ok=True,
            hallucination_nota="N/A",
            hallucination_parecer="LLM offline — avaliação de alucinação ignorada",
            hallucination_ok=True,
            instructions=answer,
        )

    # ── Avaliador 2: Alucinação ─────────────────────────────────────────────
    hal = _grade_hallucination(answer, context)

    return PrescriptionResult(
        canonical_fault=canonical_fault, documented=True, sources=[doc],
        retrieval_score=max_score, retrieval_nota=ret["nota"],
        retrieval_parecer=ret["parecer"], retrieval_ok=True,
        hallucination_score=hal["score"], hallucination_nota=hal["nota"],
        hallucination_parecer=hal["parecer"], hallucination_ok=hal["ok"],
        instructions=answer,
    )
