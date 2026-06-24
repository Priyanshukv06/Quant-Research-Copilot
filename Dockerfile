# Dockerfile for Unified Free Deployment on Render
# ------------------------------------------------
# STAGE 1: Build Next.js Frontend
# ------------------------------------------------
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Install dependencies
COPY frontend/package*.json ./
RUN npm install

# Build static export (output: 'export' in next.config.ts)
COPY frontend/ ./
# We set NODE_ENV to production so api.ts uses relative routing '/api/copilot'
ENV NODE_ENV=production
RUN npm run build

# ------------------------------------------------
# STAGE 2: Setup FastAPI Backend
# ------------------------------------------------
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies required for data science packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source code
COPY backend/ ./backend/

# Copy the built frontend from STAGE 1 into /app/frontend/out
# FastAPI's StaticFiles is configured to look exactly here!
COPY --from=frontend-builder /app/frontend/out /app/frontend/out

# Expose port (Render sets $PORT automatically, but defaults to 8000)
ENV PORT=8000
EXPOSE 8000

# Start Uvicorn pointing to the backend directory
WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
