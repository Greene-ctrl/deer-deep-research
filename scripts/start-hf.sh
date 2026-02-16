#!/bin/bash
set -e

APP_ROOT="/home/user/app"

echo "Listing files in APP_ROOT:"
ls -F "${APP_ROOT}"

# Initialize config files if they don't exist
if [ ! -f "${APP_ROOT}/config.yaml" ]; then
    echo "Creating config.yaml from example..."
    cp "${APP_ROOT}/config.example.yaml" "${APP_ROOT}/config.yaml"
fi

if [ ! -f "${APP_ROOT}/.env" ]; then
    echo "Creating .env from example..."
    cp "${APP_ROOT}/.env.example" "${APP_ROOT}/.env"
fi

# Ensure logs directory exists
mkdir -p "${APP_ROOT}/logs"

# Start LangGraph server
echo "Starting LangGraph server..."
cd "${APP_ROOT}/backend" && /home/user/.local/bin/uv run langgraph dev --no-browser --allow-blocking --host 127.0.0.1 --port 2024 > "${APP_ROOT}/logs/langgraph.log" 2>&1 &

# Start Gateway API
echo "Starting Gateway API..."
cd "${APP_ROOT}/backend" && /home/user/.local/bin/uv run uvicorn src.gateway.app:app --host 127.0.0.1 --port 8001 > "${APP_ROOT}/logs/gateway.log" 2>&1 &

# Start Frontend
echo "Starting Frontend..."
cd "${APP_ROOT}/frontend"
# Use npx next start directly to avoid pnpm argument passing issues
npx next start -p 3000 -H 127.0.0.1 > "${APP_ROOT}/logs/frontend.log" 2>&1 &

# Wait for services to start with a health check loop
echo "Waiting for services to initialize..."
for i in {1..60}; do
    GW_UP=0
    FE_UP=0
    curl -s http://127.0.0.1:8001/health > /dev/null && GW_UP=1
    curl -s http://127.0.0.1:3000 > /dev/null && FE_UP=1

    if [ $GW_UP -eq 1 ] && [ $FE_UP -eq 1 ]; then
        echo "Services are up!"
        break
    fi
    echo "Waiting for services... GW=$GW_UP, FE=$FE_UP ($i/60)"
    if [ $i -gt 20 ] && [ $FE_UP -eq 0 ]; then
        echo "Frontend log tail (last 10 lines):"
        tail -n 10 "${APP_ROOT}/logs/frontend.log"
    fi
    sleep 2
done

# Tail logs in background
tail -f "${APP_ROOT}/logs/gateway.log" "${APP_ROOT}/logs/frontend.log" "${APP_ROOT}/logs/langgraph.log" &

# Start Nginx in the foreground
echo "Starting Nginx on port 7860..."
nginx -c "${APP_ROOT}/nginx.conf" -g 'daemon off;'
