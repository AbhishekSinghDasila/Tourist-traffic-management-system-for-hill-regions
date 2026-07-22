# ---------- Builder stage ----------
FROM python:3.11-slim AS builder

WORKDIR /app

RUN pip config set global.timeout 180 && \
    pip config set global.retries 5

COPY requirements.txt .

# EasyOCR downloads model weights on first use (~100MB).
# torch is a heavy dependency — this stage takes 3-5 minutes.
RUN pip install --no-cache-dir --user \
    --index-url https://pypi.org/simple/ \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    -r requirements.txt

# ---------- Final stage ----------
FROM python:3.11-slim

RUN useradd -m -u 1001 appuser

WORKDIR /app

# System deps needed by EasyOCR (OpenCV) and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# EasyOCR model cache directory — writable by appuser
RUN mkdir -p /home/appuser/.EasyOCR && \
    chown -R appuser:appuser /home/appuser/.EasyOCR

COPY . .
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
