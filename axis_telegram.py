#!/usr/bin/env python3
"""
AXIS Telegram — AX-006 Telegram Baseline
Funciones simples de Telegram, extraidas de server.py sin cambiar texto
de alertas, botones, parse_mode, timeout, ni comportamiento.

NO incluye (quedan en server.py por dependencia de estado complejo,
segun regla explicita del sprint AX-006):
- enviar_telegram_botones: depende de _portfolio y de la logica del
  Derby (lee derby["activo"], derby["turno_actual"], derby["caballos"]
  para decidir si mostrar el boton DERBY). Moverla requeriria que este
  modulo dependiera de Portfolio/Derby, lo cual el sprint prohibe.
- telegram_webhook: ruta Flask con logica de ordenes, ejecucion Tradier,
  Portfolio y Derby. Explicitamente excluida por el sprint.
- enviar_senal_con_botones: orquesta registrar_senal_disparada, precio
  Tradier, opcion Tradier, y enviar_telegram_botones. Explicitamente
  excluida por el sprint.
"""

import os
import requests

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-5010153427")


def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        print(f"Telegram: {r.status_code} — {mensaje[:60]}")
    except Exception as e:
        print(f"Error Telegram: {e}")
