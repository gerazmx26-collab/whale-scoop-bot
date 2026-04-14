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
nohup uvicorn backend.main:app --port 8000 --log-level error > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
sleep 5

# 2. Verificar que Backend esté listo
echo "⌛ Verificando Backend..."
until curl -s http://localhost:8000/health | grep -q "healthy"; do
    sleep 2
done

# 3. Iniciar Frontend (Dashboard)
echo "🎨 Iniciando Dashboard..."
cd "$PROJECT_DIR/frontend"
npm run dev -- -p 3001 > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!

# 4. Iniciar Whale Scoop Bot (Python - Modo Demo)
echo "🐠 Iniciando Whale Scoop Bot..."
cd "$WHALE_SCOOP_DIR"
python3 main.py > /tmp/whale_scoop.log 2>&1 &
BOT_PID=$!

# 5. Abrir Navegador
sleep 5
open http://localhost:3001

echo "--------------------------------------------------"
echo "✅ Sistema corriendo"
echo "   Backend API:  http://localhost:8000"
echo "   Dashboard:   http://localhost:3001"
echo "   Whale Scoop: Modo DEMO (cuenta papel)"
echo ""
echo "   Logs:"
echo "   - Backend:  tail -f /tmp/backend.log"
echo "   - Frontend: tail -f /tmp/frontend.log"
echo "   - Bot:      tail -f /tmp/whale_scoop.log"
echo "--------------------------------------------------"

# Cleanup
trap "kill $BACKEND_PID $FRONTEND_PID $BOT_PID 2>/dev/null; echo 'Saliendo...'; exit" INT TERM
wait