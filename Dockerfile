# ==============================================================================
# AI Legal Document Intelligence Platform
# Production Multi-Stage Dockerfile for Hugging Face Spaces (Docker SDK)
# ==============================================================================

# --- Stage 1: Build React 19 / TypeScript Frontend ---
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# --- Stage 2: Production Python 3.11 Runtime ---
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860 \
    APP_ENV=production \
    DEBUG=false \
    PYTHONPATH=/app/backend

# Install essential system dependencies (libpq for PostgreSQL, curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create Hugging Face default non-root user (UID 1000)
RUN useradd -m -u 1000 user

WORKDIR /app

# Install Python backend dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend application source code
COPY backend /app/backend

# Copy compiled frontend distribution from builder stage
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Copy Hugging Face startup entrypoint
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Create runtime directories and set ownership for user 1000
RUN mkdir -p /app/backend/uploads /app/backend/chroma_data /app/uploads /app/chroma_data && \
    chown -R user:user /app

# Switch to Hugging Face non-root user
USER user

# Hugging Face Spaces exposes port 7860
EXPOSE 7860

CMD ["/app/start.sh"]
