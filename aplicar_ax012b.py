import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD1 = 'def evaluar_activo(simbolo, velas, ahora):\n    hora = ahora.hour\n    ed   = estado_dia[simbolo]\n    c    = canal[simbolo]\n\n    vela_actual = None\n    for v in velas:\n        dt_v = datetime.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S")\n        if dt_v.hour == hora - 1:\n            vela_actual = v\n            break\n\n    if not vela_actual:\n        print(f"{simbolo}: no se encontro vela para hora {hora-1}")\n        return\n\n    v_open  = float(vela_actual["open"])\n    v_close = float(vela_actual["close"])\n    v_high  = float(vela_actual["high"])\n    v_low   = float(vela_actual["low"])\n    fecha_hoy = datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")'

NEW1 = 'def preparar_contexto_vela(simbolo, velas, ahora):\n    """AX-012B: extraida de evaluar_activo() sin cambiar comportamiento.\n    Localiza la vela correspondiente a la hora actual y extrae sus datos\n    basicos. Funcion pura -- no lee ni modifica estado_dia ni canal."""\n    hora = ahora.hour\n\n    vela_actual = None\n    for v in velas:\n        dt_v = datetime.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S")\n        if dt_v.hour == hora - 1:\n            vela_actual = v\n            break\n\n    if not vela_actual:\n        print(f"{simbolo}: no se encontro vela para hora {hora-1}")\n        return None\n\n    v_open  = float(vela_actual["open"])\n    v_close = float(vela_actual["close"])\n    v_high  = float(vela_actual["high"])\n    v_low   = float(vela_actual["low"])\n    fecha_hoy = datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")\n\n    return {\n        "hora":        hora,\n        "vela_actual": vela_actual,\n        "v_open":      v_open,\n        "v_close":     v_close,\n        "v_high":      v_high,\n        "v_low":       v_low,\n        "fecha_hoy":   fecha_hoy,\n    }\n\ndef evaluar_activo(simbolo, velas, ahora):\n    ed = estado_dia[simbolo]\n    c  = canal[simbolo]\n\n    ctx = preparar_contexto_vela(simbolo, velas, ahora)\n    if ctx is None:\n        return\n\n    hora        = ctx["hora"]\n    vela_actual = ctx["vela_actual"]\n    v_open      = ctx["v_open"]\n    v_close     = ctx["v_close"]\n    v_high      = ctx["v_high"]\n    v_low       = ctx["v_low"]\n    fecha_hoy   = ctx["fecha_hoy"]'

if content.count(OLD1) != 1:
    errors.append(f'Se esperaba 1 coincidencia, se encontraron {content.count(OLD1)}')
else:
    content = content.replace(OLD1, NEW1, 1)
    print('Cambio OK: preparar_contexto_vela() extraida, evaluar_activo() usa ctx')

if errors:
    print('ERRORES:')
    for e in errors:
        print('  - ' + e)
    sys.exit(1)
else:
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('server.py actualizado -- preparar_contexto_vela() creada')
