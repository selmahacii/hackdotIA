#!/usr/bin/env bash
set -e

echo "=== Guardia Backend Initializing on Hugging Face Spaces ==="

# Check if an external DATABASE_URL is provided, else start embedded PostgreSQL
if [ -z "$DATABASE_URL" ] || [[ "$DATABASE_URL" == *"localhost"* ]]; then
    echo "Starting local PostgreSQL instance in container..."
    service postgresql start || /etc/init.d/postgresql start
    
    # Configure user and database if not already created
    su - postgres -c "psql -tc \"SELECT 1 FROM pg_user WHERE usename = 'elderly'\" | grep -q 1 || psql -c \"CREATE USER elderly WITH SUPERUSER PASSWORD 'elderly';\"" || true
    su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname = 'elderly'\" | grep -q 1 || psql -c \"CREATE DATABASE elderly OWNER elderly;\"" || true
    
    export DATABASE_URL="postgresql+asyncpg://elderly:elderly@127.0.0.1:5432/elderly"
    echo "Embedded PostgreSQL configured at: $DATABASE_URL"
fi

# Run database migrations to head
echo "Applying database schema migrations..."
python -m alembic upgrade head

# Seed initial RBAC users, residents, and devices
echo "Seeding RBAC profiles and demonstration data..."
python -m scripts.seed_db

# Start FastAPI Uvicorn on Hugging Face port 7860
echo "Starting Guardia FastAPI on 0.0.0.0:7860..."
exec uvicorn app.main:app --host 0.0.0.0 --port 7860
