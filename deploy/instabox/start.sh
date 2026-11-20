#!/bin/bash
# (Re)start the backend and the static frontend. Uses systemd when the units are installed, else falls back to tmux.
cd ~/AI-Interview-Agent
if systemctl --user cat aura-backend >/dev/null 2>&1; then
  systemctl --user restart aura-backend aura-frontend
  echo "Restarted aura-backend and aura-frontend (systemd)."
else
  tmux kill-session -t backend 2>/dev/null || true
  tmux kill-session -t frontend 2>/dev/null || true
  tmux new -d -s backend  "cd ~/AI-Interview-Agent && source app/.venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips='*'"
  tmux new -d -s frontend "cd ~/AI-Interview-Agent/frontend && npx vite preview --host 0.0.0.0 --port 5173"
  echo "Started in tmux. Logs: tmux attach -t backend | tmux attach -t frontend"
fi
