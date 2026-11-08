#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [ ! -f ".venv/bin/activate" ]; then
    echo "Erreur : environnement Python .venv introuvable."
    exit 1
fi

source .venv/bin/activate

echo "======================================"
echo "  Descent V2 — Assistant local"
echo "======================================"
echo
echo "Interface : http://127.0.0.1:8000"
echo "API       : http://127.0.0.1:8000/docs"
echo
echo "Arrêt du serveur : Ctrl+C"
echo

exec python -m uvicorn web_app:app \
    --host 127.0.0.1 \
    --port 8000
