# fix_tradier_raw.py — Corrige bug del parametro dias en /tradier_raw para 15min v8.75
# Endpoint completamente aislado, no afecta ninguna otra parte de AXIS
# Corre desde: /Users/noellazaro/SPY-ALERT-SERVER/

import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD = '''        else:
            fecha_ini = hoy - _td(days=2)
            r = requests.get(
                f"{TRADIER_BASE_REAL}/markets/timesales",
                headers=TRADIER_HEADERS_REAL,
                params={
                    "symbol": simbolo, "interval": "15min",
                    "start": f"{fecha_ini.strftime('%Y-%m-%d')} 09:00",
                    "end": f"{hoy.strftime('%Y-%m-%d')} 16:30",
                    "session_filter": "open",
                },
                timeout=15
            )
            if r.status_code != 200:
                return jsonify({"error": f"Tradier HTTP {r.status_code}"}), 500
            series = r.json().get("series")
            data = []
            if series and series != "null":
                data = series.get("data", [])
                if isinstance(data, dict): data = [data]
            data = data[-dias:]'''

NEW = '''        else:
            fecha_ini = hoy - _td(days=dias)
            r = requests.get(
                f"{TRADIER_BASE_REAL}/markets/timesales",
                headers=TRADIER_HEADERS_REAL,
                params={
                    "symbol": simbolo, "interval": "15min",
                    "start": f"{fecha_ini.strftime('%Y-%m-%d')} 09:00",
                    "end": f"{hoy.strftime('%Y-%m-%d')} 16:30",
                    "session_filter": "open",
                },
                timeout=20
            )
            if r.status_code != 200:
                return jsonify({"error": f"Tradier HTTP {r.status_code}"}), 500
            series = r.json().get("series")
            data = []
            if series and series != "null":
                data = series.get("data", [])
                if isinstance(data, dict): data = [data]'''

if OLD not in content:
    errors.append("Bloque 15min en tradier_raw no encontrado")
else:
    content = content.replace(OLD, NEW, 1)
    print("✅ Bug corregido — parametro dias ahora se usa correctamente para rango de fechas en 15min")
    print("✅ Eliminado el corte data[-dias:] — ahora devuelve TODO el rango pedido a Tradier")

content = content.replace('AXIS Breakout Sentinel v8.74', 'AXIS Breakout Sentinel v8.75')
print("✅ Versión v8.75")

if errors:
    print("\n❌ ERRORES:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("\n✅ server.py v8.75 guardado")
    print("   git add server.py && git commit -m 'fix: parametro dias en tradier_raw 15min v8.75' && git push origin main")
