FROM python:3.12-slim

# binarios p/ OCR do Doc1 (tesseract) e rasterizacao de PDF (poppler)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-por poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONPATH=/app/src

# constroi indices na imagem (similaridade + RAG) — comente se preferir volume
# RUN python scripts/build_all.py

EXPOSE 8000 8501
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
