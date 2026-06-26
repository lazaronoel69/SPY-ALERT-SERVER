#!/bin/bash

echo "===== GIT STATUS ====="
git status

echo
echo "===== LAST 3 COMMITS ====="
git log --oneline -3

echo
echo "===== PY COMPILE ====="
python3 -m py_compile server.py
python3 -m py_compile axis_config.py axis_tradier.py axis_storage.py axis_telegram.py axis_orders.py axis_portfolio.py axis_channels.py axis_market.py 2>/dev/null
echo "PY_COMPILE_OK"

echo
echo "===== RAILWAY STATUS ====="
curl -s "https://web-production-bf9d0.up.railway.app/status?t=$(date +%s)" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('sistema')); print('Mercado:', d.get('mercado')); print('Posiciones:', d.get('portfolio',{}).get('posiciones_abiertas'))" 2>&1

echo
echo "===== ACTIVE DOC SUMMARY ====="
DOC="${1:-docs/AXIS-2.0/05-STRATEGY-ENGINE-DESIGN.md}"
echo "DOC: $DOC"
echo "--- HEAD ---"
head -60 "$DOC"
echo
echo "--- TAIL ---"
tail -60 "$DOC"
