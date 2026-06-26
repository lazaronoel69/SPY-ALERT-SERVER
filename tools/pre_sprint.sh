#!/bin/bash
# AX-INF-001 — pre_sprint.sh
# Verificacion inicial antes de empezar un sprint. Copia todo al clipboard.

OUT=$(mktemp)

{
  echo "=== git pull ==="
  git pull
  echo ""
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
  fi
} > "$OUT" 2>&1

cat "$OUT"
pbcopy < "$OUT"
rm -f "$OUT"

echo ""
echo "REPORT COPIED TO CLIPBOARD — paste with ⌘+V"
