# add_tradier_raw.py — Endpoint permanente de solo lectura /tradier_raw v8.73
# Permite verificar en cualquier momento los datos crudos de Tradier (daily o 15min)
# sin tocar ninguna logica de construccion de AXIS. Util para comparar contra
# TC2000/TradingView cuando haya dudas de precision de datos.
# Corre desde: /Users/noellazaro/SPY-ALERT-SERVER/

import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

ANCHOR = '''@app.route("/velas_status", methods=["GET"])'''

NEW_ENDPOINT = '''@app.route("/tradier_raw", methods=["GET"])
def tradier_raw():
    """Endpoint permanente de SOLO LECTURA. Llama Tradier directo (sin pasar
    por la base de datos local de AXIS) para verificar datos crudos contra
    TC2000/TradingView cuando haya dudas de precision. No afecta ninguna
    logica de construccion ni evaluacion de AXIS."""
    from datetime import date as _date, timedelta as _td
    simbolo  = request.args.get("simbolo", "SPY").upper()
    interval = request.args.get("interval", "daily")
    dias     = int(request.args.get("dias", 5))

    try:
        hoy = _date.today()
        if interval == "daily":
            fecha_ini = hoy - _td(days=dias * 2)  # buffer por fines de semana
            r = requests.get(
                f"{TRADIER_BASE_REAL}/markets/history",
                headers=TRADIER_HEADERS_REAL,
                params={
                    "symbol":   simbolo,
                    "interval": "daily",
                    "start":    fecha_ini.strftime("%Y-%m-%d"),
                    "end":      hoy.strftime("%Y-%m-%d"),
                },
                timeout=15
            )
            if r.status_code != 200:
                return jsonify({"error": f"Tradier HTTP {r.status_code}"}), 500
            hist = r.json().get("history") or {}
            data = hist.get("day", [])
            if isinstance(data, dict): data = [data]
            data = data[-dias:]
            resultado = [{
                "fecha": d["date"], "open": float(d["open"]), "high": float(d["high"]),
                "low": float(d["low"]), "close": float(d["close"]),
                "volume": int(d.get("volume", 0))
            } for d in data]
        else:
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
            data = data[-dias:]
            resultado = [{
                "time": d["time"], "open": float(d["open"]), "high": float(d["high"]),
                "low": float(d["low"]), "close": float(d["close"])
            } for d in data]

        return jsonify({
            "simbolo": simbolo, "interval": interval,
            "fuente": "Tradier directo — sin construccion AXIS",
            "total": len(resultado), "datos": resultado
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/velas_status", methods=["GET"])'''

if ANCHOR not in content:
    errors.append("Anchor /velas_status no encontrado")
else:
    content = content.replace(ANCHOR, NEW_ENDPOINT, 1)
    print("✅ Endpoint /tradier_raw agregado (permanente, solo lectura)")

content = content.replace('AXIS Breakout Sentinel v8.72', 'AXIS Breakout Sentinel v8.73')
print("✅ Versión v8.73")

if errors:
    print("\n❌ ERRORES:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("\n✅ server.py v8.73 guardado")
    print("   git add server.py && git commit -m 'feat: endpoint permanente tradier_raw v8.73' && git push origin main")
