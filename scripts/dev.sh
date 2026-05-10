#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

cleanup() {
  echo ""
  echo "Stopping dev servers..."
  kill $BE_PID $FE_PID 2>/dev/null
  wait $BE_PID $FE_PID 2>/dev/null
  echo "Done."
}
trap cleanup EXIT INT TERM

echo "Starting backend on :${BACKEND_PORT} ..."
cd "$ROOT/src/backend"
uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload &
BE_PID=$!

echo "Starting frontend on :${FRONTEND_PORT} ..."
cd "$ROOT/src/frontend"
npx vite --port "$FRONTEND_PORT" --host 0.0.0.0 &
FE_PID=$!

echo ""
echo "==================================="
echo "  Backend:  http://localhost:${BACKEND_PORT}"
echo "  Frontend: http://localhost:${FRONTEND_PORT}"
echo "  Press Ctrl+C to stop both."
echo "==================================="
echo ""

wait
