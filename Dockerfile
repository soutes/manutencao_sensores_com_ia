FROM python:3.14-slim

# OCR 100% Python (PyMuPDF render + RapidOCR-onnxruntime) — sem binario de sistema.
# Nao requer tesseract/poppler.

# Poetry sem virtualenv dentro do container (container ja e isolado)
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN pip install poetry==2.2.1

WORKDIR /app

# copia lock antes do codigo — camada de deps e cacheada ate mudar pyproject/lock
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root && rm -rf $POETRY_CACHE_DIR

COPY . .
ENV PYTHONPATH=/app/src

EXPOSE 8000 8501

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
