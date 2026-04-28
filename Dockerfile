# ─────────────────────────────────────────────────────────────
# CineScope — Dockerfile (Backend + Frontend, single container)
# ─────────────────────────────────────────────────────────────

# ── Stage 1: Build frontend ───────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /frontend

# Install deps first (cache layer)
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

# Copy source and build
COPY frontend/ ./
RUN npm run build
# Output is in /frontend/dist


# ── Stage 2: Build Python deps ────────────────────────────────
FROM python:3.12-slim AS backend-builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt


# ── Stage 3: Runtime ──────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Python venv from stage 2
COPY --from=backend-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Backend source
COPY backend/app/ ./app/

# Frontend build output — FastAPI will serve this as static files
COPY --from=frontend-builder /frontend/dist ./static/

RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
