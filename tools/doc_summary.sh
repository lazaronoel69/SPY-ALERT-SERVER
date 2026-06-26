#!/bin/bash
# AX-INF-001 — doc_summary.sh
# Uso: ./tools/doc_summary.sh docs/AXIS-2.0/10-HANDOFF.md
# Resumen rapido de un documento + estado de git. Copia todo al clipboard.

if [ -z "$1" ]; then
  echo "Uso: $0 <ruta-del-documento>"
  exit 1
fi

DOC="$1"

if [ ! -f "$DOC" ]; then
  echo "Archivo no encontrado: $DOC"
  exit 1
fi

OUT=$(mktemp)

{
  echo "=== git status ==="
  git status
  echo ""
  echo "=== git log --oneline -1 ==="
  git log --oneline -1
  echo ""
  echo "=== HEAD -80 de $DOC ==="
  head -80 "$DOC"
  echo ""
  echo "=== TAIL -80 de $DOC ==="
  tail -80 "$DOC"
} > "$OUT" 2>&1

cat "$OUT"
pbcopy < "$OUT"
rm -f "$OUT"

echo ""
echo "REPORT COPIED TO CLIPBOARD — paste with ⌘+V"
