import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD1 = '    # RPG — dispara siempre con ruptura del piso (v8.77).\n    # Condicion adicional (RCB 30% o SMA20>SMA40) solo decide el label RPG vs RPG+,\n    # nunca bloquea el disparo. Mismo patron que el fix de 1VR en v8.63.\n    if RPG_ON and ed["rpg_activo"] and not ed["rpg_fired"] and ed["rpg_piso"]:\n        if v_close < ed["rpg_piso"]:\n            ahora_dt_rpg = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))\n            techo_rpg    = calcular_techo_canal(simbolo, ahora_dt_rpg)\n            _, mitad_rpg = calcular_piso_mitad_canal(simbolo, ahora_dt_rpg)\n            c_rpg        = canal[simbolo]\n            zona_30_rpg = None\n            if techo_rpg and mitad_rpg:\n                zona_30_rpg = techo_rpg - (techo_rpg - mitad_rpg) * 0.30\n            en_rcb_30_rpg = (\n                c_rpg["on"] and not c_rpg["apagado"] and c_rpg["p3"] is not None\n                and techo_rpg is not None and zona_30_rpg is not None\n                and zona_30_rpg <= v_close <= techo_rpg\n            )\n            s20_rpg = ed.get("rpg_s20")\n            s40_rpg = ed.get("rpg_s40")\n            sma20_gt_sma40 = s20_rpg and s40_rpg and s20_rpg > s40_rpg\n            ed["rpg_fired"]  = True\n            ed["rpg_activo"] = False\n            guardar_estado_dia()\n            label_rpg = "RPG+" if (en_rcb_30_rpg or sma20_gt_sma40) else "RPG"\n            if en_rcb_30_rpg:\n                extra_rpg = f"<b>Canal RCB:</b> Techo ${techo_rpg:.2f} | Zona 30%: ${zona_30_rpg:.2f}\\n"\n            elif sma20_gt_sma40:\n                extra_rpg = f"<b>SMA20:</b> ${s20_rpg:.2f} > <b>SMA40:</b> ${s40_rpg:.2f}\\n"\n            else:\n                extra_rpg = ""\n            enviar_senal_con_botones(\n                simbolo, f"{label_rpg} — RUPTURA PISO GAP",\n                f"{hora_vela+1}:00 EST", v_close, "PUT",\n                f"<b>Piso V1:</b> ${ed[\'rpg_piso\']:.2f} | <b>Cierre:</b> ${v_close:.2f}\\n{extra_rpg}"\n            )'

NEW1 = '    # RPG\n    evaluar_rpg_disparo(simbolo, ed, vela_actual, v_close, hora_vela)'

if content.count(OLD1) != 1:
    errors.append(f'Se esperaba 1 coincidencia, se encontraron {content.count(OLD1)}')
else:
    content = content.replace(OLD1, NEW1, 1)
    print('FIX OK: bloque RPG V2-V7 reemplazado por llamada a evaluar_rpg_disparo()')

if errors:
    print('ERRORES:')
    for e in errors:
        print('  - ' + e)
    sys.exit(1)
else:
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('server.py reparado -- AX-012E completado correctamente')
