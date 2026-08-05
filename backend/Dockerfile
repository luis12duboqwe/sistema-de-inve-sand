# Production-ready FastAPI image
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --upgrade \
        pip \
        setuptools==83.0.0 \
        wheel==0.47.0 \
    && python -m pip install --no-cache-dir -r requirements.txt \
    # pip solo se necesita para construir el entorno. No debe viajar en la imagen final:
    # sus dependencias vendorizadas amplían innecesariamente la superficie de ataque.
    && rm -rf \
        /opt/venv/lib/python3.11/site-packages/pip \
        /opt/venv/lib/python3.11/site-packages/pip-*.dist-info \
        /opt/venv/bin/pip \
        /opt/venv/bin/pip3 \
        /opt/venv/bin/pip3.11

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    # El Python global de la imagen base incluye pip únicamente para instalar paquetes.
    # La aplicación usa /opt/venv y no necesita un instalador en producción.
    && rm -rf \
        /usr/local/lib/python3.11/site-packages/pip \
        /usr/local/lib/python3.11/site-packages/pip-*.dist-info \
        /usr/local/bin/pip \
        /usr/local/bin/pip3 \
        /usr/local/bin/pip3.11

COPY --from=builder /opt/venv /opt/venv
COPY . .

RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && mkdir -p /app/uploads /app/logs /app/backups \
    && chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/ready || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
