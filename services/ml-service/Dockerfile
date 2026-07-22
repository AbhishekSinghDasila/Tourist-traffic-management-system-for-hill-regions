# ---------- Builder stage ----------
FROM python:3.11-slim AS builder

WORKDIR /app

RUN pip config set global.timeout 120 && \
    pip config set global.retries 5

COPY requirements.txt .
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

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

COPY . .

# model_artifacts directory must be writable for training
RUN mkdir -p model_artifacts && \
    chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
