# add_comparar.py — Endpoint temporal de solo lectura para comparar strikes
# NO modifica ninguna logica existente de compra
# Agrega /comparar_strikes?simbolo=X&tipo=put|call
# Corre desde: /Users/noellazaro/SPY-ALERT-SERVER/

import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

# Buscar un punto de anclaje seguro — despues de get_opcion_tradier
ANCHOR = '''def buscar_opcion_reto(opcion_original, presupuesto):'''

NEW_ENDPOINT = '''@app.route("/comparar_strikes", methods=["GET"])
def comparar_strikes():
    """Endpoint de SOLO LECTURA para comparar strikes por delta vs % OTM actual.
    No modifica ninguna logica de compra existente."""
    simbolo = request.args.get("simbolo", "SPY").upper()
    tipo    = request.args.get("tipo", "put").lower()
    try:
        from datetime import date
        hoy = date.today()
        # Precio actual
        r0 = requests.get(f"{TRADIER_BASE}/markets/quotes",
                          headers=TRADIER_HEADERS, params={"symbols": simbolo}, timeout=10)
        precio_actual = float(r0.json()["quotes"]["quote"]["last"])

        # Vencimientos disponibles
        r = requests.get(f"{TRADIER_BASE}/markets/options/expirations",
                         headers=TRADIER_HEADERS,
                         params={"symbol": simbolo, "includeAllRoots": "true"}, timeout=10)
        fechas = r.json().get("expirations", {}).get("date", [])
        if isinstance(fechas, str):
            fechas = [fechas]

        vencimientos_7_14 = [f for f in sorted(fechas)
                             if 7 <= (date.fromisoformat(f) - hoy).days <= 14]

        resultado = {"simbolo": simbolo, "precio_actual": precio_actual,
                    "pct_otm_actual": get_pct_otm(precio_actual), "vencimientos": []}

        for venc in vencimientos_7_14[:3]:  # max 3 vencimientos para no saturar
            r2 = requests.get(f"{TRADIER_BASE}/markets/options/chains",
                              headers=TRADIER_HEADERS,
                              params={"symbol": simbolo, "expiration": venc, "greeks": "true"},
                              timeout=10)
            opciones = r2.json().get("options", {}).get("option", [])
            filtradas = [o for o in opciones if o.get("option_type") == tipo and float(o.get("ask", 0)) > 0]

            # Strike actual del sistema (por % OTM)
            pct = get_pct_otm(precio_actual)
            dist = precio_actual * pct / 100
            strike_obj_actual = round(precio_actual + dist) if tipo == "call" else round(precio_actual - dist)
            mejor_actual = min(filtradas, key=lambda o: abs(float(o.get("strike", 0)) - strike_obj_actual)) if filtradas else None

            # Strike por delta ~0.35
            con_delta = [o for o in filtradas if o.get("greeks", {}).get("delta") is not None]
            mejor_delta = min(con_delta, key=lambda o: abs(abs(float(o["greeks"]["delta"])) - 0.35)) if con_delta else None

            dias = (date.fromisoformat(venc) - hoy).days
            resultado["vencimientos"].append({
                "fecha": venc, "dias": dias,
                "metodo_actual_pct": {
                    "strike": mejor_actual.get("strike") if mejor_actual else None,
                    "ask": mejor_actual.get("ask") if mejor_actual else None,
                    "delta": mejor_actual.get("greeks", {}).get("delta") if mejor_actual else None,
                },
                "metodo_delta_035": {
                    "strike": mejor_delta.get("strike") if mejor_delta else None,
                    "ask": mejor_delta.get("ask") if mejor_delta else None,
                    "delta": mejor_delta.get("greeks", {}).get("delta") if mejor_delta else None,
                }
            })

        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def buscar_opcion_reto(opcion_original, presupuesto):'''

if ANCHOR not in content:
    errors.append("Punto de anclaje buscar_opcion_reto no encontrado")
else:
    content = content.replace(ANCHOR, NEW_ENDPOINT, 1)
    print("✅ Endpoint /comparar_strikes agregado (solo lectura)")

if errors:
    print("\n❌ ERRORES:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("\n✅ server.py guardado con endpoint temporal de comparacion")
    print("   git add server.py && git commit -m 'temp: endpoint comparar_strikes solo lectura' && git push origin main")

