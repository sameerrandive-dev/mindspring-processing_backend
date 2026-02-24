#!/bin/sh
# Startup script for Railway deployment
# Reads PORT from environment variable (Railway sets this automatically)

PORT=${PORT:-8000}
echo "Running database migrations..."
alembic upgrade head

echo "Starting application on port $PORT"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
