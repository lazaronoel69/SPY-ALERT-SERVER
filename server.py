#!/usr/bin/env python3
"""
SPY Canal Bajista — Servidor Email a Telegram
Lee alertas de TradingView en Gmail y las reenvía al grupo de Telegram.
"""

import imaplib
import email
import requests
import time
import threading
from flask import Flask, jsonify
from email.header import decode_header

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════
# CONFIGURACION
# ═══════════════════════════════════════════════════════════
GMAIL_USER       = "spyalerts1969@gmail.com"
GMAIL_PASSWORD   = "vcqwshgssvbxbxte"
TELEGRAM_TOKEN   = "8668514895:AAG5HKGmDLr6_SM1rz3gwC6uk1Ue9iepN70"
TELEGRAM_CHAT_ID = "-5010153427"
CHECK_INTERVAL   = 60  # segundos entre cada revision

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
        print(f"Telegram: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")
        return None

# ═══════════════════════════════════════════════════════════
# FUNCION — leer emails no leidos de TradingView
# ═══════════════════════════════════════════════════════════
def leer_emails():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASSWORD)
        mail.select("inbox")

        status, messages = mail.search(None, '(UNSEEN FROM "noreply@tradingview.com")')

        if status != "OK" or not messages[0]:
            print("No hay emails nuevos de TradingView")
            mail.logout()
            return

        email_ids = messages[0].split()
        print(f"Emails nuevos: {len(email_ids)}")

        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            if status != "OK":
                continue

            msg = email.message_from_bytes(msg_data[0][1])

            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = msg.get_payload(decode=True).decode()

            mensaje_telegram = f"📊 <b>SPY Alert</b>\n\n{body.strip()}"
            print(f"Enviando: {mensaje_telegram}")
            enviar_telegram(mensaje_telegram)

            mail.store(email_id, "+FLAGS", "\\Seen")

        mail.logout()

    except Exception as e:
        print(f"Error leyendo Gmail: {e}")

# ═══════════════════════════════════════════════════════════
# LOOP — revisar email cada 60 segundos
# ═══════════════════════════════════════════════════════════
def monitor_loop():
    print("Monitor iniciado...")
    enviar_telegram("✅ <b>SPY Canal Bajista activo</b>\nMonitoreando alertas de TradingView.")
    while True:
        leer_emails()
        time.sleep(CHECK_INTERVAL)

# ═══════════════════════════════════════════════════════════
# RUTAS FLASK
# ═══════════════════════════════════════════════════════════
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "SPY Canal Bajista — servidor activo"}), 200

@app.route("/test", methods=["GET"])
def test():
    enviar_telegram("✅ Servidor SPY Canal Bajista activo y funcionando.")
    return jsonify({"status": "mensaje enviado a Telegram"}), 200

# ═══════════════════════════════════════════════════════════
# INICIO
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()
    app.run(host="0.0.0.0", port=5000, debug=False)
