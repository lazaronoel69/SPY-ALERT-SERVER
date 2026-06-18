# fix_contratos.py — Seleccion de contratos en Telegram v8.71
# 1. Botones: [✅ x1] [📦 x2-10] [🏇 DERBY] — sin IGNORAR
# 2. exec_multi → edita mensaje con botones [2]...[10]
# 3. exec_c:{orden_id}:{contratos} → ejecuta con cantidad elegida
# Corre desde: /Users/noellazaro/SPY-ALERT-SERVER/

import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

# ═══════════════════════════════════════════════════════
# CAMBIO 1 — enviar_telegram_botones(): nuevos botones
# ═══════════════════════════════════════════════════════
OLD_BOTONES = '''    botones = [
        {"text": "✅ EJECUTAR", "callback_data": f"exec:{orden_id}"},
        {"text": "❌ IGNORAR",  "callback_data": f"skip:{orden_id}"},
    ]
    if derby_activo and caballo_disponible:
        botones.insert(1, {"text": f"🏇 {caballo_nombre}", "callback_data": f"reto:{orden_id}:{caballo_disponible}"})'''

NEW_BOTONES = '''    botones = [
        {"text": "✅ x1",     "callback_data": f"exec_c:{orden_id}:1"},
        {"text": "📦 x2-10", "callback_data": f"exec_multi:{orden_id}"},
    ]
    if derby_activo and caballo_disponible:
        botones.insert(2, {"text": "🏇 DERBY", "callback_data": f"reto:{orden_id}:{caballo_disponible}"})'''

if OLD_BOTONES not in content:
    errors.append("CAMBIO 1: bloque botones en enviar_telegram_botones no encontrado")
else:
    content = content.replace(OLD_BOTONES, NEW_BOTONES, 1)
    print("✅ Cambio 1: botones actualizados — x1, x2-10, DERBY")

# ═══════════════════════════════════════════════════════
# CAMBIO 2 — webhook: nueva accion exec_multi
# ═══════════════════════════════════════════════════════
OLD_EXEC = '''        if accion == "exec":
            datos = ordenes_pendientes.pop(orden_id, None)
            guardar_ordenes()
            if not datos:
                editar_mensaje("⚠️ <b>Orden expirada o ya procesada.</b>")
                return jsonify({"ok": True}), 200
            opcion     = datos["opcion"]
            estrategia = datos.get("estrategia", "AXIS")
            resultado_tradier = ejecutar_orden_tradier(opcion)
            tradier_orden_id = resultado_tradier.get("id") if resultado_tradier["ok"] else None
            tradier_gtc_id   = resultado_tradier.get("venta_id") if resultado_tradier["ok"] else None
            registrar_posicion(opcion, estrategia, opcion["subyacente"], opcion["ask"],
                               tradier_orden_id=tradier_orden_id, tradier_gtc_id=tradier_gtc_id)
            estado_tradier = "✅ Orden enviada a sandbox" if resultado_tradier["ok"] else f"⚠️ Error Tradier: {resultado_tradier.get('error','')}"
            agregar_recibo(
                f"━━━━━━━━━━━━━━━━━━\\n"
                f"✅ <b>EJECUTADA</b> — registrada en Portfolio\\n"
                f"📋 <b>Opción:</b> {opcion['symbol']}\\n"
                f"💰 <b>Costo:</b> ${opcion['ask']*100:.2f} | <b>GTC:</b> ${opcion['ask']*2:.2f}\\n"
                f"🏦 <b>Tradier:</b> {estado_tradier}"
            )'''

NEW_EXEC = '''        if accion == "exec_multi":
            # Mostrar menu de contratos 2-10
            if orden_id not in ordenes_pendientes:
                editar_mensaje("⚠️ <b>Orden expirada o ya procesada.</b>")
                return jsonify({"ok": True}), 200
            fila1 = [{"text": str(i), "callback_data": f"exec_c:{orden_id}:{i}"} for i in range(2, 7)]
            fila2 = [{"text": str(i), "callback_data": f"exec_c:{orden_id}:{i}"} for i in range(7, 11)]
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageReplyMarkup",
                json={"chat_id": chat_id, "message_id": message_id,
                      "reply_markup": {"inline_keyboard": [fila1, fila2]}},
                timeout=5
            )

        elif accion == "exec_c":
            # Ejecutar con cantidad elegida
            contratos = int(partes[2]) if len(partes) >= 3 else 1
            datos = ordenes_pendientes.pop(orden_id, None)
            guardar_ordenes()
            if not datos:
                editar_mensaje("⚠️ <b>Orden expirada o ya procesada.</b>")
                return jsonify({"ok": True}), 200
            opcion     = datos["opcion"]
            estrategia = datos.get("estrategia", "AXIS")
            resultado_tradier = ejecutar_orden_tradier_contratos(opcion, contratos)
            tradier_orden_id = resultado_tradier.get("id") if resultado_tradier["ok"] else None
            tradier_gtc_id   = resultado_tradier.get("venta_id") if resultado_tradier["ok"] else None
            costo_total = round(opcion["ask"] * 100 * contratos, 2)
            registrar_posicion(opcion, estrategia, opcion["subyacente"], opcion["ask"],
                               contratos=contratos,
                               tradier_orden_id=tradier_orden_id, tradier_gtc_id=tradier_gtc_id)
            estado_tradier = "✅ Orden enviada a sandbox" if resultado_tradier["ok"] else f"⚠️ Error Tradier: {resultado_tradier.get('error','')}"
            agregar_recibo(
                f"━━━━━━━━━━━━━━━━━━\\n"
                f"✅ <b>EJECUTADA</b> — {contratos} contrato{'s' if contratos > 1 else ''}\\n"
                f"📋 <b>Opción:</b> {opcion['symbol']}\\n"
                f"📊 <b>Contratos:</b> {contratos} × ${opcion['ask']:.2f} = ${costo_total:.2f}\\n"
                f"🎯 <b>GTC:</b> ${opcion['ask']*2:.2f} (+100%)\\n"
                f"🏦 <b>Tradier:</b> {estado_tradier}"
            )

        elif accion == "exec":
            datos = ordenes_pendientes.pop(orden_id, None)
            guardar_ordenes()
            if not datos:
                editar_mensaje("⚠️ <b>Orden expirada o ya procesada.</b>")
                return jsonify({"ok": True}), 200
            opcion     = datos["opcion"]
            estrategia = datos.get("estrategia", "AXIS")
            resultado_tradier = ejecutar_orden_tradier(opcion)
            tradier_orden_id = resultado_tradier.get("id") if resultado_tradier["ok"] else None
            tradier_gtc_id   = resultado_tradier.get("venta_id") if resultado_tradier["ok"] else None
            registrar_posicion(opcion, estrategia, opcion["subyacente"], opcion["ask"],
                               tradier_orden_id=tradier_orden_id, tradier_gtc_id=tradier_gtc_id)
            estado_tradier = "✅ Orden enviada a sandbox" if resultado_tradier["ok"] else f"⚠️ Error Tradier: {resultado_tradier.get('error','')}"
            agregar_recibo(
                f"━━━━━━━━━━━━━━━━━━\\n"
                f"✅ <b>EJECUTADA</b> — registrada en Portfolio\\n"
                f"📋 <b>Opción:</b> {opcion['symbol']}\\n"
                f"💰 <b>Costo:</b> ${opcion['ask']*100:.2f} | <b>GTC:</b> ${opcion['ask']*2:.2f}\\n"
                f"🏦 <b>Tradier:</b> {estado_tradier}"
            )'''

if OLD_EXEC not in content:
    errors.append("CAMBIO 2: bloque accion exec en webhook no encontrado")
else:
    content = content.replace(OLD_EXEC, NEW_EXEC, 1)
    print("✅ Cambio 2: acciones exec_multi y exec_c agregadas al webhook")

# ═══════════════════════════════════════════════════════
# CAMBIO 3 — Version v8.71
# ═══════════════════════════════════════════════════════
content = content.replace('AXIS Breakout Sentinel v8.70', 'AXIS Breakout Sentinel v8.71')
content = content.replace('"sistema": "AXIS Breakout Sentinel v8.70"', '"sistema": "AXIS Breakout Sentinel v8.71"')
content = content.replace('print("AXIS Breakout Sentinel v8.70 iniciado...")', 'print("AXIS Breakout Sentinel v8.71 iniciado...")')
print("✅ Cambio 3: versión v8.71")

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
    print("\n✅ server.py v8.71 guardado — seleccion contratos en Telegram")
    print("   git add server.py && git commit -m 'feat: seleccion contratos 1-10 en Telegram v8.71' && git push origin main")

