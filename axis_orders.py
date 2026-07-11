#!/usr/bin/env python3
"""
AXIS Orders — AX-007 Orders Baseline
Persistencia de ordenes_pendientes, extraida de server.py sin cambiar
formato de axis_ordenes.json ni ORDEN_TIMEOUT_MIN.

Como ordenes_pendientes es un dict global en server.py, estas funciones
lo reciben como parametro (en vez de leerlo/escribirlo como global propio
de este modulo). server.py mantiene wrappers guardar_ordenes() y
cargar_ordenes() sin argumentos, que llaman a estas funciones pasando
su propio global, para no romper ninguna llamada existente.

NO incluye (segun regla explicita del sprint AX-007):
- loop_limpiar_ordenes: logica de expiracion + edicion de mensajes Telegram.
- enviar_senal_con_botones: orquesta Tradier + Telegram + esta persistencia.
- telegram_webhook: logica de ordenes + ejecucion + Portfolio + Derby.
"""

import os
import json
import pytz
from datetime import datetime

from axis_config import ORDENES_FILE, ORDEN_TIMEOUT_MIN


def guardar_ordenes(ordenes_pendientes):
    """Persiste ordenes_pendientes en /data para sobrevivir reinicios."""
    try:
        data = {}
        for oid, d in ordenes_pendientes.items():
            data[oid] = {
                "opcion":         d["opcion"],
                "estrategia":     d.get("estrategia", "AXIS"),
                "alert_id":       d.get("alert_id"),
                "ts":             d["ts"].isoformat() if hasattr(d["ts"], "isoformat") else str(d["ts"]),
                "message_id":     d["message_id"],
                "chat_id":        d["chat_id"],
                "texto_original": d.get("texto_original", ""),
            }
        with open(ORDENES_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error guardando ordenes: {e}")


def cargar_ordenes(ordenes_pendientes):
    """Carga ordenes_pendientes desde /data al arrancar.
    Modifica el dict ordenes_pendientes recibido in-place (mismo
    comportamiento que la version original con el global de server.py)."""
    try:
        if not os.path.exists(ORDENES_FILE):
            return
        with open(ORDENES_FILE, "r") as f:
            data = json.load(f)
        ahora = datetime.now(pytz.utc)
        recuperadas = 0
        for oid, d in data.items():
            try:
                ts = datetime.fromisoformat(d["ts"])
                if ts.tzinfo is None:
                    ts = pytz.utc.localize(ts)
                # Descartar órdenes ya expiradas
                if (ahora - ts).total_seconds() > ORDEN_TIMEOUT_MIN * 60:
                    continue
                ordenes_pendientes[oid] = {
                    "opcion":         d["opcion"],
                    "estrategia":     d.get("estrategia", "AXIS"),
                    "alert_id":       d.get("alert_id"),
                    "ts":             ts,
                    "message_id":     d["message_id"],
                    "chat_id":        d["chat_id"],
                    "texto_original": d.get("texto_original", ""),
                }
                recuperadas += 1
            except Exception as e:
                print(f"Error recuperando orden {oid}: {e}")
        if recuperadas:
            print(f"Ordenes pendientes recuperadas: {recuperadas}")
        # Limpiar archivo dejando solo las vigentes
        guardar_ordenes(ordenes_pendientes)
    except Exception as e:
        print(f"Error cargando ordenes: {e}")
