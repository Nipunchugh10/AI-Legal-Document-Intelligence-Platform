#!/bin/sh
set -e

echo "[+] ==================================================="
echo "[+] Legal AI Document Intelligence Platform — Starting"
echo "[+] ==================================================="

# Wait for PostgreSQL to be ready
echo "[+] Waiting for PostgreSQL database connection..."
python3 -c "
import time
import psycopg2
import os
from urllib.parse import urlparse

db_url = os.environ.get('DATABASE_URL', '')
if db_url:
    # Handle both postgresql:// and postgres:// prefixes
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    result = urlparse(db_url)
    username = result.username or 'postgres'
    password = result.password or 'postgres'
    database = result.path[1:] if len(result.path) > 1 else 'legal_ai_db'
    hostname = result.hostname or 'postgres'
    port = result.port or 5432

    connected = False
    for i in range(30):
        try:
            conn = psycopg2.connect(
                dbname=database,
                user=username,
                password=password,
                host=hostname,
                port=port,
                connect_timeout=3
            )
            conn.close()
            connected = True
            print(f'[+] PostgreSQL connected successfully at {hostname}:{port}/{database}')
            break
        except Exception as e:
            print(f'[-] DB waiting (attempt {i+1}/30): {e}')
            time.sleep(1)

    if not connected:
        print('[-] ERROR: Could not connect to PostgreSQL within 30 seconds.')
        exit(1)
else:
    print('[-] WARNING: DATABASE_URL is not set. Skipping DB readiness check.')
"

# Run database migrations
echo "[+] Applying database migrations (alembic upgrade head)..."
alembic upgrade head
echo "[+] Migrations applied successfully."

# Start backend application process
echo "[+] Starting application server: $@"
exec "$@"
