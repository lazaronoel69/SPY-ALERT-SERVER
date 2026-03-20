#!/usr/bin/env python3
"""
SPY Alert System v3.0
- Reporte a las :01 de cada hora (hora final del operador)
- Yahoo Finance con headers para evitar bloqueo en cloud
- Verificacion de P1/P2 sin auto-correccion
"""

import requests
import threading
import time
from datetime import datetime, timedelta
import pytz
from flask import Flask, jsonify
import pandas as pd

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════
# CONFIGURACION
# ═══════════════════════════════════════════════════════════
TELEGRAM_TOKEN   = "8668514895:AAG5HKGmDLr6_SM1rz3gwC6uk1Ue9iepN70"
TELEGRAM_CHAT_ID = "-5010153427"
EST              = pytz.timezone("America/New_York")

# P1 y P2 — con ADJ desactivado en TradingView
P1 = { "fecha": "2026-02-26", "hora": 10, "high": 693.36 }
P2 = { "fecha": "2026-03-10", "hora": 14, "high": 683.35 }

# Headers para evitar bloqueo de Yahoo Finance en servidores cloud
YF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
}

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
# YAHOO FINANCE — con headers para evitar bloqueo en cloud
# ═══════════════════════════════════════════════════════════
def get_spy_data(period="2d", interval="1h"):
    try:
        session = requests.Session()
        session.headers.update(YF_HEADERS)

        # Obtener cookie primero
        session.get("https://finance.yahoo.com", timeout=10)

        import yfinance as yf
        spy = yf.download(
            "SPY",
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            session=session
        )
        return spy if not spy.empty else None
    except Exception as e:
        print(f"Error Yahoo Finance: {e}")
        return None

def get_spy_data_fecha(fecha_str, interval="1h"):
    try:
        session = requests.Session()
        session.headers.update(YF_HEADERS)
        session.get("https://finance.yahoo.com", timeout=10)

        import yfinance as yf
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        fin = (fecha + timedelta(days=1)).strftime("%Y-%m-%d")
        spy = yf.download(
            "SPY",
            start=fecha_str,
            end=fin,
            interval=interval,
            auto_adjust=False,
            progress=False,
            session=session
        )
        return spy if not spy.empty else None
    except Exception as e:
        print(f"Error Yahoo Finance fecha: {e}")
        return None

# ═══════════════════════════════════════════════════════════
# VERIFICACION P1 Y P2 — solo avisa, NO corrige
# ═══════════════════════════════════════════════════════════
def get_high_vela(fecha_str, hora_est):
    spy = get_spy_data_fecha(fecha_str)
    if spy is None:
        return None
    for idx in spy.index:
        idx_est = idx.astimezone(EST)
        if idx_est.hour == hora_est:
            val = spy.loc[idx, "High"]
            return float(val.iloc[0] if hasattr(val, 'iloc') else val)
    return None

def verificar_puntos():
    mensaje = "🔍 <b>Verificacion P1 y P2</b>\n"
    mensaje += "<i>(Yahoo Finance sin ADJ vs operador)</i>\n\n"

    high_p1 = get_high_vela(P1["fecha"], P1["hora"])
    if high_p1:
        diff = abs(high_p1 - P1["high"])
        if diff > 0.50:
            mensaje += f"⚠️ <b>P1 REVISAR</b>\n   Operador: ${P1['high']:.2f} | Yahoo: ${high_p1:.2f} | Diff: ${diff:.2f}\n   Verificar en TradingView con ADJ desactivado\n\n"
        else:
            mensaje += f"✅ <b>P1 OK</b> — ${P1['high']:.2f} (Yahoo: ${high_p1:.2f} | Diff: ${diff:.2f})\n\n"
    else:
        mensaje += f"⚠️ P1 no verificado — usando ${P1['high']:.2f}\n\n"

    high_p2 = get_high_vela(P2["fecha"], P2["hora"])
    if high_p2:
        diff = abs(high_p2 - P2["high"])
        if diff > 0.50:
            mensaje += f"⚠️ <b>P2 REVISAR</b>\n   Operador: ${P2['high']:.2f} | Yahoo: ${high_p2:.2f} | Diff: ${diff:.2f}\n   Verificar en TradingView con ADJ desactivado\n\n"
        else:
            mensaje += f"✅ <b>P2 OK</b> — ${P2['high']:.2f} (Yahoo: ${high_p2:.2f} | Diff: ${diff:.2f})\n\n"
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
# OBTENER ULTIMA VELA CERRADA DE SPY
# ═══════════════════════════════════════════════════════════
def get_ultima_vela():
    spy = get_spy_data(period="2d", interval="1h")
    if spy is None or len(spy) < 2:
        return None
    try:
        ultima = spy.iloc[-2]
        return {
            "open":  float(ultima["Open"]),
            "close": float(ultima["Close"]),
            "high":  float(ultima["High"]),
            "low":   float(ultima["Low"]),
            "time":  spy.index[-2].astimezone(EST).strftime("%H:%M EST")
        }
    except Exception as e:
        print(f"Error procesando vela: {e}")
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

    # Hora final para el operador = hora actual (vela de TradingView cierra :30)
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
            f"<b>Hora analisis:</b> {hora_operador}\n\n"
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
# LOOP — reporta a los :01 de cada hora
# ═══════════════════════════════════════════════════════════
def monitor_loop():
    print("SPY Alert System v3.0 iniciado...")
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
    return jsonify({"status": "SPY Alert System v3.0 activo"}), 200

@app.route("/test", methods=["GET"])
def test():
    enviar_telegram("✅ <b>SPY Alert System v3.0</b> — activo y funcionando.")
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
