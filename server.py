#!/usr/bin/env python3
"""
SPY Alert System — Servidor completo
- Verifica y corrige P1/P2 con Yahoo Finance
- Calcula techo diagonal en tiempo real
- Reporta hora a hora al grupo de Telegram
"""

import requests
import threading
import time
import yfinance as yf
from datetime import datetime, timedelta
import pytz
from flask import Flask, jsonify

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════
# CONFIGURACION
# ═══════════════════════════════════════════════════════════
TELEGRAM_TOKEN   = "8668514895:AAG5HKGmDLr6_SM1rz3gwC6uk1Ue9iepN70"
TELEGRAM_CHAT_ID = "-5010153427"
EST              = pytz.timezone("America/New_York")

# P1 y P2 — valores iniciales del operador
P1 = { "fecha": "2026-02-26", "hora": 10, "high": 693.36 }
P2 = { "fecha": "2026-03-10", "hora": 14, "high": 683.35 }

# ═══════════════════════════════════════════════════════════
# TELEGRAM
# ═══════════════════════════════════════════════════════════
def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = { "chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML" }
    try:
        r = requests.post(url, json=payload, timeout=10)
        print(f"Telegram: {r.status_code}")
    except Exception as e:
        print(f"Error Telegram: {e}")

# ═══════════════════════════════════════════════════════════
# YAHOO FINANCE — verificar high de P1 y P2
# ═══════════════════════════════════════════════════════════
def get_high_vela(fecha_str, hora_est):
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        inicio = fecha.strftime("%Y-%m-%d")
        fin = (fecha + timedelta(days=1)).strftime("%Y-%m-%d")
        spy = yf.download("SPY", start=inicio, end=fin, interval="1h", progress=False)
        if spy.empty:
            return None
        for idx in spy.index:
            idx_est = idx.astimezone(EST)
            if idx_est.hour == hora_est:
                high_real = float(spy.loc[idx, "High"].iloc[0] if hasattr(spy.loc[idx, "High"], 'iloc') else spy.loc[idx, "High"])
                return high_real
        return None
    except Exception as e:
        print(f"Error Yahoo Finance: {e}")
        return None

# ═══════════════════════════════════════════════════════════
# VERIFICAR Y CORREGIR P1 Y P2
# ═══════════════════════════════════════════════════════════
def verificar_puntos():
    global P1, P2
    mensaje = "🔍 <b>Verificacion P1 y P2 con Yahoo Finance</b>\n\n"

    high_real_p1 = get_high_vela(P1["fecha"], P1["hora"])
    if high_real_p1:
        diff = abs(high_real_p1 - P1["high"])
        if diff > 0.10:
            mensaje += f"⚠️ <b>P1 CORREGIDO</b>\n   Operador: ${P1['high']:.2f} → Yahoo: ${high_real_p1:.2f}\n\n"
            P1["high"] = high_real_p1
        else:
            mensaje += f"✅ <b>P1 OK</b> — ${P1['high']:.2f} (Yahoo: ${high_real_p1:.2f})\n\n"
    else:
        mensaje += f"⚠️ P1 no verificado — usando ${P1['high']:.2f}\n\n"

    high_real_p2 = get_high_vela(P2["fecha"], P2["hora"])
    if high_real_p2:
        diff = abs(high_real_p2 - P2["high"])
        if diff > 0.10:
            mensaje += f"⚠️ <b>P2 CORREGIDO</b>\n   Operador: ${P2['high']:.2f} → Yahoo: ${high_real_p2:.2f}\n\n"
            P2["high"] = high_real_p2
        else:
            mensaje += f"✅ <b>P2 OK</b> — ${P2['high']:.2f} (Yahoo: ${high_real_p2:.2f})\n\n"
    else:
        mensaje += f"⚠️ P2 no verificado — usando ${P2['high']:.2f}\n\n"

    mensaje += f"📐 Techo calculado con P1=${P1['high']:.2f} y P2=${P2['high']:.2f}"
    enviar_telegram(mensaje)

# ═══════════════════════════════════════════════════════════
# CALCULAR TECHO DIAGONAL
# ═══════════════════════════════════════════════════════════
def calcular_techo_ahora():
    p1_dt = EST.localize(datetime.strptime(f"{P1['fecha']} {P1['hora']}:00", "%Y-%m-%d %H:%M"))
    p2_dt = EST.localize(datetime.strptime(f"{P2['fecha']} {P2['hora']}:00", "%Y-%m-%d %H:%M"))
    ahora = datetime.now(EST)
    pendiente = (P2["high"] - P1["high"]) / (p2_dt.timestamp() - p1_dt.timestamp())
    techo = P1["high"] + pendiente * (ahora.timestamp() - p1_dt.timestamp())
    return round(techo, 2)

# ═══════════════════════════════════════════════════════════
# OBTENER ULTIMA VELA CERRADA DE SPY
# ═══════════════════════════════════════════════════════════
def get_ultima_vela():
    try:
        spy = yf.download("SPY", period="2d", interval="1h", progress=False)
        if spy.empty or len(spy) < 2:
            return None
        ultima = spy.iloc[-2]
        return {
            "open":  float(ultima["Open"]),
            "close": float(ultima["Close"]),
            "high":  float(ultima["High"]),
            "low":   float(ultima["Low"]),
            "time":  spy.index[-2].astimezone(EST).strftime("%H:%M EST")
        }
    except Exception as e:
        print(f"Error vela: {e}")
        return None

# ═══════════════════════════════════════════════════════════
# REPORTE HORARIO
# ═══════════════════════════════════════════════════════════
def reporte_horario():
    ahora_est = datetime.now(EST)
    hora = ahora_est.hour
    if hora < 10 or hora > 16:
        print(f"Fuera de horario: {ahora_est.strftime('%H:%M EST')}")
        return

    techo = calcular_techo_ahora()
    vela  = get_ultima_vela()

    if not vela:
        enviar_telegram("⚠️ No se pudo obtener datos de SPY.")
        return

    vela_verde  = vela["close"] > vela["open"]
    cuerpo      = abs(vela["close"] - vela["open"])
    rango       = vela["high"] - vela["low"]
    mecha_sup   = vela["high"] - max(vela["close"], vela["open"])
    mecha_pct   = (mecha_sup / rango * 100) if rango > 0 else 0
    mecha_ok    = mecha_pct <= 25
    sobre_techo = vela["close"] > techo
    ruptura     = vela_verde and mecha_ok and sobre_techo

    proxima = ahora_est + timedelta(hours=1)

    if ruptura:
        mensaje = (
            f"🟢 <b>RUPTURA DEL CANAL — {ahora_est.strftime('%H:%M EST')}</b>\n\n"
            f"Vela verde limpia cerro sobre el techo.\n"
            f"<b>Techo:</b> ${techo:.2f}\n"
            f"<b>Cierre:</b> ${vela['close']:.2f}\n"
            f"<b>Mecha superior:</b> {mecha_pct:.0f}%\n\n"
            f"⚡ EVALUAR ENTRADA"
        )
    else:
        razon = []
        if not vela_verde: razon.append("vela roja")
        if not mecha_ok:   razon.append(f"mecha {mecha_pct:.0f}%")
        if not sobre_techo: razon.append(f"cierre ${vela['close']:.2f} bajo techo ${techo:.2f}")
        mensaje = (
            f"🔴 <b>Sin ruptura — {ahora_est.strftime('%H:%M EST')}</b>\n\n"
            f"<b>Techo actual:</b> ${techo:.2f}\n"
            f"<b>Cierre vela:</b> ${vela['close']:.2f}\n"
            f"<b>Vela:</b> {'Verde' if vela_verde else 'Roja'} | Mecha: {mecha_pct:.0f}%\n"
            f"<b>Razon:</b> {', '.join(razon)}\n\n"
            f"Sistema activo — proxima revision: {proxima.strftime('%H:%M EST')}"
        )

    enviar_telegram(mensaje)

# ═══════════════════════════════════════════════════════════
# LOOP PRINCIPAL — reporta a los :35 de cada hora
# ═══════════════════════════════════════════════════════════
def monitor_loop():
    print("Monitor iniciado...")
    time.sleep(5)
    verificar_puntos()
    while True:
        ahora = datetime.now(EST)
        minutos_para_35 = (35 - ahora.minute) % 60
        if minutos_para_35 == 0:
            minutos_para_35 = 60
        print(f"Proximo reporte en {minutos_para_35} min")
        time.sleep(minutos_para_35 * 60)
        reporte_horario()

# ═══════════════════════════════════════════════════════════
# RUTAS FLASK
# ═══════════════════════════════════════════════════════════
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "SPY Alert System activo"}), 200

@app.route("/test", methods=["GET"])
def test():
    enviar_telegram("✅ Servidor SPY Alert System activo y funcionando.")
    return jsonify({"status": "ok"}), 200

@app.route("/reporte", methods=["GET"])
def reporte_manual():
    reporte_horario()
    return jsonify({"status": "reporte enviado"}), 200

@app.route("/verificar", methods=["GET"])
def verificar_manual():
    verificar_puntos()
    return jsonify({"status": "verificacion enviada"}), 200

if __name__ == "__main__":
    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()
    app.run(host="0.0.0.0", port=5000, debug=False)
