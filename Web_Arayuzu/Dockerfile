FROM python:3.11-slim

ARG REQUIREMENTS_FILE=requirements-ocr.txt

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AYEC_HOST=0.0.0.0 \
    AYEC_PORT=8501 \
    AYEC_DB_PATH=/data/ayecpro.db \
    AYEC_TENANT_DIR=/data/Kullanıcılar \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl \
       fonts-dejavu-core \
       libgomp1 \
       tesseract-ocr \
       tesseract-ocr-eng \
       tesseract-ocr-tur \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-ocr.txt requirements-paddle.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir --requirement "$REQUIREMENTS_FILE"

COPY . .
RUN mkdir -p /data /data/Kullanıcılar /app/web/uploads \
    && python tools/verify_runtime.py --require-ocr

VOLUME ["/data", "/app/web/uploads"]
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/api/desktop/health', timeout=3).read()"

CMD ["python", "Main.py", "--host", "0.0.0.0", "--port", "8501", "--db", "/data/ayecpro.db"]
