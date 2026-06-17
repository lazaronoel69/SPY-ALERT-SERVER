# fix_derby.py — Implementa REAL LAZARO-PALMA Derby v8.65
# Corre desde: /Users/noellazaro/SPY-ALERT-SERVER/
# Uso: python3 fix_derby.py

import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

# ═══════════════════════════════════════════════════════
# CAMBIO 1 — portfolio_vacio(): reemplazar 10 carriles por 4 caballos
# ═══════════════════════════════════════════════════════
OLD_PORTFOLIO_VACIO = '''def portfolio_vacio():
    return {
        "posiciones":  [],
        "historial":   [],
        "reto": {
            "activo":          False,
            "turno_actual":    1,
            "carriles": [
                {
                    "id":              i+1,
                    "capital":         0,
                    "capital_inicial": 0,
                    "ronda":           0,
                    "posicion":        None,
                    "eliminado":       False,
                    "historial":       []
                }
                for i in range(10)
            ]
        }
    }'''

NEW_PORTFOLIO_VACIO = '''DERBY_CABALLOS = [
    {"id": 1, "nombre": "Noel"},
    {"id": 2, "nombre": "Paula"},
    {"id": 3, "nombre": "Noel Andres"},
    {"id": 4, "nombre": "Emilia"},
]

def portfolio_vacio():
    return {
        "posiciones":  [],
        "historial":   [],
        "derby": {
            "nombre":          "REAL LAZARO-PALMA",
            "activo":          False,
            "turno_actual":    1,
            "ganador":         None,
            "esperando_cierre": False,
            "caballos": [
                {
                    "id":              c["id"],
                    "nombre":          c["nombre"],
                    "capital":         0,
                    "capital_inicial": 0,
                    "ronda":           0,
                    "posicion":        None,
                    "eliminado":       False,
                    "historial":       []
                }
                for c in DERBY_CABALLOS
            ]
        }
    }'''

if OLD_PORTFOLIO_VACIO not in content:
    errors.append("CAMBIO 1: portfolio_vacio() no encontrado")
else:
    content = content.replace(OLD_PORTFOLIO_VACIO, NEW_PORTFOLIO_VACIO, 1)
    print("✅ Cambio 1: portfolio_vacio() reemplazado con 4 caballos")

# ═══════════════════════════════════════════════════════
# CAMBIO 2 — analizar_portfolio_claude(): actualizar referencia reto→derby
# ═══════════════════════════════════════════════════════
OLD_CLAUDE_RETO = '''    if not posiciones and not any(c["posicion"] for c in reto["carriles"]):
        return "Sin posiciones abiertas para analizar."'''

NEW_CLAUDE_RETO = '''    derby = reto  # derby recibe el objeto derby
    if not posiciones and not any(c["posicion"] for c in derby.get("caballos", [])):
        return "Sin posiciones abiertas para analizar."'''

if OLD_CLAUDE_RETO not in content:
    errors.append("CAMBIO 2: referencia reto carriles en claude no encontrada")
else:
    content = content.replace(OLD_CLAUDE_RETO, NEW_CLAUDE_RETO, 1)
    print("✅ Cambio 2: analizar_portfolio_claude() actualizado")

# ═══════════════════════════════════════════════════════
# CAMBIO 3 — analizar_portfolio_claude(): capital_reto→derby
# ═══════════════════════════════════════════════════════
OLD_CAPITAL_RETO = '''        capital_reto = sum(c["capital"] for c in reto["carriles"])'''
NEW_CAPITAL_RETO = '''        capital_reto = sum(c["capital"] for c in reto.get("caballos", []))'''

if OLD_CAPITAL_RETO not in content:
    errors.append("CAMBIO 3: capital_reto suma no encontrada")
else:
    content = content.replace(OLD_CAPITAL_RETO, NEW_CAPITAL_RETO, 1)
    print("✅ Cambio 3: capital_reto actualizado a caballos")

# ═══════════════════════════════════════════════════════
# CAMBIO 4 — cerrar_posicion(): reemplazar lógica carriles por caballos
# ═══════════════════════════════════════════════════════
OLD_CERRAR_RETO = '''    if pos.get("es_reto") and pos.get("carril_id"):
        for c in _portfolio["reto"]["carriles"]:
            if c["id"] == pos["carril_id"]:
                nuevo_capital = round(c["capital"] + pl_usd, 2)
                c["capital"]  = nuevo_capital
                c["posicion"] = None
                c["historial"].append({
                    "ronda":         c["ronda"],
                    "pl_usd":        pl_usd,
                    "pl_pct":        pl_pct,
                    "capital_final": nuevo_capital,
                    "motivo":        motivo,
                })
                CAPITAL_MINIMO = 280
                if nuevo_capital < CAPITAL_MINIMO:
                    c["eliminado"] = True
                    enviar_telegram(
                        f"💀 <b>Carril #{c['id']} ELIMINADO</b>\\n"
                        f"Capital final: ${nuevo_capital:.2f} — insuficiente para siguiente ronda\\n"
                        f"Capital inicial fue: ${c.get('capital_inicial', 0):.2f}"
                    )
                break'''

NEW_CERRAR_RETO = '''    if pos.get("es_reto") and pos.get("carril_id"):
        derby = _portfolio["derby"]
        for c in derby["caballos"]:
            if c["id"] == pos["carril_id"]:
                nuevo_capital = round(c["capital"] + pl_usd, 2)
                c["capital"]  = nuevo_capital
                c["posicion"] = None
                c["historial"].append({
                    "ronda":         c["ronda"],
                    "pl_usd":        pl_usd,
                    "pl_pct":        pl_pct,
                    "capital_final": nuevo_capital,
                    "motivo":        motivo,
                })
                CAPITAL_MINIMO = 280
                if nuevo_capital < CAPITAL_MINIMO:
                    c["eliminado"] = True
                    enviar_telegram(
                        f"💀 <b>{c['nombre']} ELIMINADO — REAL LAZARO-PALMA</b>\\n"
                        f"Capital final: ${nuevo_capital:.2f} — insuficiente para siguiente carrera\\n"
                        f"Capital inicial fue: ${c.get('capital_inicial', 0):.2f}"
                    )
                # Verificar si queda un solo caballo vivo
                vivos = [x for x in derby["caballos"] if not x.get("eliminado")]
                if len(vivos) == 1 and derby["activo"]:
                    ganador = vivos[0]
                    derby["ganador"] = ganador["nombre"]
                    derby["activo"]  = False
                    if ganador["capital"] > 0 and ganador["posicion"] is not None:
                        derby["esperando_cierre"] = True
                        enviar_telegram(
                            f"🏆 <b>GANADOR DEL REAL LAZARO-PALMA: {ganador['nombre']}</b>\\n"
                            f"Capital acumulado: ${ganador['capital']:.2f}\\n"
                            f"⏳ Esperando cierre de posición para confirmar premio final..."
                        )
                    else:
                        derby["esperando_cierre"] = False
                        enviar_telegram(
                            f"🏆 <b>GANADOR DEL REAL LAZARO-PALMA: {ganador['nombre']}</b>\\n"
                            f"Premio metálico: ${ganador['capital']:.2f}\\n"
                            f"🏇 Derby finalizado — activa uno nuevo cuando quieras"
                        )
                break'''

if OLD_CERRAR_RETO not in content:
    errors.append("CAMBIO 4: lógica cerrar_posicion reto no encontrada")
else:
    content = content.replace(OLD_CERRAR_RETO, NEW_CERRAR_RETO, 1)
    print("✅ Cambio 4: cerrar_posicion() actualizado con lógica derby y ganador")

# ═══════════════════════════════════════════════════════
# CAMBIO 5 — enviar_telegram_botones(): reto→derby
# ═══════════════════════════════════════════════════════
OLD_BOTONES = '''def enviar_telegram_botones(mensaje, orden_id):
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    reto_activo = _portfolio["reto"]["activo"]
    carril_disponible = None
    if reto_activo:
        turno = _portfolio["reto"].get("turno_actual", 1)
        carriles = _portfolio["reto"]["carriles"]
        orden = list(range(turno - 1, 10)) + list(range(0, turno - 1))
        for idx in orden:
            c = carriles[idx]
            if not c.get("eliminado") and c["posicion"] is None:
                carril_disponible = c["id"]
                break
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    botones = [
        {"text": "✅ EJECUTAR", "callback_data": f"exec:{orden_id}"},
        {"text": "❌ IGNORAR",  "callback_data": f"skip:{orden_id}"},
    ]
    if reto_activo and carril_disponible:
        botones.insert(1, {"text": f"🏆 RETO C{carril_disponible}", "callback_data": f"reto:{orden_id}:{carril_disponible}"})'''

NEW_BOTONES = '''def enviar_telegram_botones(mensaje, orden_id):
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    derby = _portfolio["derby"]
    derby_activo = derby["activo"]
    caballo_disponible = None
    caballo_nombre = None
    if derby_activo:
        turno = derby.get("turno_actual", 1)
        caballos = derby["caballos"]
        orden = list(range(turno - 1, 4)) + list(range(0, turno - 1))
        for idx in orden:
            c = caballos[idx]
            if not c.get("eliminado") and c["posicion"] is None:
                caballo_disponible = c["id"]
                caballo_nombre = c["nombre"]
                break
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    botones = [
        {"text": "✅ EJECUTAR", "callback_data": f"exec:{orden_id}"},
        {"text": "❌ IGNORAR",  "callback_data": f"skip:{orden_id}"},
    ]
    if derby_activo and caballo_disponible:
        botones.insert(1, {"text": f"🏇 {caballo_nombre}", "callback_data": f"reto:{orden_id}:{caballo_disponible}"})'''

if OLD_BOTONES not in content:
    errors.append("CAMBIO 5: enviar_telegram_botones no encontrado")
else:
    content = content.replace(OLD_BOTONES, NEW_BOTONES, 1)
    print("✅ Cambio 5: enviar_telegram_botones() actualizado con nombres de caballos")

# ═══════════════════════════════════════════════════════
# CAMBIO 6 — webhook accion=="reto": actualizar lógica derby
# ═══════════════════════════════════════════════════════
OLD_WEBHOOK_RETO = '''        elif accion == "reto":
            carril_id = carril_id_reto or 1
            datos = ordenes_pendientes.pop(orden_id, None)
            guardar_ordenes()
            if not datos:
                editar_mensaje("⚠️ <b>Orden expirada o ya procesada.</b>")
                return jsonify({"ok": True}), 200
            opcion     = datos["opcion"]
            estrategia = datos.get("estrategia", "AXIS")
            carril = next((c for c in _portfolio["reto"]["carriles"] if c["id"] == carril_id), None)
            if not carril or carril.get("eliminado"):
                agregar_recibo(f"━━━━━━━━━━━━━━━━━━\\n⚠️ <b>Carril #{carril_id} no disponible</b>")
                return jsonify({"ok": True}), 200
            if carril["posicion"] is not None:
                turno = carril_id + 1
                nuevo_id = None
                orden_b  = list(range(turno - 1, 10)) + list(range(0, turno - 1))
                for idx in orden_b:
                    c = _portfolio["reto"]["carriles"][idx]
                    if not c.get("eliminado") and c["posicion"] is None:
                        nuevo_id = c["id"]
                        break
                if not nuevo_id:
                    agregar_recibo(f"━━━━━━━━━━━━━━━━━━\\n⚠️ <b>Sin carriles disponibles</b>")
                    return jsonify({"ok": True}), 200
                carril_id = nuevo_id
                carril    = next((c for c in _portfolio["reto"]["carriles"] if c["id"] == carril_id), None)
            costo_1cont = round(opcion["ask"] * 100, 2)
            if carril["capital"] == 0:
                carril["capital"]         = costo_1cont
                carril["capital_inicial"] = costo_1cont
                contratos   = 1
                presupuesto = costo_1cont
            else:
                presupuesto = round(carril["capital"] * 0.80, 2)
                if costo_1cont > presupuesto:
                    opcion_reto = buscar_opcion_reto(opcion, presupuesto)
                    if not opcion_reto:
                        rec_claude = recomendar_opcion_claude(opcion, carril["capital"], presupuesto)
                        agregar_recibo(
                            f"━━━━━━━━━━━━━━━━━━\\n"
                            f"⚠️ <b>Capital insuficiente — Carril #{carril_id}</b>\\n"
                            f"Capital: ${carril['capital']:.2f} | Presupuesto: ${presupuesto:.2f}\\n"
                            f"🤖 <b>Claude recomienda:</b>\\n{rec_claude}"
                        )
                        return jsonify({"ok": True}), 200
                    opcion = opcion_reto
                    costo_1cont = round(opcion["ask"] * 100, 2)
                contratos = max(1, int(presupuesto // costo_1cont))
            carriles = _portfolio["reto"]["carriles"]
            siguiente = None
            orden = list(range(carril_id, 10)) + list(range(0, carril_id))
            for idx in orden:
                c = carriles[idx]
                if not c.get("eliminado") and c["posicion"] is None and c["id"] != carril_id:
                    siguiente = c["id"]
                    break
            _portfolio["reto"]["turno_actual"] = siguiente if siguiente else carril_id
            resultado_tradier = ejecutar_orden_tradier_contratos(opcion, contratos)
            tradier_orden_id = resultado_tradier.get("id")    if resultado_tradier["ok"] else None
            tradier_gtc_id   = resultado_tradier.get("venta_id") if resultado_tradier["ok"] else None
            costo_total = round(opcion["ask"] * 100 * contratos, 2)
            registrar_posicion(opcion, estrategia, opcion["subyacente"], opcion["ask"],
                               es_reto=True, carril_id=carril_id, contratos=contratos,
                               tradier_orden_id=tradier_orden_id, tradier_gtc_id=tradier_gtc_id)
            estado_tradier = "✅ Orden enviada a sandbox" if resultado_tradier["ok"] else f"⚠️ Error: {resultado_tradier.get('error','')}"
            es_primera = carril["capital_inicial"] == costo_1cont and carril["ronda"] == 1
            agregar_recibo(
                f"━━━━━━━━━━━━━━━━━━\\n"
                f"🏆 <b>RETO C{carril_id} — {'PRIMERA ENTRADA' if es_primera else 'EJECUTADO'}</b>\\n"
                f"📋 <b>Opción:</b> {opcion['symbol']}\\n"
                f"📊 <b>Contratos:</b> {contratos} × ${opcion['ask']:.2f} = ${costo_total:.2f}\\n"
                f"💰 <b>Capital carril:</b> ${carril['capital']:.2f}\\n"
                f"🎯 <b>GTC:</b> ${opcion['ask']*2:.2f} (+100%)\\n"
                f"🔄 <b>Siguiente turno:</b> C{_portfolio['reto']['turno_actual']}\\n"
                f"🏦 <b>Tradier:</b> {estado_tradier}"
            )'''

NEW_WEBHOOK_RETO = '''        elif accion == "reto":
            caballo_id = carril_id_reto or 1
            datos = ordenes_pendientes.pop(orden_id, None)
            guardar_ordenes()
            if not datos:
                editar_mensaje("⚠️ <b>Orden expirada o ya procesada.</b>")
                return jsonify({"ok": True}), 200
            opcion     = datos["opcion"]
            estrategia = datos.get("estrategia", "AXIS")
            derby = _portfolio["derby"]
            caballo = next((c for c in derby["caballos"] if c["id"] == caballo_id), None)
            if not caballo or caballo.get("eliminado"):
                # Buscar siguiente disponible
                nuevo_id = None
                for c in derby["caballos"]:
                    if not c.get("eliminado") and c["posicion"] is None:
                        nuevo_id = c["id"]
                        break
                if not nuevo_id:
                    agregar_recibo(f"━━━━━━━━━━━━━━━━━━\\n⚠️ <b>Todos los caballos ocupados o eliminados</b>")
                    return jsonify({"ok": True}), 200
                caballo_id = nuevo_id
                caballo    = next((c for c in derby["caballos"] if c["id"] == caballo_id), None)
            if caballo["posicion"] is not None:
                # Buscar otro caballo libre
                nuevo_id = None
                for c in derby["caballos"]:
                    if not c.get("eliminado") and c["posicion"] is None and c["id"] != caballo_id:
                        nuevo_id = c["id"]
                        break
                if not nuevo_id:
                    agregar_recibo(f"━━━━━━━━━━━━━━━━━━\\n⚠️ <b>Todos los caballos en carrera</b>")
                    return jsonify({"ok": True}), 200
                caballo_id = nuevo_id
                caballo    = next((c for c in derby["caballos"] if c["id"] == caballo_id), None)
            costo_1cont = round(opcion["ask"] * 100, 2)
            if caballo["capital"] == 0:
                # Primera carrera — sin límite de capital
                caballo["capital"]         = costo_1cont
                caballo["capital_inicial"] = costo_1cont
                contratos   = 1
                presupuesto = costo_1cont
            else:
                # Carreras siguientes — usa capital acumulado
                presupuesto = round(caballo["capital"] * 0.80, 2)
                if costo_1cont > presupuesto:
                    opcion_reto = buscar_opcion_reto(opcion, presupuesto)
                    if not opcion_reto:
                        rec_claude = recomendar_opcion_claude(opcion, caballo["capital"], presupuesto)
                        agregar_recibo(
                            f"━━━━━━━━━━━━━━━━━━\\n"
                            f"⚠️ <b>Capital insuficiente — {caballo['nombre']}</b>\\n"
                            f"Capital: ${caballo['capital']:.2f} | Presupuesto: ${presupuesto:.2f}\\n"
                            f"🤖 <b>Claude recomienda:</b>\\n{rec_claude}"
                        )
                        return jsonify({"ok": True}), 200
                    opcion = opcion_reto
                    costo_1cont = round(opcion["ask"] * 100, 2)
                contratos = max(1, int(presupuesto // costo_1cont))
            # Actualizar turno al siguiente caballo disponible
            siguiente = None
            for c in derby["caballos"]:
                if not c.get("eliminado") and c["posicion"] is None and c["id"] != caballo_id:
                    siguiente = c["id"]
                    break
            derby["turno_actual"] = siguiente if siguiente else caballo_id
            resultado_tradier = ejecutar_orden_tradier_contratos(opcion, contratos)
            tradier_orden_id = resultado_tradier.get("id")    if resultado_tradier["ok"] else None
            tradier_gtc_id   = resultado_tradier.get("venta_id") if resultado_tradier["ok"] else None
            costo_total = round(opcion["ask"] * 100 * contratos, 2)
            registrar_posicion(opcion, estrategia, opcion["subyacente"], opcion["ask"],
                               es_reto=True, carril_id=caballo_id, contratos=contratos,
                               tradier_orden_id=tradier_orden_id, tradier_gtc_id=tradier_gtc_id)
            caballo["ronda"] += 1
            estado_tradier = "✅ Orden enviada a sandbox" if resultado_tradier["ok"] else f"⚠️ Error: {resultado_tradier.get('error','')}"
            es_primera = caballo["ronda"] == 1
            agregar_recibo(
                f"━━━━━━━━━━━━━━━━━━\\n"
                f"🏇 <b>{caballo['nombre']} — {'PRIMERA CARRERA' if es_primera else f'CARRERA #{caballo[chr(114)+chr(111)+chr(110)+chr(100)+chr(97)]}'}</b>\\n"
                f"📋 <b>Opción:</b> {opcion['symbol']}\\n"
                f"📊 <b>Contratos:</b> {contratos} × ${opcion['ask']:.2f} = ${costo_total:.2f}\\n"
                f"💰 <b>Capital:</b> ${caballo['capital']:.2f}\\n"
                f"🎯 <b>GTC:</b> ${opcion['ask']*2:.2f} (+100%)\\n"
                f"🔄 <b>Siguiente:</b> {next((x['nombre'] for x in derby['caballos'] if x['id'] == derby['turno_actual']), 'N/A')}\\n"
                f"🏦 <b>Tradier:</b> {estado_tradier}"
            )'''

if OLD_WEBHOOK_RETO not in content:
    errors.append("CAMBIO 6: webhook accion reto no encontrado")
else:
    content = content.replace(OLD_WEBHOOK_RETO, NEW_WEBHOOK_RETO, 1)
    print("✅ Cambio 6: webhook derby actualizado")

# ═══════════════════════════════════════════════════════
# CAMBIO 7 — /portfolio/reto/activar → /derby/activar
# ═══════════════════════════════════════════════════════
OLD_RETO_ACTIVAR = '''@app.route("/portfolio/reto/activar", methods=["GET"])
def reto_activar():
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    _portfolio["reto"]["activo"] = True
    guardar_portfolio()
    enviar_telegram("🏆 <b>Reto Millonario ACTIVADO</b>\\n10 carriles × $200 = $2,000\\n¡A duplicar!")
    return jsonify({"ok": True, "reto": _portfolio["reto"]}), 200

@app.route("/portfolio/reto/desactivar", methods=["GET"])
def reto_desactivar():
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    _portfolio["reto"]["activo"] = False
    guardar_portfolio()
    enviar_telegram("⏸ <b>Reto Millonario PAUSADO</b>")
    return jsonify({"ok": True}), 200'''

NEW_RETO_ACTIVAR = '''@app.route("/derby/activar", methods=["GET"])
def derby_activar():
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    derby = _portfolio["derby"]
    derby["activo"]           = True
    derby["ganador"]          = None
    derby["esperando_cierre"] = False
    derby["turno_actual"]     = 1
    # Resetear caballos
    for c in derby["caballos"]:
        c["capital"]         = 0
        c["capital_inicial"] = 0
        c["ronda"]           = 0
        c["posicion"]        = None
        c["eliminado"]       = False
        c["historial"]       = []
    guardar_portfolio()
    enviar_telegram(
        f"🏇 <b>REAL LAZARO-PALMA — NUEVO DERBY ACTIVADO</b>\\n"
        f"Caballos: Noel · Paula · Noel Andrés · Emilia\\n"
        f"¡Que gane el mejor!"
    )
    return jsonify({"ok": True, "derby": _portfolio["derby"]}), 200

@app.route("/derby/desactivar", methods=["GET"])
def derby_desactivar():
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    _portfolio["derby"]["activo"] = False
    guardar_portfolio()
    enviar_telegram("⏸ <b>REAL LAZARO-PALMA PAUSADO</b>")
    return jsonify({"ok": True}), 200

@app.route("/derby/status", methods=["GET"])
def derby_status():
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    derby = _portfolio["derby"]
    caballos_info = []
    for c in derby["caballos"]:
        caballos_info.append({
            "id":       c["id"],
            "nombre":   c["nombre"],
            "capital":  c["capital"],
            "ronda":    c["ronda"],
            "posicion": c["posicion"],
            "eliminado": c.get("eliminado", False),
            "historial": c.get("historial", []),
        })
    return jsonify({
        "nombre":           derby["nombre"],
        "activo":           derby["activo"],
        "ganador":          derby.get("ganador"),
        "esperando_cierre": derby.get("esperando_cierre", False),
        "turno_actual":     derby.get("turno_actual", 1),
        "caballos":         caballos_info,
    }), 200

# Mantener compatibilidad con rutas antiguas
@app.route("/portfolio/reto/activar", methods=["GET"])
def reto_activar():
    return derby_activar()

@app.route("/portfolio/reto/desactivar", methods=["GET"])
def reto_desactivar():
    return derby_desactivar()'''

if OLD_RETO_ACTIVAR not in content:
    errors.append("CAMBIO 7: rutas reto/activar no encontradas")
else:
    content = content.replace(OLD_RETO_ACTIVAR, NEW_RETO_ACTIVAR, 1)
    print("✅ Cambio 7: endpoints derby/activar, derby/status creados")

# ═══════════════════════════════════════════════════════
# CAMBIO 8 — /status endpoint: reto→derby
# ═══════════════════════════════════════════════════════
OLD_STATUS_RETO = '''    reto = _portfolio["reto"]
    carriles_vivos = [c for c in reto["carriles"] if not c.get("eliminado")]
    reto_resumen = {
        "activo": reto["activo"], "turno_actual": reto.get("turno_actual", 1),
        "carriles_vivos": len(carriles_vivos),
        "capital_total": round(sum(c["capital"] for c in carriles_vivos), 2),
    }'''

NEW_STATUS_RETO = '''    derby = _portfolio.get("derby", _portfolio.get("reto", {}))
    caballos_vivos = [c for c in derby.get("caballos", derby.get("carriles", [])) if not c.get("eliminado")]
    reto_resumen = {
        "activo": derby.get("activo", False),
        "turno_actual": derby.get("turno_actual", 1),
        "carriles_vivos": len(caballos_vivos),
        "capital_total": round(sum(c["capital"] for c in caballos_vivos), 2),
        "ganador": derby.get("ganador"),
    }'''

if OLD_STATUS_RETO not in content:
    errors.append("CAMBIO 8: status reto resumen no encontrado")
else:
    content = content.replace(OLD_STATUS_RETO, NEW_STATUS_RETO, 1)
    print("✅ Cambio 8: /status actualizado para derby")

# ═══════════════════════════════════════════════════════
# CAMBIO 9 — portfolio_data(): reto→derby
# ═══════════════════════════════════════════════════════
OLD_PORTFOLIO_DATA = '''    return jsonify({
        "posiciones": _portfolio["posiciones"],
        "historial":  _portfolio["historial"][-20:],
        "reto":       _portfolio["reto"],
    }), 200'''

NEW_PORTFOLIO_DATA = '''    return jsonify({
        "posiciones": _portfolio["posiciones"],
        "historial":  _portfolio["historial"][-20:],
        "derby":      _portfolio.get("derby", {}),
        "reto":       _portfolio.get("derby", {}),  # compatibilidad
    }), 200'''

if OLD_PORTFOLIO_DATA not in content:
    errors.append("CAMBIO 9: portfolio_data return no encontrado")
else:
    content = content.replace(OLD_PORTFOLIO_DATA, NEW_PORTFOLIO_DATA, 1)
    print("✅ Cambio 9: portfolio/data actualizado")

# ═══════════════════════════════════════════════════════
# CAMBIO 10 — resumen diario: carriles→caballos
# ═══════════════════════════════════════════════════════
OLD_RESUMEN = '''        reto   = _portfolio["reto"]
        cap_reto = sum(c["capital"] for c in reto["carriles"] if not c.get("eliminado"))
        vivos  = sum(1 for c in reto["carriles"] if not c.get("eliminado"))'''

NEW_RESUMEN = '''        reto   = _portfolio.get("derby", _portfolio.get("reto", {}))
        cap_reto = sum(c["capital"] for c in reto.get("caballos", reto.get("carriles", [])) if not c.get("eliminado"))
        vivos  = sum(1 for c in reto.get("caballos", reto.get("carriles", [])) if not c.get("eliminado"))'''

if OLD_RESUMEN not in content:
    errors.append("CAMBIO 10: resumen diario reto no encontrado")
else:
    content = content.replace(OLD_RESUMEN, NEW_RESUMEN, 1)
    print("✅ Cambio 10: resumen diario actualizado")

# ═══════════════════════════════════════════════════════
# CAMBIO 11 — Homepage: agregar card Derby
# ═══════════════════════════════════════════════════════
OLD_HOME_CARDS = '''    <a href="/analisis" class="nav-card" style="border-color:#1a3a2a;">
      <div class="icon">📈</div>
      <div class="title">Análisis</div>
      <div class="desc">Historial · Win Rate · Comportamiento</div>
    </a>
    <a href="/bitacora" class="nav-card bitacora">
      <div class="icon">📋</div>
      <div class="title">Bitácora</div>
      <div class="desc">Pendientes · Decisiones · Seguimiento</div>
    </a>'''

NEW_HOME_CARDS = '''    <a href="/analisis" class="nav-card" style="border-color:#1a3a2a;">
      <div class="icon">📈</div>
      <div class="title">Análisis</div>
      <div class="desc">Historial · Win Rate · Comportamiento</div>
    </a>
    <a href="/bitacora" class="nav-card bitacora">
      <div class="icon">📋</div>
      <div class="title">Bitácora</div>
      <div class="desc">Pendientes · Decisiones · Seguimiento</div>
    </a>
    <a href="/derby" class="nav-card" style="border-color:#3d0000; grid-column: 1 / -1;">
      <div class="icon">🏇</div>
      <div class="title">REAL LAZARO-PALMA</div>
      <div class="desc">Noel · Paula · Noel Andrés · Emilia — Derby de Opciones</div>
    </a>'''

if OLD_HOME_CARDS not in content:
    errors.append("CAMBIO 11: home cards no encontradas")
else:
    content = content.replace(OLD_HOME_CARDS, NEW_HOME_CARDS, 1)
    print("✅ Cambio 11: card Derby agregada al homepage")

# ═══════════════════════════════════════════════════════
# CAMBIO 12 — Ruta /derby para servir axis_derby.html
# ═══════════════════════════════════════════════════════
OLD_CHARTS_ROUTE = '''@app.route("/charts", methods=["GET"])
def serve_charts():
    from flask import Response
    import os
    html_path = os.path.join(os.path.dirname(__file__), "axis_charts.html")'''

NEW_CHARTS_ROUTE = '''@app.route("/derby", methods=["GET"])
def serve_derby():
    from flask import Response
    import os
    html_path = os.path.join(os.path.dirname(__file__), "axis_derby.html")
    if os.path.exists(html_path):
        with open(html_path, "r") as f:
            return Response(f.read(), mimetype="text/html")
    return Response("<h1>axis_derby.html no encontrado</h1>", mimetype="text/html"), 404

@app.route("/charts", methods=["GET"])
def serve_charts():
    from flask import Response
    import os
    html_path = os.path.join(os.path.dirname(__file__), "axis_charts.html")'''

if OLD_CHARTS_ROUTE not in content:
    errors.append("CAMBIO 12: ruta /charts no encontrada para insertar /derby")
else:
    content = content.replace(OLD_CHARTS_ROUTE, NEW_CHARTS_ROUTE, 1)
    print("✅ Cambio 12: ruta /derby agregada")

# ═══════════════════════════════════════════════════════
# CAMBIO 13 — cargar_portfolio(): migrar reto→derby si existe
# ═══════════════════════════════════════════════════════
OLD_CARGAR_PORTFOLIO = '''def cargar_portfolio():
    global _portfolio
    try:
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE, 'r') as f:
                _portfolio = json.load(f)
            print(f"Portfolio cargado — {len(_portfolio['posiciones'])} posiciones abiertas")
        else:
            _portfolio = portfolio_vacio()
            guardar_portfolio()
            print("Portfolio nuevo creado")
    except Exception as e:
        print(f"Error cargando portfolio: {e}")
        _portfolio = portfolio_vacio()'''

NEW_CARGAR_PORTFOLIO = '''def cargar_portfolio():
    global _portfolio
    try:
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE, 'r') as f:
                _portfolio = json.load(f)
            # Migrar reto→derby si viene de versión anterior
            if "reto" in _portfolio and "derby" not in _portfolio:
                vacio = portfolio_vacio()
                _portfolio["derby"] = vacio["derby"]
                print("Migración: reto→derby completada")
                guardar_portfolio()
            elif "derby" not in _portfolio:
                vacio = portfolio_vacio()
                _portfolio["derby"] = vacio["derby"]
                guardar_portfolio()
            print(f"Portfolio cargado — {len(_portfolio['posiciones'])} posiciones abiertas")
        else:
            _portfolio = portfolio_vacio()
            guardar_portfolio()
            print("Portfolio nuevo creado")
    except Exception as e:
        print(f"Error cargando portfolio: {e}")
        _portfolio = portfolio_vacio()'''

if OLD_CARGAR_PORTFOLIO not in content:
    errors.append("CAMBIO 13: cargar_portfolio no encontrado")
else:
    content = content.replace(OLD_CARGAR_PORTFOLIO, NEW_CARGAR_PORTFOLIO, 1)
    print("✅ Cambio 13: cargar_portfolio() con migración reto→derby")

# ═══════════════════════════════════════════════════════
# CAMBIO 14 — Version v8.65
# ═══════════════════════════════════════════════════════
content = content.replace('AXIS Breakout Sentinel v8.64', 'AXIS Breakout Sentinel v8.65')
content = content.replace('"sistema": "AXIS Breakout Sentinel v8.64"', '"sistema": "AXIS Breakout Sentinel v8.65"')
content = content.replace('print("AXIS Breakout Sentinel v8.64 iniciado...")', 'print("AXIS Breakout Sentinel v8.65 iniciado...")')
print("✅ Cambio 14: versión v8.65")

# ═══════════════════════════════════════════════════════
# VERIFICACION FINAL
# ═══════════════════════════════════════════════════════
if errors:
    print("\n❌ ERRORES ENCONTRADOS:")
    for e in errors:
        print(f"  - {e}")
    print("\nNo se guardó el archivo.")
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("\n✅ server.py v8.65 guardado — REAL LAZARO-PALMA implementado")
    print("   Siguiente: crear axis_derby.html")
    print("   Luego: git add server.py axis_derby.html && git commit -m 'feat: REAL LAZARO-PALMA derby v8.65' && git push origin main")

