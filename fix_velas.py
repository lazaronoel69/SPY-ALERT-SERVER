# fix_velas.py — Fix definitivo barras incompletas v8.66
# Corre desde: /Users/noellazaro/SPY-ALERT-SERVER/
# Uso: python3 fix_velas.py

import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

# ═══════════════════════════════════════════════════════
# CAMBIO 1 — actualizar_velas_local(): no guardar barras no cerradas
# ═══════════════════════════════════════════════════════
OLD_ACTUALIZAR = '''    if nuevas:
        local["barras"].extend(nuevas)
        local["ultima_barra"] = nuevas[-1]["time"]
        guardar_velas_local(simbolo, local)
        print(f"{simbolo}: +{len(nuevas)} barras nuevas guardadas")

    return True'''

NEW_ACTUALIZAR = '''    if nuevas:
        # FILTER: no guardar barras cuyo periodo de 15min no haya cerrado
        # Buffer de 2 minutos extra para delay de Tradier
        from datetime import datetime as _dt2, timedelta as _td2
        ahora_est_utc = datetime.now(EST)
        nuevas_cerradas = []
        for b in nuevas:
            try:
                ts_str = b["time"].replace("T", " ")[:19]
                barra_dt = _dt2.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                barra_cierre = barra_dt + _td2(minutes=17)  # 15min + 2min buffer
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

if OLD_ACTUALIZAR not in content:
    errors.append("CAMBIO 1: bloque actualizar_velas_local no encontrado")
else:
    content = content.replace(OLD_ACTUALIZAR, NEW_ACTUALIZAR, 1)
    print("✅ Cambio 1: actualizar_velas_local() — filtro barras no cerradas con buffer 17min")

# ═══════════════════════════════════════════════════════
# CAMBIO 2 — construir_base_datos_activo(): mismo filtro al construir
# ═══════════════════════════════════════════════════════
OLD_CONSTRUIR_BARRAS = '''        if r3.status_code == 200:
            s3 = r3.json().get("series")
            if s3 and s3 != "null":
                b3 = s3.get("data", [])
                if isinstance(b3, dict): b3 = [b3]
                for barra in b3:
                    barra["interval"] = "15min"
                todas_barras.extend(b3)
                print(f"  {simbolo} timesales 15min hoy: {len(b3)} barras")'''

NEW_CONSTRUIR_BARRAS = '''        if r3.status_code == 200:
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
                        barra_cierre = barra_dt + _td3(minutes=17)
                        barra_cierre_est = EST.localize(barra_cierre)
                        if ahora_est_c >= barra_cierre_est:
                            barra["interval"] = "15min"
                            b3_cerradas.append(barra)
                    except:
                        barra["interval"] = "15min"
                        b3_cerradas.append(barra)
                todas_barras.extend(b3_cerradas)
                print(f"  {simbolo} timesales 15min hoy: {len(b3_cerradas)} barras cerradas (de {len(b3)} recibidas)")'''

if OLD_CONSTRUIR_BARRAS not in content:
    errors.append("CAMBIO 2: bloque construir_base_datos_activo barras hoy no encontrado")
else:
    content = content.replace(OLD_CONSTRUIR_BARRAS, NEW_CONSTRUIR_BARRAS, 1)
    print("✅ Cambio 2: construir_base_datos_activo() — mismo filtro al construir base")

# ═══════════════════════════════════════════════════════
# CAMBIO 3 — rellenar_velas endpoint: mismo filtro
# ═══════════════════════════════════════════════════════
OLD_RELLENAR = '''            tiempos_existentes = {b["time"] for b in b15}
            nuevas = []
            for b in barras_tradier:
                t = b["time"]
                if t not in tiempos_existentes:
                    b["interval"] = "15min"
                    nuevas.append(b)
            if nuevas:
                local["barras"].extend(nuevas)
                local["barras"].sort(key=lambda x: x["time"])
                local["ultima_barra"] = local["barras"][-1]["time"]
                guardar_velas_local(simbolo, local)
                resultado[simbolo] = f"✅ +{len(nuevas)} barras nuevas ({antes} → {antes+len(nuevas)})"
            else:
                resultado[simbolo] = f"✅ Sin faltantes ({antes} barras)"'''

NEW_RELLENAR = '''            tiempos_existentes = {b["time"] for b in b15}
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
                        barra_cierre = EST.localize(barra_dt + _tdr(minutes=17))
                        if ahora_est_r < barra_cierre:
                            continue  # barra aun abierta — no guardar
                    except:
                        pass
                    b["interval"] = "15min"
                    nuevas.append(b)
            if nuevas:
                local["barras"].extend(nuevas)
                local["barras"].sort(key=lambda x: x["time"])
                local["ultima_barra"] = local["barras"][-1]["time"]
                guardar_velas_local(simbolo, local)
                resultado[simbolo] = f"✅ +{len(nuevas)} barras nuevas ({antes} → {antes+len(nuevas)})"
            else:
                resultado[simbolo] = f"✅ Sin faltantes ({antes} barras)"'''

if OLD_RELLENAR not in content:
    errors.append("CAMBIO 3: bloque rellenar_velas no encontrado")
else:
    content = content.replace(OLD_RELLENAR, NEW_RELLENAR, 1)
    print("✅ Cambio 3: /rellenar_velas — mismo filtro aplicado")

# ═══════════════════════════════════════════════════════
# CAMBIO 4 — Version v8.66
# ═══════════════════════════════════════════════════════
content = content.replace('AXIS Breakout Sentinel v8.65', 'AXIS Breakout Sentinel v8.66')
content = content.replace('"sistema": "AXIS Breakout Sentinel v8.65"', '"sistema": "AXIS Breakout Sentinel v8.66"')
content = content.replace('print("AXIS Breakout Sentinel v8.65 iniciado...")', 'print("AXIS Breakout Sentinel v8.66 iniciado...")')
print("✅ Cambio 4: versión v8.66")

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
    print("\n✅ server.py v8.66 guardado — fix definitivo barras incompletas")
    print("   Corre: git add server.py && git commit -m 'fix: no guardar barras antes de cerrar v8.66' && git push origin main")

