"""CONTRATO: API FastAPI expondo o core. >>> AGENTE D preenche TODOs. <<<"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from pydantic import BaseModel
from core.pipeline import process_event
from core.rag import prescribe

app = FastAPI(title="Manutencao Prescritiva SENAI", version="0.1")


class Event(BaseModel):
    id: int | None = None
    created_at: str | None = None
    # demais features chegam livres (model_config extra=allow)
    model_config = {"extra": "allow"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/event")
def post_event(event: Event):
    """Recebe evento de sensor -> report completo."""
    return process_event(event.model_dump())


@app.post("/chat")
def chat(payload: dict):
    """TODO(Agente D): pergunta livre -> prescribe(fault, question)."""
    fault = payload.get("fault", "")
    question = payload.get("question")
    return prescribe(fault, question).__dict__
