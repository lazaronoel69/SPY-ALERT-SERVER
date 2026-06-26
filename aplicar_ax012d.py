import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

# PASO 1 -- reemplazar bloque GBA en V1 por llamada (ANTES de insertar
# la funcion nueva, para evitar texto duplicado durante la busqueda)
OLD_V1 = '        # GBA\n        if GBA_ON and v7_ayer and v_close > v_open and not ed["gba_fired"]:\n            gap_baja = (v7_ayer - v_open) / v7_ayer * 100\n            if gap_baja >= 0.1:\n                ed["gba_activo"] = True\n                print(f"{simbolo} GBA activado — techo: ${v_close:.2f}")'

NEW_V1 = '        # GBA\n        evaluar_gba(simbolo, ed, v_open, v_close, v_alcista, v7_ayer, None, hora_vela, True)'

if content.count(OLD_V1) != 1:
    errors.append(f'BLOQUE V1: se esperaba 1 coincidencia, se encontraron {content.count(OLD_V1)}')
else:
    content = content.replace(OLD_V1, NEW_V1, 1)
    print('Paso 1 OK: bloque GBA V1 reemplazado por llamada a evaluar_gba()')

# PASO 2 -- reemplazar bloque GBA en V2-V7 por llamada
OLD_V27 = '    # GBA\n    if GBA_ON and ed["gba_activo"] and not ed["gba_fired"] and v1_close:\n        if v_alcista and v_close > v1_close:\n            ed["gba_fired"]  = True\n            ed["gba_activo"] = False\n            guardar_estado_dia()\n            tipo = "GBA" if hora_vela == 10 else "GBA+2"\n            enviar_senal_con_botones(\n                simbolo, f"{tipo} — GAP BAJISTA ALZA",\n                f"{hora_vela+1}:00 EST", v_close, "CALL",\n                f"<b>Techo V1:</b> ${v1_close:.2f} | <b>Cierre:</b> ${v_close:.2f}\\n"\n            )'

NEW_V27 = '    # GBA\n    evaluar_gba(simbolo, ed, v_open, v_close, v_alcista, v7_ayer, v1_close, hora_vela, False)'

if content.count(OLD_V27) != 1:
    errors.append(f'BLOQUE V2-V7: se esperaba 1 coincidencia, se encontraron {content.count(OLD_V27)}')
else:
    content = content.replace(OLD_V27, NEW_V27, 1)
    print('Paso 2 OK: bloque GBA V2-V7 reemplazado por llamada a evaluar_gba()')

# PASO 3 -- insertar evaluar_gba() justo antes de evaluar_activo()
# (despues de evaluar_gna(), siguiendo lo pedido en el sprint:
# 'crear inmediatamente despues de evaluar_gna()')
MARKER = 'def evaluar_activo(simbolo, velas, ahora):'
FUNC_DEF = 'def evaluar_gba(simbolo, ed, v_open, v_close, v_alcista, v7_ayer, v1_close, hora_vela, es_v1):\n    """AX-012D: extraida de evaluar_activo() sin cambiar comportamiento.\n    Contiene EXACTAMENTE los 2 bloques de GBA que existian inline:\n    activacion en V1 (es_v1=True) y disparo en V2-V7 (es_v1=False).\n    Recibe explicitamente todas las variables necesarias -- no lee nada\n    implicito de un scope compartido."""\n    if es_v1:\n        # GBA\n        if GBA_ON and v7_ayer and v_close > v_open and not ed["gba_fired"]:\n            gap_baja = (v7_ayer - v_open) / v7_ayer * 100\n            if gap_baja >= 0.1:\n                ed["gba_activo"] = True\n                print(f"{simbolo} GBA activado — techo: ${v_close:.2f}")\n    else:\n        # GBA\n        if GBA_ON and ed["gba_activo"] and not ed["gba_fired"] and v1_close:\n            if v_alcista and v_close > v1_close:\n                ed["gba_fired"]  = True\n                ed["gba_activo"] = False\n                guardar_estado_dia()\n                tipo = "GBA" if hora_vela == 10 else "GBA+2"\n                enviar_senal_con_botones(\n                    simbolo, f"{tipo} — GAP BAJISTA ALZA",\n                    f"{hora_vela+1}:00 EST", v_close, "CALL",\n                    f"<b>Techo V1:</b> ${v1_close:.2f} | <b>Cierre:</b> ${v_close:.2f}\\n"\n                )'

if content.count(MARKER) != 1:
    errors.append(f'MARKER: se esperaba 1 coincidencia, se encontraron {content.count(MARKER)}')
else:
    content = content.replace(MARKER, FUNC_DEF + chr(10) + chr(10) + MARKER, 1)
    print('Paso 3 OK: evaluar_gba() insertada antes de evaluar_activo() (despues de evaluar_gna())')

if errors:
    print('ERRORES:')
    for e in errors:
        print('  - ' + e)
    sys.exit(1)
else:
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('server.py actualizado -- evaluar_gba() extraida correctamente')
