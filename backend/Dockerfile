# Van Udyan Biodiversity Platform — backend container
#
# Image used for Render, Fly.io, Railway or any Docker host. Installs Tesseract so the printed
# GPS Map Camera stamp can be read even without Windows OCR (winsdk is Windows-only and skipped
# on Linux via the sys_platform marker in requirements.txt).

FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System packages:
#   libgl1 / libglib2.0-0 — Pillow for image orientation and thumbnails
#   tesseract-ocr          — OCR fallback for reading printed location stamps on photos
#   curl                   — healthcheck tool
#   gdal-bin, libgeos-dev — Shapely / GeoAlchemy2 geometry helpers
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      tesseract-ocr \
      libgl1 \
      libglib2.0-0 \
      libgeos-dev \
      curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (better Docker layer caching)
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt

# Then the application code and the reference data the backend reads at runtime
COPY backend /app/backend
COPY data /app/data

# Writable mount points (bind a persistent volume here on hosts that support it;
# otherwise the Supabase Storage backend handles persistence instead).
RUN mkdir -p /app/data/uploads /app/data/uploads_thumbs /app/logs

ENV UPLOADS_DIR=/app/data/uploads \
    THUMBS_DIR=/app/data/uploads_thumbs \
    PORT=8000

# Run as an unprivileged user. Only grant write access where the application
# actually writes (uploads, thumbnails, logs); the rest of /app stays read-only
# as far as the runtime is concerned.
RUN groupadd --system --gid 1001 vanudyan \
 && useradd --system --uid 1001 --gid 1001 --home-dir /app --shell /usr/sbin/nologin vanudyan \
 && chown -R vanudyan:vanudyan /app/data/uploads /app/data/uploads_thumbs /app/logs
USER vanudyan

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://localhost:${PORT}/ready" || exit 1

# Use shell form so ${PORT} is expanded (Render / Railway set PORT dynamically)
CMD exec uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port ${PORT}
