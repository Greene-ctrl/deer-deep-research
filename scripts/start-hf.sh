#!/bin/bash
set -e

# Initialize config files if they don't exist
if [ ! -f config.yaml ]; then
    echo "Creating config.yaml from example..."
    cp config.example.yaml config.yaml
fi

if [ ! -f .env ]; then
    echo "Creating .env from example..."
    cp .env.example .env
fi

# Ensure logs directory exists
mkdir -p logs

# Start LangGraph server
echo "Starting LangGraph server..."
cd backend && /home/user/.local/bin/uv run langgraph dev --no-browser --allow-blocking --host 0.0.0.0 --port 2024 > ../logs/langgraph.log 2>&1 &
cd ..

# Start Gateway API
echo "Starting Gateway API..."
cd backend && /home/user/.local/bin/uv run uvicorn src.gateway.app:app --host 0.0.0.0 --port 8001 > ../logs/gateway.log 2>&1 &
cd ..

# Start Frontend
echo "Starting Frontend..."
cd frontend && pnpm run start -- -p 3000 > ../logs/frontend.log 2>&1 &
cd ..

# Wait for services to start
echo "Waiting for services to initialize..."
sleep 5

# Start Nginx in the foreground
echo "Starting Nginx on port 7860..."
nginx -c /home/user/app/nginx.conf -g 'daemon off;'
