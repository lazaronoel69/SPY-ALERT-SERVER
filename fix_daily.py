# fix_daily.py — Fix definitivo barras diarias v8.72
# 1. Nueva funcion agregar_barra_diaria() — calcula OHLC del dia desde barras 15min y la agrega si no existe
# 2. Llamada en loop_v7_anticipada a las 4:16 PM (captura en tiempo real)
# 3. Red de seguridad en construir_base_datos() al arrancar — rellena dias faltantes recientes
# 4. Red de seguridad en /rellenar_velas — rellena dias faltantes tambien
# Corre desde: /Users/noellazaro/SPY-ALERT-SERVER/

import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

# ═══════════════════════════════════════════════════════
# CAMBIO 1 — Nueva funcion agregar_barra_diaria()
# Se inserta justo antes de construir_base_datos_activo()
# ═══════════════════════════════════════════════════════
ANCHOR1 = '''def construir_base_datos_activo(simbolo):'''

NEW_FUNC = '''def agregar_barra_diaria(simbolo, fecha_str=None):
    """Calcula el OHLC diario desde las barras 15min de una fecha y lo agrega
    a la base permanente si no existe ya. Usado tanto en tiempo real (4:16 PM)
    como en las redes de seguridad (arranque y /rellenar_velas)."""
    from datetime import date as _date, datetime as _dt2
    if fecha_str is None:
        fecha_str = _date.today().strftime("%Y-%m-%d")

    local = cargar_velas_local(simbolo)
    barras_daily = [b for b in local["barras"] if b.get("interval") == "daily"]
    fechas_existentes = {b["time"][:10] for b in barras_daily}
    if fecha_str in fechas_existentes:
        return False  # ya existe, no duplicar

    barras_15min_dia = [
        b for b in local["barras"]
        if b.get("interval") == "15min" and b["time"][:10] == fecha_str
    ]
    if len(barras_15min_dia) < 4:
        return False  # dia incompleto, no construir barra diaria todavia

    barras_15min_dia.sort(key=lambda x: x["time"])
    nueva_daily = {
        "time":     fecha_str + "T16:00:00",
        "open":     float(barras_15min_dia[0]["open"]),
        "high":     max(float(b["high"]) for b in barras_15min_dia),
        "low":      min(float(b["low"])  for b in barras_15min_dia),
        "close":    float(barras_15min_dia[-1]["close"]),
        "volume":   sum(int(b.get("volume", 0)) for b in barras_15min_dia),
        "interval": "daily"
    }
    local["barras"].append(nueva_daily)
    guardar_velas_local(simbolo, local)
    print(f"{simbolo}: barra diaria agregada — {fecha_str} O:{nueva_daily['open']:.2f} C:{nueva_daily['close']:.2f}")
    return True

def rellenar_dias_faltantes(simbolo, dias_atras=10):
    """Red de seguridad: revisa los ultimos N dias habiles y agrega
    cualquier barra diaria faltante usando las barras 15min ya guardadas."""
    from datetime import date as _date, timedelta as _td
    hoy = _date.today()
    agregadas = 0
    for i in range(dias_atras):
        fecha = hoy - _td(days=i)
        if fecha.weekday() >= 5:
            continue
        if not es_dia_mercado(EST.localize(datetime(fecha.year, fecha.month, fecha.day, 12, 0))):
            continue
        if agregar_barra_diaria(simbolo, fecha.strftime("%Y-%m-%d")):
            agregadas += 1
    return agregadas

def construir_base_datos_activo(simbolo):'''

if ANCHOR1 not in content:
    errors.append("CAMBIO 1: anchor construir_base_datos_activo no encontrado")
else:
    content = content.replace(ANCHOR1, NEW_FUNC, 1)
    print("✅ Cambio 1: funciones agregar_barra_diaria() y rellenar_dias_faltantes() agregadas")

# ═══════════════════════════════════════════════════════
# CAMBIO 2 — Llamar agregar_barra_diaria() en loop_v7_anticipada a las 4:16 PM
# ═══════════════════════════════════════════════════════
OLD_416 = '''                    if "resumen" not in ejecutado_416:
                        ejecutado_416.add("resumen")
                        guardar_snapshot_precios(ahora)
                        archivar_señales_dia(ahora.strftime("%Y-%m-%d"))
                        enviar_resumen_diario(ahora)'''

NEW_416 = '''                    if "resumen" not in ejecutado_416:
                        ejecutado_416.add("resumen")
                        fecha_hoy_v7 = ahora.strftime("%Y-%m-%d")
                        for simbolo_daily in ACTIVOS:
                            try:
                                agregar_barra_diaria(simbolo_daily, fecha_hoy_v7)
                            except Exception as e:
                                print(f"Error agregando barra diaria {simbolo_daily}: {e}")
                        guardar_snapshot_precios(ahora)
                        archivar_señales_dia(ahora.strftime("%Y-%m-%d"))
                        enviar_resumen_diario(ahora)'''

if OLD_416 not in content:
    errors.append("CAMBIO 2: bloque 4:16 PM en loop_v7_anticipada no encontrado")
else:
    content = content.replace(OLD_416, NEW_416, 1)
    print("✅ Cambio 2: agregar_barra_diaria() llamada en captura tiempo real 4:16 PM")

# ═══════════════════════════════════════════════════════
# CAMBIO 3 — Red de seguridad al arrancar (construir_base_datos)
# ═══════════════════════════════════════════════════════
OLD_ARRANQUE = '''def construir_base_datos():
    print("Verificando base de datos de velas...")
    for simbolo in ACTIVOS:
        construir_base_datos_activo(simbolo)
    print("Base de datos de velas lista.")'''

NEW_ARRANQUE = '''def construir_base_datos():
    print("Verificando base de datos de velas...")
    for simbolo in ACTIVOS:
        construir_base_datos_activo(simbolo)
    print("Base de datos de velas lista.")
    print("Verificando barras diarias faltantes (red de seguridad)...")
    for simbolo in ACTIVOS:
        try:
            agregadas = rellenar_dias_faltantes(simbolo, dias_atras=10)
            if agregadas:
                print(f"{simbolo}: {agregadas} barras diarias recuperadas")
        except Exception as e:
            print(f"Error rellenando dias faltantes {simbolo}: {e}")'''

if OLD_ARRANQUE not in content:
    errors.append("CAMBIO 3: bloque construir_base_datos no encontrado")
else:
    content = content.replace(OLD_ARRANQUE, NEW_ARRANQUE, 1)
    print("✅ Cambio 3: red de seguridad agregada al arranque")

# ═══════════════════════════════════════════════════════
# CAMBIO 4 — Red de seguridad en /rellenar_velas
# ═══════════════════════════════════════════════════════
OLD_RELLENAR_END = '''            if nuevas:
                local["barras"].extend(nuevas)
                local["barras"].sort(key=lambda x: x["time"])
                local["ultima_barra"] = local["barras"][-1]["time"]
                guardar_velas_local(simbolo, local)
                resultado[simbolo] = f"✅ +{len(nuevas)} barras nuevas ({antes} → {antes+len(nuevas)})"
            else:
                resultado[simbolo] = f"✅ Sin faltantes ({antes} barras)"
        except Exception as e:
            resultado[simbolo] = f"❌ Error: {e}"
    return jsonify({"fecha": str(hoy), "resultado": resultado}), 200'''

NEW_RELLENAR_END = '''            if nuevas:
                local["barras"].extend(nuevas)
                local["barras"].sort(key=lambda x: x["time"])
                local["ultima_barra"] = local["barras"][-1]["time"]
                guardar_velas_local(simbolo, local)
                resultado[simbolo] = f"✅ +{len(nuevas)} barras nuevas ({antes} → {antes+len(nuevas)})"
            else:
                resultado[simbolo] = f"✅ Sin faltantes ({antes} barras)"
            # Red de seguridad — rellenar barras diarias faltantes tambien
            try:
                daily_agregadas = rellenar_dias_faltantes(simbolo, dias_atras=10)
                if daily_agregadas:
                    resultado[simbolo] += f" | +{daily_agregadas} barras diarias recuperadas"
            except Exception as e:
                resultado[simbolo] += f" | error daily: {e}"
        except Exception as e:
            resultado[simbolo] = f"❌ Error: {e}"
    return jsonify({"fecha": str(hoy), "resultado": resultado}), 200'''

if OLD_RELLENAR_END not in content:
    errors.append("CAMBIO 4: bloque final rellenar_velas no encontrado")
else:
    content = content.replace(OLD_RELLENAR_END, NEW_RELLENAR_END, 1)
    print("✅ Cambio 4: red de seguridad agregada a /rellenar_velas")

# ═══════════════════════════════════════════════════════
# CAMBIO 5 — Version v8.72
# ═══════════════════════════════════════════════════════
content = content.replace('AXIS Breakout Sentinel v8.71', 'AXIS Breakout Sentinel v8.72')
print("✅ Cambio 5: versión v8.72")

# ═══════════════════════════════════════════════════════
# VERIFICACION
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
    print("\n✅ server.py v8.72 guardado — fix definitivo barras diarias")
    print("   git add server.py && git commit -m 'fix: barras diarias 2 capas v8.72' && git push origin main")
