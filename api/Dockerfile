# WardWatch API - Production Dockerfile
# Uses distroless base for minimal attack surface
# Runs as non-root user (uid 65532 = nonroot in distroless)

# ─── Build stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install dependencies into a virtual environment
COPY requirements.txt .
RUN python -m venv /venv && \
    /venv/bin/pip install --upgrade pip && \
    /venv/bin/pip install --no-cache-dir -r requirements.txt

# ─── Runtime stage ───────────────────────────────────────────────────────────
FROM gcr.io/distroless/python3-debian12

# Copy virtualenv from builder
COPY --from=builder /venv /venv

# Copy application code
WORKDIR /app
COPY . .

# Run as non-root (distroless nonroot user uid=65532)
USER nonroot:nonroot

# Cloud Run expects port 8080
EXPOSE 8080

# Start the application
CMD ["/venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
