# ── Stage 1: build React frontend ────────────────────────────────────────────
FROM node:20-slim AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js ./
COPY src/ ./src/
RUN npm run build

# ── Stage 2: Python backend + built frontend ──────────────────────────────────
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY calculate_real_time_risk.py ./
COPY ML/ ./ML/
COPY --from=frontend /app/dist ./dist

EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.server:app --host 0.0.0.0 --port ${PORT:-8000}"]
