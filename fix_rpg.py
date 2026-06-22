# fix_rpg.py — RPG dispara siempre con ruptura del piso v8.77
# Condicion adicional (RCB 30% o SMA20>SMA40) deja de ser requisito, solo decide label.
# Mismo patron de fix que ya se hizo con 1VR en v8.63. Fix generico, todos los activos.
# Corre desde: /Users/noellazaro/SPY-ALERT-SERVER/

import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD = '''    # RPG
    if RPG_ON and ed["rpg_activo"] and not ed["rpg_fired"] and ed["rpg_piso"]:
        if v_close < ed["rpg_piso"]:
            ahora_dt_rpg = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))
            techo_rpg    = calcular_techo_canal(simbolo, ahora_dt_rpg)
            _, mitad_rpg = calcular_piso_mitad_canal(simbolo, ahora_dt_rpg)
            c_rpg        = canal[simbolo]

            zona_30_rpg = None
            if techo_rpg and mitad_rpg:
                zona_30_rpg = techo_rpg - (techo_rpg - mitad_rpg) * 0.30
            en_rcb_30_rpg = (
                c_rpg["on"] and not c_rpg["apagado"] and c_rpg["p3"] is not None
                and techo_rpg is not None and zona_30_rpg is not None
                and zona_30_rpg <= v_close <= techo_rpg
            )

            s20_rpg = ed.get("rpg_s20")
            s40_rpg = ed.get("rpg_s40")
            sma20_gt_sma40 = s20_rpg and s40_rpg and s20_rpg > s40_rpg

            if en_rcb_30_rpg or sma20_gt_sma40:
                ed["rpg_fired"]  = True
                ed["rpg_activo"] = False
                guardar_estado_dia()
                label_rpg = "RPG+" if en_rcb_30_rpg else "RPG"
                extra_rpg = f"<b>Canal RCB:</b> Techo ${techo_rpg:.2f} | Zona 30%: ${zona_30_rpg:.2f}\\n" if en_rcb_30_rpg else \\
                            f"<b>SMA20:</b> ${s20_rpg:.2f} > <b>SMA40:</b> ${s40_rpg:.2f}\\n"
                enviar_senal_con_botones(
                    simbolo, f"{label_rpg} — RUPTURA PISO GAP",
                    f"{hora_vela+1}:00 EST", v_close, "PUT",
                    f"<b>Piso V1:</b> ${ed['rpg_piso']:.2f} | <b>Cierre:</b> ${v_close:.2f}\\n{extra_rpg}"
                )
            else:
                print(f"{simbolo} RPG ruptura sin condición adicional — no dispara")'''

NEW = '''    # RPG — dispara siempre con ruptura del piso (v8.77).
    # Condicion adicional (RCB 30% o SMA20>SMA40) solo decide el label RPG vs RPG+,
    # nunca bloquea el disparo. Mismo patron que el fix de 1VR en v8.63.
    if RPG_ON and ed["rpg_activo"] and not ed["rpg_fired"] and ed["rpg_piso"]:
        if v_close < ed["rpg_piso"]:
            ahora_dt_rpg = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))
            techo_rpg    = calcular_techo_canal(simbolo, ahora_dt_rpg)
            _, mitad_rpg = calcular_piso_mitad_canal(simbolo, ahora_dt_rpg)
            c_rpg        = canal[simbolo]

            zona_30_rpg = None
            if techo_rpg and mitad_rpg:
                zona_30_rpg = techo_rpg - (techo_rpg - mitad_rpg) * 0.30
            en_rcb_30_rpg = (
                c_rpg["on"] and not c_rpg["apagado"] and c_rpg["p3"] is not None
                and techo_rpg is not None and zona_30_rpg is not None
                and zona_30_rpg <= v_close <= techo_rpg
            )

            s20_rpg = ed.get("rpg_s20")
            s40_rpg = ed.get("rpg_s40")
            sma20_gt_sma40 = s20_rpg and s40_rpg and s20_rpg > s40_rpg

            ed["rpg_fired"]  = True
            ed["rpg_activo"] = False
            guardar_estado_dia()
            label_rpg = "RPG+" if (en_rcb_30_rpg or sma20_gt_sma40) else "RPG"
            if en_rcb_30_rpg:
                extra_rpg = f"<b>Canal RCB:</b> Techo ${techo_rpg:.2f} | Zona 30%: ${zona_30_rpg:.2f}\\n"
            elif sma20_gt_sma40:
                extra_rpg = f"<b>SMA20:</b> ${s20_rpg:.2f} > <b>SMA40:</b> ${s40_rpg:.2f}\\n"
            else:
                extra_rpg = ""
            enviar_senal_con_botones(
                simbolo, f"{label_rpg} — RUPTURA PISO GAP",
                f"{hora_vela+1}:00 EST", v_close, "PUT",
                f"<b>Piso V1:</b> ${ed['rpg_piso']:.2f} | <b>Cierre:</b> ${v_close:.2f}\\n{extra_rpg}"
            )'''

if OLD not in content:
    errors.append("Bloque RPG original no encontrado")
else:
    content = content.replace(OLD, NEW, 1)
    print("✅ RPG ahora dispara siempre con ruptura del piso (generico, todos los activos)")
    print("✅ Condicion adicional solo decide label RPG vs RPG+")

content = content.replace('AXIS Breakout Sentinel v8.76', 'AXIS Breakout Sentinel v8.77')
print("✅ Versión v8.77")

if errors:
    print("\n❌ ERRORES:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("\n✅ server.py v8.77 guardado")
    print("   git add server.py && git commit -m 'fix: RPG dispara siempre con ruptura del piso v8.77' && git push origin main")

