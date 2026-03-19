#!/usr/bin/env python3
"""
SPY Canal Bajista — Servidor Webhook
Recibe alertas de TradingView y las reenvía al grupo de Telegram.

Instalacion:
    pip install flask requests

Uso:
    python server.py

Despues usar ngrok para exponer el servidor:
    ngrok http 5000
"""

from flask import Flask, request, jsonify
import requests
import json
from datetime import datetime

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════
# CONFIGURACION — actualiza estos valores
# ═══════════════════════════════════════════════════════════
TELEGRAM_TOKEN   = "8668514895:AAG5HKGmDLr6_SM1rz3gwC6uk1Ue9iepN70"
TELEGRAM_CHAT_ID = "-5010153427"  # Grupo Option Alert Ro_bot

# ═══════════════════════════════════════════════════════════
# FUNCION — enviar mensaje a Telegram
# ═══════════════════════════════════════════════════════════
def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")
        return None

# ═══════════════════════════════════════════════════════════
# RUTA — recibe webhook de TradingView
# ═══════════════════════════════════════════════════════════
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # TradingView puede enviar texto plano o JSON
        if request.is_json:
            data = request.get_json()
            mensaje = data.get("message", str(data))
        else:
            mensaje = request.data.decode("utf-8")

        print(f"[{datetime.now()}] Mensaje recibido: {mensaje}")

        # Reenviar a Telegram
        resultado = enviar_telegram(mensaje)
        print(f"Telegram response: {resultado}")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"Error en webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ═══════════════════════════════════════════════════════════
# RUTA — prueba manual
# ═══════════════════════════════════════════════════════════
@app.route("/test", methods=["GET"])
def test():
    mensaje = "✅ Servidor SPY Canal Bajista activo y funcionando."
    enviar_telegram(mensaje)
    return jsonify({"status": "mensaje enviado a Telegram"}), 200

# ═══════════════════════════════════════════════════════════
# INICIO
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 50)
    print("SPY Canal Bajista — Servidor Webhook")
    print("Escuchando en http://localhost:5000")
    print("Webhook URL: http://localhost:5000/webhook")
    print("Test URL:    http://localhost:5000/test")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=False)
