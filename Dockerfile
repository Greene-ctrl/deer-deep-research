# Stage 1: Build the frontend
FROM node:22-slim AS frontend-builder
WORKDIR /app/frontend

# Install pnpm
RUN corepack enable && corepack install -g pnpm@10.26.2

# Copy package files
COPY frontend/package.json frontend/pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy frontend source
COPY frontend ./

# Build the frontend. NEXT_PUBLIC_API_URL should be /api for the proxy to work.
ENV NEXT_PUBLIC_API_URL=/api
RUN pnpm run build

# Stage 2: Final image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/user/.local/bin:$PATH" \
    DEER_FLOW_CONFIG_PATH="/home/user/app/config.yaml"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    nginx \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install pnpm
RUN corepack enable && corepack install -g pnpm@10.26.2

# Create a non-root user
RUN useradd -m -u 1000 user

# Prepare Nginx directories and permissions
RUN mkdir -p /var/cache/nginx /var/log/nginx /var/lib/nginx /run/nginx && \
    chown -R user:user /var/cache/nginx /var/log/nginx /var/lib/nginx /run/nginx

USER user
WORKDIR /home/user/app

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy backend
COPY --chown=user:user backend ./backend
# Install backend dependencies
RUN cd backend && uv sync

# Copy built frontend from Stage 1
COPY --from=frontend-builder --chown=user:user /app/frontend/.next ./frontend/.next
COPY --from=frontend-builder --chown=user:user /app/frontend/public ./frontend/public
COPY --from=frontend-builder --chown=user:user /app/frontend/package.json ./frontend/package.json
COPY --from=frontend-builder --chown=user:user /app/frontend/pnpm-lock.yaml ./frontend/pnpm-lock.yaml
COPY --from=frontend-builder --chown=user:user /app/frontend/next.config.js ./frontend/next.config.js

# Install production dependencies for frontend
RUN cd frontend && pnpm install --prod --frozen-lockfile

# Copy other necessary files
COPY --chown=user:user config.example.yaml ./config.yaml
COPY --chown=user:user .env.example ./.env
COPY --chown=user:user skills ./skills
COPY --chown=user:user scripts ./scripts
COPY --chown=user:user docker/nginx/nginx.hf.conf ./nginx.conf

# Create logs directory
RUN mkdir -p /home/user/app/logs

# HF Space port
EXPOSE 7860

# Make start script executable
RUN chmod +x ./scripts/start-hf.sh

CMD ["./scripts/start-hf.sh"]
