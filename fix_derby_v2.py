# fix_derby_v2.py — Fix definitivo derby separado del portfolio v8.70
# Cambios:
# 1. registrar_posicion(): reto["carriles"] → derby["caballos"]
# 2. cerrar_posicion(): verificar capital_inicial > 0 antes de afectar caballo
# 3. /derby/activar: limpiar es_reto=False y carril_id=None en posiciones abiertas
# 4. Limpiar referencias viejas a "carriles" en /status y /derby/status
# 5. Limpiar posiciones activas NVDA CALL y AAPL CALL (es_reto=False, carril_id=None)
# 6. Version v8.70

import sys
import json

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

# ═══════════════════════════════════════════════════════
# CAMBIO 1 — registrar_posicion(): referencia vieja a reto/carriles
# ═══════════════════════════════════════════════════════
OLD_REG = '''    if es_reto and carril_id:
        for c in _portfolio["reto"]["carriles"]:
            if c["id"] == carril_id:
                c["posicion"] = pos["id"]
                c["ronda"]   += 1
                break'''

NEW_REG = '''    if es_reto and carril_id:
        for c in _portfolio["derby"]["caballos"]:
            if c["id"] == carril_id:
                c["posicion"] = pos["id"]
                c["ronda"]   += 1
                break'''

if OLD_REG not in content:
    errors.append("CAMBIO 1: bloque registrar_posicion reto/carriles no encontrado")
else:
    content = content.replace(OLD_REG, NEW_REG, 1)
    print("✅ Cambio 1: registrar_posicion() — reto/carriles → derby/caballos")

# ═══════════════════════════════════════════════════════
# CAMBIO 2 — cerrar_posicion(): verificar capital_inicial > 0
# ═══════════════════════════════════════════════════════
OLD_CERRAR = '''    if pos.get("es_reto") and pos.get("carril_id"):
        derby = _portfolio["derby"]
        for c in derby["caballos"]:
            if c["id"] == pos["carril_id"]:'''

NEW_CERRAR = '''    if pos.get("es_reto") and pos.get("carril_id"):
        derby = _portfolio["derby"]
        for c in derby["caballos"]:
            if c["id"] == pos["carril_id"] and c.get("capital_inicial", 0) > 0:'''

if OLD_CERRAR not in content:
    errors.append("CAMBIO 2: bloque cerrar_posicion no encontrado")
else:
    content = content.replace(OLD_CERRAR, NEW_CERRAR, 1)
    print("✅ Cambio 2: cerrar_posicion() — verificar capital_inicial > 0")

# ═══════════════════════════════════════════════════════
# CAMBIO 3 — /derby/activar: limpiar es_reto en posiciones abiertas
# ═══════════════════════════════════════════════════════
OLD_ACTIVAR = '''    derby["turno_actual"]     = 1
    # Resetear caballos
    for c in derby["caballos"]:'''

NEW_ACTIVAR = '''    derby["turno_actual"]     = 1
    # Limpiar posiciones abiertas del portfolio — desvinculadas del derby nuevo
    for pos in _portfolio["posiciones"]:
        if pos.get("estado") == "abierta":
            pos["es_reto"]   = False
            pos["carril_id"] = None
    # Resetear caballos
    for c in derby["caballos"]:'''

if OLD_ACTIVAR not in content:
    errors.append("CAMBIO 3: bloque derby/activar no encontrado")
else:
    content = content.replace(OLD_ACTIVAR, NEW_ACTIVAR, 1)
    print("✅ Cambio 3: /derby/activar — limpiar es_reto en posiciones abiertas")

# ═══════════════════════════════════════════════════════
# CAMBIO 4 — Limpiar referencias viejas carriles en /status y /derby/status
# ═══════════════════════════════════════════════════════
OLD_STATUS1 = '''    caballos_vivos = [c for c in derby.get("caballos", derby.get("carriles", [])) if not c.get("eliminado")]'''
NEW_STATUS1 = '''    caballos_vivos = [c for c in derby.get("caballos", []) if not c.get("eliminado")]'''

if OLD_STATUS1 not in content:
    errors.append("CAMBIO 4a: referencia derby/carriles en derby/status no encontrada")
else:
    content = content.replace(OLD_STATUS1, NEW_STATUS1, 1)
    print("✅ Cambio 4a: /derby/status — eliminar referencia vieja a carriles")

OLD_STATUS2 = '''        "carriles_vivos": len(caballos_vivos),'''
NEW_STATUS2 = '''        "caballos_vivos": len(caballos_vivos),'''

if OLD_STATUS2 not in content:
    errors.append("CAMBIO 4b: carriles_vivos en derby/status no encontrado")
else:
    content = content.replace(OLD_STATUS2, NEW_STATUS2, 1)
    print("✅ Cambio 4b: /derby/status — carriles_vivos → caballos_vivos")

OLD_STATUS3 = '''        cap_reto = sum(c["capital"] for c in reto.get("caballos", reto.get("carriles", [])) if not c.get("eliminado"))
        vivos  = sum(1 for c in reto.get("caballos", reto.get("carriles", [])) if not c.get("eliminado"))'''
NEW_STATUS3 = '''        cap_reto = sum(c["capital"] for c in reto.get("caballos", []) if not c.get("eliminado"))
        vivos  = sum(1 for c in reto.get("caballos", []) if not c.get("eliminado"))'''

if OLD_STATUS3 not in content:
    errors.append("CAMBIO 4c: referencias viejas en /status no encontradas")
else:
    content = content.replace(OLD_STATUS3, NEW_STATUS3, 1)
    print("✅ Cambio 4c: /status — eliminar referencias viejas a carriles")

# ═══════════════════════════════════════════════════════
# CAMBIO 5 — Version v8.70
# ═══════════════════════════════════════════════════════
content = content.replace('AXIS Breakout Sentinel v8.69', 'AXIS Breakout Sentinel v8.70')
content = content.replace('"sistema": "AXIS Breakout Sentinel v8.69"', '"sistema": "AXIS Breakout Sentinel v8.70"')
content = content.replace('print("AXIS Breakout Sentinel v8.69 iniciado...")', 'print("AXIS Breakout Sentinel v8.70 iniciado...")')
print("✅ Cambio 5: versión v8.70")

# ═══════════════════════════════════════════════════════
# VERIFICACION FINAL
# ═══════════════════════════════════════════════════════
if errors:
    print("\n❌ ERRORES:")
    for e in errors:
        print(f"  - {e}")
    print("\nNo se guardó el archivo.")
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("\n✅ server.py v8.70 guardado — derby separado del portfolio")
    print("   Siguiente: limpiar posiciones activas en axis_portfolio.json")
    print("   Luego: git add server.py && git commit -m 'fix: derby separado del portfolio v8.70' && git push origin main")

