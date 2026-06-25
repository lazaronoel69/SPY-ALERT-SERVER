import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD = 'HORAS_REPORTE    = [10, 11, 12, 13, 14, 15, 16]'
NEW = 'HORAS_REPORTE    = [10, 11, 12, 13, 14, 15]\n# v8.84: hora 16 (4:00 PM / V7) eliminada de aqui -- V7 se evalua\n# EXCLUSIVAMENTE a las 3:58 PM via loop_v7_anticipada() con la vela\n# provisional. monitor_loop ya NO vuelve a evaluar V7 a las 4:01 PM,\n# evitando alertas duplicadas/falsas (caso GOOG RPG falso 06/25).'

if content.count(OLD) != 1:
    errors.append(f"Se esperaba 1 coincidencia exacta de HORAS_REPORTE, se encontraron {content.count(OLD)}")
else:
    content = content.replace(OLD, NEW, 1)
    print("Cambio OK: hora 16 eliminada de HORAS_REPORTE -- V7 solo se evalua a las 3:58 PM")

content = content.replace("AXIS Breakout Sentinel v8.83", "AXIS Breakout Sentinel v8.84")
print("Version v8.84")

if errors:
    print("ERRORES:")
    for e in errors:
        print("  - " + e)
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("server.py v8.84 guardado")
