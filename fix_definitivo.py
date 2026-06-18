# fix_definitivo.py — Fix definitivo velas AXIS v8.68
# 1. Fix en get_velas(): nunca devolver vela cuya ultima barra no haya cerrado + 1min
# 2. Eliminar parches anteriores de buffer en actualizar_velas_local(), construir_base_datos_activo(), rellenar_velas
# 3. Version v8.68
# Corre desde: /Users/noellazaro/SPY-ALERT-SERVER/
# Uso: python3 fix_definitivo.py

import sys
import os

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

# ═══════════════════════════════════════════════════════
# CAMBIO 1 — Eliminar parche buffer en actualizar_velas_local()
# Reemplazar el bloque con filtro de barras por el original limpio
# ═══════════════════════════════════════════════════════
OLD_ACTUALIZAR = '''    if nuevas:
        # FILTER: no guardar barras cuyo periodo de 15min no haya cerrado
        # Buffer de 2 minutos extra para delay de Tradier
        from datetime import datetime as _dt2, timedelta as _td2
        ahora_est_utc = datetime.now(EST)
        nuevas_cerradas = []
        for b in nuevas:
            try:
                ts_str = b["time"].replace("T", " ")[:19]
                barra_dt = _dt2.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                barra_cierre = barra_dt + _td2(minutes=1)  # 15min + 2min buffer
                barra_cierre_est = EST.localize(barra_cierre)
                if ahora_est_utc >= barra_cierre_est:
                    nuevas_cerradas.append(b)
                else:
                    print(f"{simbolo}: barra {b['time']} aun abierta — no guardada")
            except Exception as e:
                print(f"{simbolo}: error verificando barra {b.get('time','?')}: {e}")
                nuevas_cerradas.append(b)  # en caso de error, guardar igual
        if nuevas_cerradas:
            local["barras"].extend(nuevas_cerradas)
            local["ultima_barra"] = nuevas_cerradas[-1]["time"]
            guardar_velas_local(simbolo, local)
            print(f"{simbolo}: +{len(nuevas_cerradas)} barras cerradas guardadas (de {len(nuevas)} recibidas)")
        elif nuevas:
            print(f"{simbolo}: {len(nuevas)} barras recibidas pero ninguna cerrada aun — sin cambios")

    return True'''

NEW_ACTUALIZAR = '''    if nuevas:
        local["barras"].extend(nuevas)
        local["ultima_barra"] = nuevas[-1]["time"]
        guardar_velas_local(simbolo, local)
        print(f"{simbolo}: +{len(nuevas)} barras nuevas guardadas")

    return True'''

if OLD_ACTUALIZAR not in content:
    errors.append("CAMBIO 1: bloque actualizar_velas_local con parche no encontrado")
else:
    content = content.replace(OLD_ACTUALIZAR, NEW_ACTUALIZAR, 1)
    print("✅ Cambio 1: parche buffer eliminado de actualizar_velas_local()")

# ═══════════════════════════════════════════════════════
# CAMBIO 2 — Eliminar parche buffer en construir_base_datos_activo()
# ═══════════════════════════════════════════════════════
OLD_CONSTRUIR = '''        if r3.status_code == 200:
            s3 = r3.json().get("series")
            if s3 and s3 != "null":
                b3 = s3.get("data", [])
                if isinstance(b3, dict): b3 = [b3]
                from datetime import datetime as _dt3, timedelta as _td3
                ahora_est_c = datetime.now(EST)
                b3_cerradas = []
                for barra in b3:
                    try:
                        ts_str = barra["time"].replace("T", " ")[:19]
                        barra_dt = _dt3.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        barra_cierre = barra_dt + _td3(minutes=1)
                        barra_cierre_est = EST.localize(barra_cierre)
                        if ahora_est_c >= barra_cierre_est:
                            barra["interval"] = "15min"
                            b3_cerradas.append(barra)
                    except:
                        barra["interval"] = "15min"
                        b3_cerradas.append(barra)
                todas_barras.extend(b3_cerradas)
                print(f"  {simbolo} timesales 15min hoy: {len(b3_cerradas)} barras cerradas (de {len(b3)} recibidas)")'''

NEW_CONSTRUIR = '''        if r3.status_code == 200:
            s3 = r3.json().get("series")
            if s3 and s3 != "null":
                b3 = s3.get("data", [])
                if isinstance(b3, dict): b3 = [b3]
                for barra in b3:
                    barra["interval"] = "15min"
                todas_barras.extend(b3)
                print(f"  {simbolo} timesales 15min hoy: {len(b3)} barras")'''

if OLD_CONSTRUIR not in content:
    errors.append("CAMBIO 2: bloque construir_base_datos con parche no encontrado")
else:
    content = content.replace(OLD_CONSTRUIR, NEW_CONSTRUIR, 1)
    print("✅ Cambio 2: parche buffer eliminado de construir_base_datos_activo()")

# ═══════════════════════════════════════════════════════
# CAMBIO 3 — Eliminar parche buffer en rellenar_velas
# ═══════════════════════════════════════════════════════
OLD_RELLENAR = '''            tiempos_existentes = {b["time"] for b in b15}
            from datetime import datetime as _dtr, timedelta as _tdr
            ahora_est_r = datetime.now(EST)
            nuevas = []
            for b in barras_tradier:
                t = b["time"]
                if t not in tiempos_existentes:
                    # Verificar que la barra ya cerro (buffer 17min)
                    try:
                        ts_str = t.replace("T", " ")[:19]
                        barra_dt = _dtr.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        barra_cierre = EST.localize(barra_dt + _tdr(minutes=1))
                        if ahora_est_r < barra_cierre:
                            continue  # barra aun abierta — no guardar
                    except:
                        pass
                    b["interval"] = "15min"
                    nuevas.append(b)'''

NEW_RELLENAR = '''            tiempos_existentes = {b["time"] for b in b15}
            nuevas = []
            for b in barras_tradier:
                t = b["time"]
                if t not in tiempos_existentes:
                    b["interval"] = "15min"
                    nuevas.append(b)'''

if OLD_RELLENAR not in content:
    errors.append("CAMBIO 3: bloque rellenar_velas con parche no encontrado")
else:
    content = content.replace(OLD_RELLENAR, NEW_RELLENAR, 1)
    print("✅ Cambio 3: parche buffer eliminado de rellenar_velas")

# ═══════════════════════════════════════════════════════
# CAMBIO 4 — Fix definitivo en get_velas()
# Filtrar velas cuya ultima barra no haya cerrado + 1 minuto
# ═══════════════════════════════════════════════════════
OLD_GET_VELAS_APPEND = '''                resultado.append({
                    "datetime":      f"{fecha} {vela_hora[vela]}",
                    "open":          str(round(o, 4)),
                    "high":          str(round(h, 4)),
                    "low":           str(round(l, 4)),
                    "close":         str(round(c, 4)),
                    "vela":          vela,
                    "bars":          len(bs),
                    "bars_expected": vela_bars[vela],
                    "completa":      len(bs) >= vela_bars[vela],
                })'''

NEW_GET_VELAS_APPEND = '''                # Regla definitiva: una vela solo existe si su ultima barra de 15min
                # ya cerro + 1 minuto (para dar tiempo a Tradier de consolidar el dato)
                ultima_barra_ts = bs[-1]["time"].replace("T", " ")[:19]
                try:
                    ultima_barra_dt = dt2.strptime(ultima_barra_ts, "%Y-%m-%d %H:%M:%S")
                    vela_disponible = EST.localize(ultima_barra_dt + timedelta(minutes=16))
                    ahora_est_gv = datetime.now(EST)
                    if ahora_est_gv < vela_disponible:
                        continue  # vela aun no disponible — ultima barra no cerro + 1min
                except:
                    pass

                resultado.append({
                    "datetime":      f"{fecha} {vela_hora[vela]}",
                    "open":          str(round(o, 4)),
                    "high":          str(round(h, 4)),
                    "low":           str(round(l, 4)),
                    "close":         str(round(c, 4)),
                    "vela":          vela,
                    "bars":          len(bs),
                    "bars_expected": vela_bars[vela],
                    "completa":      len(bs) >= vela_bars[vela],
                })'''

if OLD_GET_VELAS_APPEND not in content:
    errors.append("CAMBIO 4: bloque resultado.append en get_velas no encontrado")
else:
    content = content.replace(OLD_GET_VELAS_APPEND, NEW_GET_VELAS_APPEND, 1)
    print("✅ Cambio 4: fix definitivo en get_velas() — velas solo disponibles tras cierre + 1min")

# ═══════════════════════════════════════════════════════
# CAMBIO 5 — Version v8.68
# ═══════════════════════════════════════════════════════
content = content.replace('AXIS Breakout Sentinel v8.67', 'AXIS Breakout Sentinel v8.68')
content = content.replace('"sistema": "AXIS Breakout Sentinel v8.67"', '"sistema": "AXIS Breakout Sentinel v8.68"')
content = content.replace('print("AXIS Breakout Sentinel v8.67 iniciado...")', 'print("AXIS Breakout Sentinel v8.68 iniciado...")')
print("✅ Cambio 5: versión v8.68")

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
    print("\n✅ server.py v8.68 guardado — fix definitivo velas AXIS")
    print("   Siguiente: eliminar archivos innecesarios y hacer commit")
    print("   git rm fix_derby.py fix_velas.py fix_buffer.py fix_definitivo.py")
    print("   git add server.py")
    print("   git commit -m 'fix: velas AXIS solo disponibles tras cierre + 1min v8.68'")
    print("   git push origin main")

