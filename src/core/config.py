"""Configuracao central e contratos de dados compartilhados."""
from __future__ import annotations
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
except ImportError:
    pass

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

# ====================== PERFIL (o interruptor LGPD) ======================
# LLM_PROVIDER decide ONDE o conteudo do manual e processado:
#   "ollama"     -> LLM local on-prem, nada vaza (producao / LGPD)
#   "openrouter" -> API externa, so para DEMO com dados sinteticos do case
LLM_PROVIDER = os.getenv("LLM_PROVIDER", os.getenv("LLM_BACKEND", "ollama")).lower()

# Ollama (perfil local)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", os.getenv("LLM_MODEL", "qwen2.5:7b"))

# OpenRouter (perfil online) - OpenAI-compatible
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

# compat retro
LLM_BACKEND = LLM_PROVIDER
LLM_MODEL = OLLAMA_MODEL

EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-base")

# ====================== BANCO (camada trocavel) ======================
# DATABASE_URL define o backend:
#   ausente            -> SQLite local em data/fiesc.db (on-prem / offline)
#   postgres://...     -> Supabase / Postgres (perfil cloud, persistente)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'fiesc.db').as_posix()}")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
