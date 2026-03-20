#!/usr/bin/env python3
"""
SPY Alert System v4.0
- Fuente de datos: Alpha Vantage API (confiable desde servidores cloud)
- Reporte a las :01 de cada hora
- Verificacion P1/P2 sin auto-correccion
"""

import requests
import threading
import time
from datetime import datetime, timedelta
import pytz
from flask import Flask, jsonify

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════
# CONFIGURACION
# ═══════════════════════════════════════════════════════════
TELEGRAM_TOKEN    = "8668514895:AAG5HKGmDLr6_SM1rz3gwC6uk1Ue9iepN70"
TELEGRAM_CHAT_ID  = "-5010153427"
EST               = pytz.timezone("America/New_York")
ALPHA_VANTAGE_KEY = "TYQ1F390ML6O8AWL"  # Reemplazar con key gratuita de alphavantage.co

# P1 y P2 — con ADJ desactivado en TradingView
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
# ALPHA VANTAGE — datos intraday confiables desde cloud
# ═══════════════════════════════════════════════════════════
def get_spy_intraday():
    """Obtiene velas de 60 minutos de SPY via Alpha Vantage"""
    try:
        url = (
            f"https://www.alphavantage.co/query"
            f"?function=TIME_SERIES_INTRADAY"
            f"&symbol=SPY"
            f"&interval=60min"
            f"&outputsize=compact"
            f"&apikey={ALPHA_VANTAGE_KEY}"
        )
        r = requests.get(url, timeout=15)
        data = r.json()

        if "Time Series (60min)" not in data:
            print(f"Alpha Vantage error: {data}")
            return None

        series = data["Time Series (60min)"]
        velas = []
        for timestamp_str, values in series.items():
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            dt_est = EST.localize(dt)
            velas.append({
                "time": dt_est,
                "open":  float(values["1. open"]),
                "high":  float(values["2. high"]),
                "low":   float(values["3. low"]),
                "close": float(values["4. close"]),
            })

        # Ordenar por tiempo descendente
        velas.sort(key=lambda x: x["time"], reverse=True)
        return velas

    except Exception as e:
        print(f"Error Alpha Vantage: {e}")
        return None

def get_ultima_vela():
    """Retorna la ultima vela cerrada"""
    velas = get_spy_intraday()
    if not velas or len(velas) < 2:
        return None
    # velas[0] es la mas reciente (puede estar abierta)
    # velas[1] es la ultima cerrada
    ultima = velas[1]
    return {
        "open":  ultima["open"],
        "close": ultima["close"],
        "high":  ultima["high"],
        "low":   ultima["low"],
        "time":  ultima["time"].strftime("%H:%M EST")
    }

def get_high_vela_fecha(fecha_str, hora_est):
    """Obtiene el high de una vela especifica por fecha y hora"""
    try:
        url = (
            f"https://www.alphavantage.co/query"
            f"?function=TIME_SERIES_INTRADAY"
            f"&symbol=SPY"
            f"&interval=60min"
            f"&outputsize=full"
            f"&apikey={ALPHA_VANTAGE_KEY}"
        )
        r = requests.get(url, timeout=15)
        data = r.json()

        if "Time Series (60min)" not in data:
            return None

        series = data["Time Series (60min)"]
        for timestamp_str, values in series.items():
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            dt_est = EST.localize(dt)
            if dt_est.strftime("%Y-%m-%d") == fecha_str and dt_est.hour == hora_est:
                return float(values["2. high"])
        return None

    except Exception as e:
        print(f"Error Alpha Vantage fecha: {e}")
        return None

# ═══════════════════════════════════════════════════════════
# VERIFICACION P1 Y P2 — solo avisa, NO corrige
# ═══════════════════════════════════════════════════════════
def verificar_puntos():
    mensaje = "🔍 <b>Verificacion P1 y P2</b>\n"
    mensaje += "<i>(Alpha Vantage sin ADJ vs operador)</i>\n\n"

    high_p1 = get_high_vela_fecha(P1["fecha"], P1["hora"])
    if high_p1:
        diff = abs(high_p1 - P1["high"])
        if diff > 0.50:
            mensaje += f"⚠️ <b>P1 REVISAR</b>\n   Operador: ${P1['high']:.2f} | AV: ${high_p1:.2f} | Diff: ${diff:.2f}\n\n"
        else:
            mensaje += f"✅ <b>P1 OK</b> — ${P1['high']:.2f} (AV: ${high_p1:.2f} | Diff: ${diff:.2f})\n\n"
    else:
        mensaje += f"⚠️ P1 no verificado — usando ${P1['high']:.2f}\n\n"

    high_p2 = get_high_vela_fecha(P2["fecha"], P2["hora"])
    if high_p2:
        diff = abs(high_p2 - P2["high"])
        if diff > 0.50:
            mensaje += f"⚠️ <b>P2 REVISAR</b>\n   Operador: ${P2['high']:.2f} | AV: ${high_p2:.2f} | Diff: ${diff:.2f}\n\n"
        else:
            mensaje += f"✅ <b>P2 OK</b> — ${P2['high']:.2f} (AV: ${high_p2:.2f} | Diff: ${diff:.2f})\n\n"
    else:
        mensaje += f"⚠️ P2 no verificado — usando ${P2['high']:.2f}\n\n"

    techo_hoy = calcular_techo_ahora()
    mensaje += f"📐 Techo ahora: <b>${techo_hoy:.2f}</b>\n"
    mensaje += f"⚠️ REGLA: ADJ siempre desactivado en TradingView"
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
# REPORTE HORARIO
# ═══════════════════════════════════════════════════════════
def reporte_horario():
    ahora_est = datetime.now(EST)
    hora = ahora_est.hour
    if hora < 10 or hora > 16:
        print(f"Fuera de horario: {ahora_est.strftime('%H:%M EST')}")
        return

    hora_operador = f"{hora}:00 EST"
    techo = calcular_techo_ahora()
    vela  = get_ultima_vela()

    if not vela:
        enviar_telegram(f"⚠️ <b>Hora {hora_operador}</b> — No se pudo obtener datos de SPY. Sistema activo.")
        return

    vela_verde  = vela["close"] > vela["open"]
    rango       = vela["high"] - vela["low"]
    mecha_sup   = vela["high"] - max(vela["close"], vela["open"])
    mecha_pct   = (mecha_sup / rango * 100) if rango > 0 else 0
    mecha_ok    = mecha_pct <= 25
    sobre_techo = vela["close"] > techo
    ruptura     = vela_verde and mecha_ok and sobre_techo
    proxima     = f"{hora + 1}:00 EST" if hora < 16 else "apertura manana"

    if ruptura:
        mensaje = (
            f"🟢 <b>RUPTURA DEL CANAL</b>\n"
            f"<b>Hora:</b> {hora_operador}\n\n"
            f"<b>Techo:</b> ${techo:.2f}\n"
            f"<b>Cierre vela:</b> ${vela['close']:.2f}\n"
            f"<b>Mecha sup:</b> {mecha_pct:.0f}%\n\n"
            f"⚡ <b>EVALUAR ENTRADA</b>"
        )
    else:
        razon = []
        if not vela_verde:  razon.append("vela roja")
        if not mecha_ok:    razon.append(f"mecha {mecha_pct:.0f}%")
        if not sobre_techo: razon.append(f"cierre ${vela['close']:.2f} bajo techo ${techo:.2f}")
        mensaje = (
            f"🔴 <b>Sin ruptura — Hora {hora_operador}</b>\n\n"
            f"<b>Techo:</b> ${techo:.2f}\n"
            f"<b>Cierre vela:</b> ${vela['close']:.2f}\n"
            f"<b>Vela:</b> {'Verde' if vela_verde else 'Roja'} | Mecha: {mecha_pct:.0f}%\n"
            f"<b>Razon:</b> {', '.join(razon)}\n\n"
            f"Sistema activo — proxima: {proxima}"
        )

    enviar_telegram(mensaje)

# ═══════════════════════════════════════════════════════════
# LOOP — reporta a las :01 de cada hora
# ═══════════════════════════════════════════════════════════
def monitor_loop():
    print("SPY Alert System v4.0 iniciado...")
    time.sleep(5)
    verificar_puntos()
    while True:
        ahora = datetime.now(EST)
        minutos = (1 - ahora.minute) % 60
        if minutos == 0:
            minutos = 60
        print(f"Proximo reporte en {minutos} min")
        time.sleep(minutos * 60)
        reporte_horario()

# ═══════════════════════════════════════════════════════════
# RUTAS FLASK
# ═══════════════════════════════════════════════════════════
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "SPY Alert System v4.0 activo"}), 200

@app.route("/test", methods=["GET"])
def test():
    enviar_telegram("✅ <b>SPY Alert System v4.0</b> — activo y funcionando.")
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
