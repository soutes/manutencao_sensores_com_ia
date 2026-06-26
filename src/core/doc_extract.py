"""Extracao de texto dos procedimentos (PDFs).

Doc2..Doc6 tem camada de texto -> pdfplumber.
Doc1 e ESCANEADO -> OCR via PyMuPDF (render) + RapidOCR (onnxruntime, sem binario
de sistema; funciona em Python 3.14). Tudo com degradacao graciosa.
"""
from __future__ import annotations
from pathlib import Path

import pdfplumber

_OCR = None  # RapidOCR carregado sob demanda (pesa no import)


def _get_ocr():
    global _OCR
    if _OCR is None:
        from rapidocr_onnxruntime import RapidOCR
        _OCR = RapidOCR()
    return _OCR


def _extract_text_layer(pdf_path: Path) -> str:
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()


def _extract_ocr(pdf_path: Path, dpi: int = 200) -> str:
    """OCR pagina a pagina. Retorna '' se OCR indisponivel."""
    try:
        import fitz  # PyMuPDF
        import numpy as np
        ocr = _get_ocr()
    except Exception as e:  # noqa: BLE001
        print(f"  [OCR indisponivel: {e}]")
        return ""
    out = []
    doc = fitz.open(pdf_path)
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img = img[:, :, :3]
        res, _ = ocr(img)
        if res:
            out.append(" ".join(t[1] for t in res))
    return "\n".join(out).strip()


def extract_doc(pdf_path: Path) -> str:
    """Texto de um PDF; cai para OCR se a camada de texto vier vazia (escaneado)."""
    text = _extract_text_layer(pdf_path)
    if len(text) < 50:  # provavelmente escaneado
        print(f"  {pdf_path.name}: sem camada de texto -> OCR")
        text = _extract_ocr(pdf_path)
    return text
