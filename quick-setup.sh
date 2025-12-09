#!/bin/bash
# Ultra-simple one-liner setup

echo "🚀 Setup Ultra-Simple"
cd backend && python3 -m pip install --upgrade pip -q 2>/dev/null && python3 -m pip install -r requirements.txt 2>/dev/null && python3 init_db.py --with-data 2>/dev/null && cd .. && npm install > /dev/null 2>&1 & echo "✅ Setup completado. Backend y frontend están listos." && echo "Ahora ejecuta:" && echo "  Terminal 1: ./start-backend.sh" && echo "  Terminal 2: ./start-frontend.sh"
