#!/bin/bash
# AX-INF-001 — chatgpt_report.sh
# Reporte completo de estado para pegar en ChatGPT/Claude. Copia todo al clipboard.

OUT=$(mktemp)

{
  echo "=== git status ==="
  git status
  echo ""
  echo "=== git log --oneline -3 ==="
  git log --oneline -3
  echo ""
  echo "=== python3 -m py_compile server.py ==="
  python3 -m py_compile server.py && echo "OK"
  echo ""
  if ls axis_*.py >/dev/null 2>&1; then
    for f in axis_*.py; do
      echo "=== python3 -m py_compile $f ==="
      python3 -m py_compile "$f" && echo "OK"
      echo ""
    done
  else
    echo "(sin archivos axis_*.py en este directorio)"
    echo ""
  fi
  echo "=== curl /status Railway ==="
  curl -s "https://web-production-bf9d0.up.railway.app/status?t=$(date +%s)"
  echo ""
  echo ""
  echo "=== git show --stat --oneline HEAD ==="
  GIT_PAGER=cat git show --stat --oneline HEAD
  echo ""
  echo "=== git show del ultimo commit (server.py) ==="
  GIT_PAGER=cat git show HEAD -- server.py
  echo ""
  echo "=== git show del ultimo commit (docs/AXIS-2.0/10-HANDOFF.md) ==="
  GIT_PAGER=cat git show HEAD -- docs/AXIS-2.0/10-HANDOFF.md
} > "$OUT" 2>&1

cat "$OUT"
pbcopy < "$OUT"
rm -f "$OUT"

echo ""
echo "REPORT COPIED TO CLIPBOARD — paste with ⌘+V"
