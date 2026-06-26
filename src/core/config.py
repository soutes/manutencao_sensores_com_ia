"""Configuracao central e contratos de dados compartilhados."""
from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs"
DATA_DIR = ROOT / "data"
ARTIFACTS_DIR = ROOT / "artifacts"      # indices FAISS/Chroma, scaler, etc.
BANNER_CSV = DOCS_DIR / "banner.csv"

DATA_DIR.mkdir(exist_ok=True)
ARTIFACTS_DIR.mkdir(exist_ok=True)

# 24 features numericas de vibracao (ordem fixa - usar SEMPRE esta lista).
FEATURE_COLS = [
    "z_rms_velocity_in_s", "z_rms_velocity_mm_s", "temperature_f", "temperature_c",
    "x_rms_velocity_in_s", "x_rms_velocity_mm_s", "z_peak_acceleration_g",
    "x_peak_acceleration_g", "z_peak_vel_comp_freq_hz", "x_peak_vel_comp_freq_hz",
    "z_rms_acceleration_g", "x_rms_acceleration_g", "z_kurtosis", "x_kurtosis",
    "z_crest_factor", "x_crest_factor", "z_peak_velocity_in_s", "z_peak_velocity_mm_s",
    "x_peak_velocity_in_s", "x_peak_velocity_mm_s", "z_high_freq_rms_accel_g",
    "x_high_freq_rms_accel_g", "rpm",
]

# LLM: backend plugavel. LLM_BACKEND = "api" | "ollama".
LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:7b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-base")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
