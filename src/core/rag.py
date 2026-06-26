"""CONTRATO: RAG sobre os procedimentos (PDFs) + prescricao de correcao.

>>> AGENTE B preenche os corpos marcados com TODO. Nao mude as assinaturas. <<<

Pontos criticos:
  - Doc1.pdf e ESCANEADO (sem texto) -> precisa OCR (pytesseract/easyocr).
  - Doc2..Doc6 -> extrair com pdfplumber.
  - Gating de cobertura: so prescreve defeito com documento; senao retorna
    documented=False com mensagem pedindo registro de novo documento.
  - Anti-alucinacao: LLM responde SO com base no contexto recuperado (citar fonte).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PrescriptionResult:
    canonical_fault: str
    documented: bool                       # existe procedimento?
    instructions: str                      # texto da acao recomendada (ou aviso)
    sources: list[str] = field(default_factory=list)  # docs citados


def build_doc_index(docs_dir: Path) -> None:
    """TODO(Agente B): OCR Doc1 + extrair Doc2..6, chunk, embed (EMBED_MODEL),
    persistir vector store (Chroma) em ARTIFACTS_DIR. Indexar com metadado do
    defeito canonico associado (ver core.faults.FAULT_DOC_MAP)."""
    raise NotImplementedError


def prescribe(canonical_fault: str, question: str | None = None) -> PrescriptionResult:
    """TODO(Agente B): se defeito nao documentado (FAULT_DOC_MAP[x] is None ou
    ausente) -> documented=False + mensagem 'registre novo documento'.
    Senao: recuperar chunks do doc, montar prompt restrito ao contexto, chamar
    core.llm.llm_generate, retornar instrucoes + fontes."""
    raise NotImplementedError
