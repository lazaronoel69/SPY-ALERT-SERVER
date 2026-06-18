# remove_comparar.py — Elimina el endpoint temporal /comparar_strikes
# Corre desde: /Users/noellazaro/SPY-ALERT-SERVER/

import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

start_marker = '@app.route("/comparar_strikes", methods=["GET"])'
end_marker = 'def buscar_opcion_reto(opcion_original, presupuesto):'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    errors.append("No se encontraron los marcadores del endpoint temporal")
else:
    content = content[:start_idx] + content[end_idx:]
    print("Endpoint /comparar_strikes eliminado")

if errors:
    print("ERRORES:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("server.py limpio - endpoint temporal eliminado")
    print("git add server.py && git commit -m 'cleanup: eliminar endpoint temporal comparar_strikes' && git push origin main")
