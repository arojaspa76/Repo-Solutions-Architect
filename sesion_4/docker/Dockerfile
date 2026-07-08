# =============================================================
# Dockerfile — LLM Gateway (Sesión 4)
# Multi-stage build: imagen más pequeña y segura
# =============================================================

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Solo copiar requirements primero (para cache de capas Docker)
COPY requirements.txt .

# Instalar deps en directorio separado (para copiar después)
RUN pip install --user --no-cache-dir -r requirements.txt

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Usuario no-root (buena práctica de seguridad)
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copiar solo los binarios instalados del builder
COPY --from=builder /root/.local /root/.local

# Copiar código de la aplicación
COPY ./app ./app

# Variables de entorno
ENV PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Cambiar a usuario no-root
USER appuser

# Servidor de producción con múltiples workers
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--log-level", "info"]
