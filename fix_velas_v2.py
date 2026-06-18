# fix_velas_v2.py — Corrige filtro de velas AXIS v8.69
# El filtro correcto usa la hora de cierre de la VELA AXIS completa, no la ultima barra de 15min
# Corre desde: /Users/noellazaro/SPY-ALERT-SERVER/

import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

# ═══════════════════════════════════════════════════════
# CAMBIO 1 — Corregir filtro en get_velas()
# Reemplazar timedelta(minutes=16) sobre ultima barra
# por verificacion de hora de cierre de la vela AXIS completa
# ═══════════════════════════════════════════════════════
OLD_FILTRO = '''                # Regla definitiva: una vela solo existe si su ultima barra de 15min
                # ya cerro + 1 minuto (para dar tiempo a Tradier de consolidar el dato)
                ultima_barra_ts = bs[-1]["time"].replace("T", " ")[:19]
                try:
                    ultima_barra_dt = dt2.strptime(ultima_barra_ts, "%Y-%m-%d %H:%M:%S")
                    vela_disponible = EST.localize(ultima_barra_dt + timedelta(minutes=16))
                    ahora_est_gv = datetime.now(EST)
                    if ahora_est_gv < vela_disponible:
                        continue  # vela aun no disponible — ultima barra no cerro + 1min
                except:
                    pass'''

NEW_FILTRO = '''                # Regla definitiva AXIS: una vela solo existe a partir del :01
                # despues de su hora de cierre completa
                # V1 cierra a las 10:00 → disponible a las 10:01
                # V2 cierra a las 11:00 → disponible a las 11:01
                # etc.
                vela_cierre_hora = {
                    "V1": 10, "V2": 11, "V3": 12, "V4": 13,
                    "V5": 14, "V6": 15, "V7": 16
                }
                try:
                    hora_cierre = vela_cierre_hora.get(vela)
                    if hora_cierre:
                        anno, mes, dia = int(fecha[:4]), int(fecha[5:7]), int(fecha[8:10])
                        cierre_dt = datetime(anno, mes, dia, hora_cierre, 1, 0)
                        cierre_est = EST.localize(cierre_dt)
                        if datetime.now(EST) < cierre_est:
                            continue  # vela no disponible aun
                except:
                    pass'''

if OLD_FILTRO not in content:
    errors.append("CAMBIO 1: filtro de velas en get_velas() no encontrado")
else:
    content = content.replace(OLD_FILTRO, NEW_FILTRO, 1)
    print("✅ Cambio 1: filtro corregido — velas disponibles al :01 de su hora de cierre")

# ═══════════════════════════════════════════════════════
# CAMBIO 2 — Version v8.69
# ═══════════════════════════════════════════════════════
content = content.replace('AXIS Breakout Sentinel v8.68', 'AXIS Breakout Sentinel v8.69')
content = content.replace('"sistema": "AXIS Breakout Sentinel v8.68"', '"sistema": "AXIS Breakout Sentinel v8.69"')
content = content.replace('print("AXIS Breakout Sentinel v8.68 iniciado...")', 'print("AXIS Breakout Sentinel v8.69 iniciado...")')
print("✅ Cambio 2: versión v8.69")

# ═══════════════════════════════════════════════════════
# VERIFICACION
# ═══════════════════════════════════════════════════════
if errors:
    print("\n❌ ERRORES:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("\n✅ server.py v8.69 guardado")
    print("   git add server.py && git commit -m 'fix: velas AXIS disponibles al :01 de hora de cierre v8.69' && git push origin main")

