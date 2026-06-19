# fix_daily_v2.py — agregar_barra_diaria() ahora usa Tradier history diario directo v8.74
# Resuelve discrepancia 298.50 (construido desde 15min) vs 298.01 (Tradier history real)
# No afecta velas AXIS por hora (V1-V7) — esas siguen igual desde barras 15min
# Corre desde: /Users/noellazaro/SPY-ALERT-SERVER/

import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD_FUNC = '''def agregar_barra_diaria(simbolo, fecha_str=None):
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
    return True'''

NEW_FUNC = '''def agregar_barra_diaria(simbolo, fecha_str=None):
    """Obtiene el OHLC diario OFICIAL directo de Tradier history (no lo
    construye desde barras 15min, para evitar discrepancias) y lo agrega
    a la base permanente si no existe ya. Usado tanto en tiempo real (4:16 PM)
    como en las redes de seguridad (arranque y /rellenar_velas).
    No afecta las velas AXIS por hora (V1-V7) — esas siguen usando barras 15min."""
    from datetime import date as _date

    if fecha_str is None:
        fecha_str = _date.today().strftime("%Y-%m-%d")

    local = cargar_velas_local(simbolo)
    barras_daily = [b for b in local["barras"] if b.get("interval") == "daily"]
    fechas_existentes = {b["time"][:10] for b in barras_daily}
    if fecha_str in fechas_existentes:
        return False  # ya existe, no duplicar

    try:
        r = requests.get(
            f"{TRADIER_BASE_REAL}/markets/history",
            headers=TRADIER_HEADERS_REAL,
            params={"symbol": simbolo, "interval": "daily", "start": fecha_str, "end": fecha_str},
            timeout=15
        )
        if r.status_code != 200:
            print(f"{simbolo}: error HTTP {r.status_code} pidiendo daily {fecha_str}")
            return False
        hist = r.json().get("history") or {}
        dias = hist.get("day", [])
        if isinstance(dias, dict): dias = [dias]
        if not dias:
            return False  # Tradier aun no tiene el dato consolidado de ese dia
        d = dias[0]
        nueva_daily = {
            "time":     fecha_str + "T16:00:00",
            "open":     float(d["open"]),
            "high":     float(d["high"]),
            "low":      float(d["low"]),
            "close":    float(d["close"]),
            "volume":   int(d.get("volume", 0)),
            "interval": "daily"
        }
    except Exception as e:
        print(f"{simbolo}: error obteniendo daily Tradier {fecha_str}: {e}")
        return False

    local["barras"].append(nueva_daily)
    guardar_velas_local(simbolo, local)
    print(f"{simbolo}: barra diaria agregada (Tradier oficial) — {fecha_str} O:{nueva_daily['open']:.2f} C:{nueva_daily['close']:.2f}")
    return True'''

if OLD_FUNC not in content:
    errors.append("Funcion agregar_barra_diaria original no encontrada")
else:
    content = content.replace(OLD_FUNC, NEW_FUNC, 1)
    print("✅ agregar_barra_diaria() ahora usa Tradier history oficial en vez de construir desde 15min")

content = content.replace('AXIS Breakout Sentinel v8.73', 'AXIS Breakout Sentinel v8.74')
print("✅ Versión v8.74")

if errors:
    print("\n❌ ERRORES:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("\n✅ server.py v8.74 guardado")
    print("   git add server.py && git commit -m 'fix: barra diaria usa tradier history oficial v8.74' && git push origin main")
