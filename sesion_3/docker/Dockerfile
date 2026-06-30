# ============================================================
# Dockerfile — LLM Gateway API
# Sesión 3: Kubernetes, Docker y Contenedores para LLMs
# BSG Institute
# ============================================================
#
# CONCEPTOS CLAVE de este Dockerfile:
#
# 1. Multi-stage build: reduce el tamaño de la imagen final
#    - Stage 1 (builder): instala dependencias
#    - Stage 2 (runtime): solo copia lo necesario para correr
#
# 2. Non-root user: seguridad — el proceso no corre como root
#
# 3. Layer caching: requirements.txt antes del código para
#    aprovechar el cache de Docker en rebuilds
#
# 4. Health check: Docker verifica periódicamente si el
#    contenedor está saludable
#
# Comandos:
#   docker build -t llm-gateway:latest .
#   docker run -p 8000:8000 --env-file .env llm-gateway:latest
# ============================================================

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
# Usamos una imagen con pip para instalar dependencias
FROM python:3.11-slim AS builder

# Evitar que Python escriba archivos .pyc
ENV PYTHONDONTWRITEBYTECODE=1
# No usar buffer para stdout/stderr (logs en tiempo real)
ENV PYTHONUNBUFFERED=1

WORKDIR /build

# Instalar dependencias del sistema necesarias para compilar paquetes
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# IMPORTANTE: copiar requirements ANTES del código
# Esto permite que Docker reutilice el cache si el código cambia
# pero los requirements no cambiaron
COPY requirements.txt .

# Instalar en directorio específico para copiar al stage final
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --target=/install -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
# Imagen mínima para producción — solo lo necesario para ejecutar
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV ENVIRONMENT=production

WORKDIR /app

# Instalar solo runtime (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias instaladas desde el stage builder
COPY --from=builder /install /usr/local/lib/python3.11/site-packages

# Crear usuario no-root (seguridad)
RUN useradd --create-home --shell /bin/bash appuser

# Copiar código de la aplicación
COPY app/ ./app/

# Cambiar ownership al usuario de la app
RUN chown -R appuser:appuser /app

# Cambiar al usuario no-root
USER appuser

# Exponer el puerto de la aplicación
EXPOSE 8000

# Health check: Docker verifica cada 30s si la app responde
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicio
# --host 0.0.0.0: escuchar en todas las interfaces (requerido en Docker)
# --workers 1: un worker por contenedor (Kubernetes escala con réplicas)
# --access-log: log de cada request para debugging
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--access-log"]
