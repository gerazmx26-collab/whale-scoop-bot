#!/bin/bash

# Configuración de Rutas
PROJECT_DIR="/Users/gerardo/.gemini/antigravity/scratch/whale-tracker"
WHALE_SCOOP_DIR="/Users/gerardo/whale-scoop-bot"
NODE_BIN="/tmp/node-v20.11.1-darwin-x64/bin"
export PATH="$NODE_BIN:$PATH"
export PYTHONPATH="$PROJECT_DIR/backend:$PYTHONPATH"

echo "--------------------------------------------------"
echo "🐳 SISTEMA UNIFICADO DE RASTREO DE BALLENAS"
echo "--------------------------------------------------"

# 1. Iniciar Backend (FastAPI)
echo "🚀 Iniciando Backend (FastAPI)..."
cd "$PROJECT_DIR"
nohup uvicorn backend.main:app --port 8000 --log-level warning > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

# 2. Iniciar Frontend (Dashboard)
echo "🎨 Iniciando Dashboard..."
cd "$PROJECT_DIR/frontend"
npm run dev -- -p 3001 &
FRONTEND_PID=$!

# 3. Iniciar Whale Scoop Bot (Python)
echo "🐠 Iniciando Whale Scoop Bot (Paper Trading)..."
cd "$WHALE_SCOOP_DIR"
python3 main.py > /tmp/whale_scoop.log 2>&1 &
BOT_PID=$!

# 4. Abrir Navegador
echo "⌛ Esperando a que los servicios estén listos..."
sleep 10
open http://localhost:3001

echo "--------------------------------------------------"
echo "✅ Sistema corriendo"
echo "   Backend API: http://localhost:8000"
echo "   Dashboard:  http://localhost:3001"
echo "   Whale Scoop: Modo papel"
echo "Presiona Ctrl+C para cerrar."
echo "--------------------------------------------------"

# Limpieza al cerrar
trap "kill $BACKEND_PID $FRONTEND_PID $BOT_PID 2>/dev/null; echo 'Saliendo...'; exit" INT TERM
wait