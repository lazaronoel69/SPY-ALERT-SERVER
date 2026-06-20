# fix_v1_p2.py — V1 actualiza P2 si rompe techo, sin importar tipo de vela v8.76
# Regla: en V1, si v_high > techo y v_high < p1, esa vela se convierte en nuevo P2
# sin importar si es alcista, roja, doji o cualquier tipo. Solo aplica a V1.
# V2-V7 mantienen su logica actual (ya validada, no se toca).
# Corre desde: /Users/noellazaro/SPY-ALERT-SERVER/

import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD = '''        # Canal V1 candidato
        if c["on"] and not c["apagado"]:
            ahora_dt = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))
            techo = calcular_techo_canal(simbolo, ahora_dt)
            if techo and v_close > techo and v_alcista:
                c["v1_candidato"] = v_high
                print(f"{simbolo} Canal V1 candidato Auto-P2: ${v_high:.2f}")'''

NEW = '''        # Canal V1 — P2 dinamico especial: cualquier tipo de vela
        # Si V1 rompe el techo (mecha o cuerpo, sin importar tipo de vela)
        # y el high es menor que P1, se convierte directamente en nuevo P2.
        # Esto aplica SOLO a V1 — V2-V7 usan su propia logica mas abajo.
        if c["on"] and not c["apagado"] and c.get("p1") and c.get("p2_actual_high") is not None:
            ahora_dt_v1c = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))
            techo_v1c = calcular_techo_canal(simbolo, ahora_dt_v1c)
            if techo_v1c and v_high > techo_v1c and v_high < c["p1"]["high"]:
                p2_ant_v1c = c["p2_actual_high"]
                c["p2_actual_high"] = v_high
                c["p2"]["high"]     = v_high
                c["p2"]["fecha"]    = ahora_dt_v1c.strftime("%Y-%m-%d")
                c["p2"]["hora_est"] = ahora_dt_v1c.hour
                c["p2_actual_ts"]   = ahora_dt_v1c
                guardar_canales()
                print(f"{simbolo} P2 dinamico (V1): ${p2_ant_v1c:.2f} -> ${v_high:.2f} ({ahora_dt_v1c.strftime('%Y-%m-%d')}) silencioso")'''

if OLD not in content:
    errors.append("Bloque Canal V1 candidato no encontrado")
else:
    content = content.replace(OLD, NEW, 1)
    print("✅ V1 ahora actualiza P2 directamente si rompe techo, sin importar tipo de vela")
    print("✅ V2-V7 quedan intactos con su logica actual (not v_alcista)")

content = content.replace('AXIS Breakout Sentinel v8.75', 'AXIS Breakout Sentinel v8.76')
print("✅ Versión v8.76")

if errors:
    print("\n❌ ERRORES:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("\n✅ server.py v8.76 guardado")
    print("   git add server.py && git commit -m 'fix: V1 mueve P2 sin importar tipo de vela v8.76' && git push origin main")
