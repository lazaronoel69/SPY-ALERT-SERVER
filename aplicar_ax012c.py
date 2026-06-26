import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

# PASO 1 -- reemplazar bloque GNA en V1 por llamada (ANTES de insertar
# la funcion nueva, para que el texto solo exista 1 vez en el archivo)
OLD_V1 = '        # GNA\n        if GNA_ON and v7_ayer and v_close > v_open and not ed["gna_fired"]:\n            gap_alza = (v_open - v7_ayer) / v7_ayer * 100\n            if gap_alza >= 0.1:\n                sma20 = calcular_sma(velas, 20)\n                sma40 = calcular_sma(velas, 40)\n                if sma20 and sma40 and sma20 > sma40:\n                    ed["gna_activo"] = True\n                    print(f"{simbolo} GNA activado — techo: ${v_close:.2f}")'

NEW_V1 = '        # GNA\n        evaluar_gna(simbolo, ed, velas, v_open, v_close, v_alcista, v7_ayer, None, hora_vela, True)'

if content.count(OLD_V1) != 1:
    errors.append(f'BLOQUE V1: se esperaba 1 coincidencia, se encontraron {content.count(OLD_V1)}')
else:
    content = content.replace(OLD_V1, NEW_V1, 1)
    print('Paso 1 OK: bloque GNA V1 reemplazado por llamada a evaluar_gna()')

# PASO 2 -- reemplazar bloque GNA en V2-V7 por llamada
OLD_V27 = '    # GNA\n    if GNA_ON and ed["gna_activo"] and not ed["gna_fired"] and v1_close:\n        if v_alcista and v_close > v1_close:\n            ed["gna_fired"]  = True\n            ed["gna_activo"] = False\n            guardar_estado_dia()\n            tipo = "GNA" if hora_vela == 10 else "GNA+2"\n            enviar_senal_con_botones(\n                simbolo, f"{tipo} — GAP NORMAL ALZA",\n                f"{hora_vela+1}:00 EST", v_close, "CALL",\n                f"<b>Techo V1:</b> ${v1_close:.2f} | <b>Cierre:</b> ${v_close:.2f}\\n"\n            )'

NEW_V27 = '    # GNA\n    evaluar_gna(simbolo, ed, velas, v_open, v_close, v_alcista, v7_ayer, v1_close, hora_vela, False)'

if content.count(OLD_V27) != 1:
    errors.append(f'BLOQUE V2-V7: se esperaba 1 coincidencia, se encontraron {content.count(OLD_V27)}')
else:
    content = content.replace(OLD_V27, NEW_V27, 1)
    print('Paso 2 OK: bloque GNA V2-V7 reemplazado por llamada a evaluar_gna()')

# PASO 3 -- insertar evaluar_gna() justo antes de evaluar_activo()
# (ahora el archivo ya NO tiene el texto original de los bloques,
# asi que insertar la funcion con ese mismo texto dentro no crea ambiguedad)
MARKER = 'def evaluar_activo(simbolo, velas, ahora):'
FUNC_DEF = 'def evaluar_gna(simbolo, ed, velas, v_open, v_close, v_alcista, v7_ayer, v1_close, hora_vela, es_v1):\n    """AX-012C: extraida de evaluar_activo() sin cambiar comportamiento.\n    Contiene EXACTAMENTE los 2 bloques de GNA que existian inline:\n    activacion en V1 (es_v1=True) y disparo en V2-V7 (es_v1=False).\n    Recibe explicitamente todas las variables necesarias -- no lee nada\n    implicito de un scope compartido."""\n    if es_v1:\n        # GNA\n        if GNA_ON and v7_ayer and v_close > v_open and not ed["gna_fired"]:\n            gap_alza = (v_open - v7_ayer) / v7_ayer * 100\n            if gap_alza >= 0.1:\n                sma20 = calcular_sma(velas, 20)\n                sma40 = calcular_sma(velas, 40)\n                if sma20 and sma40 and sma20 > sma40:\n                    ed["gna_activo"] = True\n                    print(f"{simbolo} GNA activado — techo: ${v_close:.2f}")\n    else:\n        # GNA\n        if GNA_ON and ed["gna_activo"] and not ed["gna_fired"] and v1_close:\n            if v_alcista and v_close > v1_close:\n                ed["gna_fired"]  = True\n                ed["gna_activo"] = False\n                guardar_estado_dia()\n                tipo = "GNA" if hora_vela == 10 else "GNA+2"\n                enviar_senal_con_botones(\n                    simbolo, f"{tipo} — GAP NORMAL ALZA",\n                    f"{hora_vela+1}:00 EST", v_close, "CALL",\n                    f"<b>Techo V1:</b> ${v1_close:.2f} | <b>Cierre:</b> ${v_close:.2f}\\n"\n                )'

if content.count(MARKER) != 1:
    errors.append(f'MARKER: se esperaba 1 coincidencia, se encontraron {content.count(MARKER)}')
else:
    content = content.replace(MARKER, FUNC_DEF + chr(10) + chr(10) + MARKER, 1)
    print('Paso 3 OK: evaluar_gna() insertada antes de evaluar_activo()')

if errors:
    print('ERRORES:')
    for e in errors:
        print('  - ' + e)
    sys.exit(1)
else:
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('server.py actualizado -- evaluar_gna() extraida correctamente')
