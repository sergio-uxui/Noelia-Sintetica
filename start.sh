#!/usr/bin/env bash
# start.sh — Arranca el dashboard de Noelia Sintética
# Detecta la IP local y muestra la URL para acceder desde el móvil.

set -e

PORT=${PORT:-8501}

# Detectar IP local (funciona en macOS y Linux)
if command -v ipconfig &> /dev/null; then
    # macOS
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "desconocida")
elif command -v hostname &> /dev/null; then
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "desconocida")
else
    LOCAL_IP="desconocida"
fi

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║         👗  Noelia Sintética — Dashboard         ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║                                                  ║"
echo "║  💻  Ordenador:  http://localhost:${PORT}           ║"
echo "║  📱  Móvil/red:  http://${LOCAL_IP}:${PORT}       ║"
echo "║                                                  ║"
echo "║  (asegúrate de que el móvil está en la misma     ║"
echo "║   WiFi que este ordenador)                       ║"
echo "║                                                  ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# Cargar .env si existe
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✅ Variables de entorno cargadas desde .env"
fi

echo "🚀 Iniciando Streamlit en el puerto ${PORT}…"
echo ""

streamlit run dashboard/app.py \
    --server.port "$PORT" \
    --server.address "0.0.0.0" \
    --server.headless true \
    --browser.serverAddress "$LOCAL_IP"
