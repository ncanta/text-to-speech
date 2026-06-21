#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
WEB_DIR="$ROOT_DIR/web"
BACKEND_PORT="${BACKEND_PORT:-8000}"
WEB_PORT="${WEB_PORT:-8080}"

if [[ ! -d "$BACKEND_DIR/venv" ]]; then
  echo "Backend virtual environment not found at $BACKEND_DIR/venv"
  echo "Run: cd backend && python3.10 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [[ -n "${WEB_PID:-}" ]]; then
    kill "$WEB_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

echo "Starting backend on http://localhost:${BACKEND_PORT}"
(
  cd "$BACKEND_DIR"
  source venv/bin/activate
  uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT"
) &
BACKEND_PID=$!

echo "Starting frontend on http://localhost:${WEB_PORT}"
(
  cd "$WEB_DIR"
  python3 -m http.server "$WEB_PORT"
) &
WEB_PID=$!

echo "Both services started. Press Ctrl+C to stop."
wait
