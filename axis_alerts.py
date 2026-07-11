#!/usr/bin/env python3
"""AXIS Alert Lifecycle — AX-TRACK-001.

Registro persistente append/update de cada alerta generada por AXIS. Usa el
mismo mecanismo JSON bajo /data que el resto del sistema y no contiene lógica
de estrategias, Telegram ni ejecución de órdenes.
"""

import json
import os
import threading
import uuid
from datetime import datetime

from axis_config import ALERTAS_FILE, EST


ESTADOS = {"GENERATED", "NOTIFIED", "ACTIVE", "CLOSED", "CANCELLED"}
_lock = threading.RLock()


def _cargar():
    try:
        with open(ALERTAS_FILE, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"alertas": []}
    except FileNotFoundError:
        return {"alertas": []}
    except Exception as e:
        print(f"Error cargando alertas: {e}")
        return None


def _guardar(data):
    try:
        os.makedirs(os.path.dirname(ALERTAS_FILE), exist_ok=True)
        temporal = f"{ALERTAS_FILE}.tmp"
        with open(temporal, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        os.replace(temporal, ALERTAS_FILE)
        return True
    except Exception as e:
        print(f"Error guardando alertas: {e}")
        return False


def crear_alerta(simbolo, estrategia, direccion, precio_referencia,
                 hora_label=None, origen="ESTRATEGIA"):
    ahora = datetime.now(EST)
    alert_id = f"A-{ahora.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    alerta = {
        "alert_id": alert_id,
        "ts_generada": ahora.isoformat(),
        "fecha": ahora.strftime("%Y-%m-%d"),
        "simbolo": simbolo,
        "estrategia": estrategia,
        "direccion": direccion,
        "precio_referencia": precio_referencia,
        "hora_label": hora_label,
        "origen": origen,
        "estado": "GENERATED",
        "ts_ultima_actualizacion": ahora.isoformat(),
        "orden_id": None,
        "posicion_id": None,
        "eventos": [{"ts": ahora.isoformat(), "estado": "GENERATED"}],
    }
    with _lock:
        data = _cargar()
        if data is None:
            return None
        data.setdefault("alertas", []).append(alerta)
        if not _guardar(data):
            return None
    return alert_id


def actualizar_alerta(alert_id, estado=None, evento=None, **campos):
    if not alert_id:
        return False
    if estado is not None and estado not in ESTADOS:
        raise ValueError(f"Estado de alerta inválido: {estado}")
    ahora = datetime.now(EST).isoformat()
    with _lock:
        data = _cargar()
        if data is None:
            return False
        alerta = next((a for a in data.get("alertas", [])
                       if a.get("alert_id") == alert_id), None)
        if alerta is None:
            print(f"Alerta no encontrada: {alert_id}")
            return False
        if estado is not None:
            alerta["estado"] = estado
        for clave, valor in campos.items():
            if valor is not None:
                alerta[clave] = valor
        alerta["ts_ultima_actualizacion"] = ahora
        detalle = {"ts": ahora}
        if estado is not None:
            detalle["estado"] = estado
        if evento:
            detalle["evento"] = evento
        if estado is not None or evento:
            alerta.setdefault("eventos", []).append(detalle)
        return _guardar(data)


def listar_alertas(alert_id=None, fecha=None, simbolo=None,
                   estrategia=None, estado=None):
    with _lock:
        data = _cargar()
        alertas = list(data.get("alertas", [])) if data is not None else []
    if alert_id:
        alertas = [a for a in alertas if a.get("alert_id") == alert_id]
    if fecha:
        alertas = [a for a in alertas if a.get("fecha") == fecha]
    if simbolo:
        alertas = [a for a in alertas if a.get("simbolo", "").upper() == simbolo.upper()]
    if estrategia:
        needle = estrategia.upper()
        alertas = [a for a in alertas if needle in a.get("estrategia", "").upper()]
    if estado:
        alertas = [a for a in alertas if a.get("estado") == estado.upper()]
    return alertas
