#!/bin/bash
set -e

echo "=================================================="
echo " AI Legal Document Intelligence Platform          "
echo " Hugging Face Spaces Production Unified Runtime   "
echo "=================================================="
echo "[*] Current User UID: $(id -u 2>/dev/null || echo 1000) (Hugging Face non-root: 1000)"
echo "[*] Listening Port  : ${PORT:-7860}"
echo "[*] Environment     : ${APP_ENV:-production}"

cd /app/backend

# Ensure persistent runtime directories exist
mkdir -p uploads chroma_data /app/uploads /app/chroma_data

# Execute cloud database verification & migrations if DATABASE_URL is configured
if [ -n "$DATABASE_URL" ]; then
    echo "[*] Verifying cloud database and executing Alembic migrations..."
    if [ -f "scripts/verify_cloud_db.py" ]; then
        python scripts/verify_cloud_db.py --apply-migrations || alembic upgrade head || echo "[!] Migration warning: continuing startup."
    else
        alembic upgrade head || echo "[!] Migration warning: continuing startup."
    fi
else
    echo "[!] Notice: DATABASE_URL is not set. Persistent database features will require DATABASE_URL configured in Spaces Secrets."
fi

echo "[*] Launching Uvicorn production server on 0.0.0.0:${PORT:-7860}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-7860}" --workers 1 --proxy-headers --forwarded-allow-ips='*'

