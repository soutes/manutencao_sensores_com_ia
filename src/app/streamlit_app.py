"""CONTRATO: dashboard + chat Streamlit. >>> AGENTE C preenche TODOs. <<<

Deve mostrar (Figura 01 - Saida):
  - Input: JSON do novo evento (text area).
  - Tipo de defeito + se e problema.
  - Quantidade de ocorrencias similares.
  - Frequencia de ocorrencias + distribuicao temporal (grafico Plotly).
  - Instrucoes de solucao (RAG) OU aviso 'sem documento'.
  - Aba de chat livre sobre o defeito.
  - Dashboard geral: histograma de falhas, timeline.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
from core.pipeline import process_event

st.set_page_config(page_title="Manutencao Prescritiva", layout="wide")
st.title("Manutencao Prescritiva - SENAI SC")

# TODO(Agente C): input JSON, chamar process_event, renderizar report + graficos.
st.info("Stub - Agente C implementa dashboard + chat.")
