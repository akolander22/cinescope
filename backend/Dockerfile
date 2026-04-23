# ─────────────────────────────────────────────────────────────
# CineScope Backend — Dockerfile
# ─────────────────────────────────────────────────────────────
#
# LEARNING NOTE: Multi-stage builds keep the final image small.
# Stage 1 ("builder") installs dependencies into a virtual env.
# Stage 2 ("runtime") copies only what's needed to run the app.
# The build tools (gcc, pip, etc.) don't end up in your final image.
#
# To build manually:
#   docker build -t cinescope-backend .
#
# To run manually:
#   docker run -p 8000:8000 -v /mnt/user/appdata/cinescope:/data cinescope-backend

# ── Stage 1: Builder ─────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies needed to compile some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first — Docker caches this layer separately.
# If requirements.txt doesn't change, this layer is cached and pip
# install is skipped on rebuilds. Always copy requirements before code.
COPY requirements.txt .

# Install into an isolated virtual env inside the build stage
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Create a non-root user — running as root in a container is a security risk.
# Unraid runs containers as nobody/root by default; this is still good practice.
RUN useradd --create-home --shell /bin/bash cinescope

WORKDIR /app

# Copy the venv from builder (not the whole build layer, just the installed packages)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY app/ ./app/

# /data is where the SQLite database lives.
# We declare it as a VOLUME so Docker knows it should be persisted externally.
# On Unraid you'll map this to /mnt/user/appdata/cinescope/data
RUN mkdir -p /data && chown cinescope:cinescope /data
VOLUME ["/data"]

USER cinescope

# Expose the port uvicorn listens on
EXPOSE 8000

# LEARNING NOTE: We use uvicorn directly (not gunicorn) since this is a
# single-user personal app. --host 0.0.0.0 makes it accessible from outside
# the container (required). --workers 1 is fine for personal use.
# Remove --reload in production (it watches files for changes, wasteful in prod).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
