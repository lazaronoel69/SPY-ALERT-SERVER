#!/usr/bin/env python3
"""
AXIS Channels — AX-009 Channels Baseline
Estructura y persistencia basica de canales bajistas (CNF/RCB/PM40),
extraida de server.py sin cambiar estructura JSON ni comportamiento.

guardar_canales/cargar_canales reciben `canal` y `ACTIVOS` como parametros
(modifican `canal` in-place, igual que la version original con los
globales de server.py). server.py mantiene wrappers guardar_canales()
y cargar_canales() sin argumentos, que llaman a estas funciones pasando
sus propios globales, para no romper ninguna llamada existente.

NO incluye (segun regla explicita del sprint AX-009):
- calcular_techo_canal, calcular_piso_mitad_canal: calculo matematico.
- Logica de P2 dinamico (vive dentro de evaluar_activo()).
"""

import os
import json


def canal_vacio():
    return {
        "on":             False,
        "p1":             None,
        "p2":             None,
        "p3":             None,
        "p2_actual_high": None,
        "p2_actual_ts":   None,
        "v1_candidato":   None,
        "apagado":        False,
        "roto":           False,
        "fecha_ruptura":  None,
    }


CANALES_DEFAULT = {
    "SPY":  {"on": False, "apagado": False, "p1": None, "p2": None, "p3": None,
             "p2_actual_high": None, "p2_actual_ts": None, "v1_candidato": None},
    "GLD":  {
        "on": True, "apagado": False, "v1_candidato": None,
        "p1": {"fecha": "2026-04-17", "hora_est": 10, "high": 448.70},
        "p2": {"fecha": "2026-05-07", "hora_est": 11, "high": 437.42},
        "p2_actual_high": 437.42,
        "p2_actual_ts": "2026-05-07T11:00:00",
        "p3": {"fecha": "2026-04-29", "hora_est": 9, "low": 415.27},
    },
    "AAPL": {"on": False, "apagado": False, "p1": None, "p2": None, "p3": None,
             "p2_actual_high": None, "p2_actual_ts": None, "v1_candidato": None},
    "BA":   {"on": False, "apagado": False, "p1": None, "p2": None, "p3": None,
             "p2_actual_high": None, "p2_actual_ts": None, "v1_candidato": None},
    "NVDA": {"on": False, "apagado": False, "p1": None, "p2": None, "p3": None,
             "p2_actual_high": None, "p2_actual_ts": None, "v1_candidato": None},
    "AMZN": {"on": False, "apagado": False, "p1": None, "p2": None, "p3": None,
             "p2_actual_high": None, "p2_actual_ts": None, "v1_candidato": None},
    "GOOG": {"on": False, "apagado": False, "p1": None, "p2": None, "p3": None,
             "p2_actual_high": None, "p2_actual_ts": None, "v1_candidato": None},
    "META": {"on": False, "apagado": False, "p1": None, "p2": None, "p3": None,
             "p2_actual_high": None, "p2_actual_ts": None, "v1_candidato": None},
}


def guardar_canales(canal, ACTIVOS, CANALES_FILE):
    try:
        data = {}
        for a in ACTIVOS:
            c = canal[a]
            ts = c["p2_actual_ts"]
            data[a] = {
                "on":             c["on"],
                "apagado":        c["apagado"],
                "roto":           c.get("roto", False),
                "fecha_ruptura":  c.get("fecha_ruptura", None),
                "p1":             c["p1"],
                "p2":             c["p2"],
                "p3":             c["p3"],
                "p2_actual_high": c["p2_actual_high"],
                "p2_actual_ts":   ts.isoformat() if hasattr(ts, 'isoformat') else ts,
                "v1_candidato":   None,
            }
        with open(CANALES_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Canales guardados → {CANALES_FILE}")
    except Exception as e:
        print(f"Error guardando canales: {e}")


def cargar_canales(canal, ACTIVOS, CANALES_FILE, EST):
    """Modifica el dict `canal` in-place (mismo comportamiento que la
    version original con los globales de server.py)."""
    try:
        if os.path.exists(CANALES_FILE):
            with open(CANALES_FILE, 'r') as f:
                data = json.load(f)
            print(f"Canales cargados desde {CANALES_FILE}")
        else:
            data = CANALES_DEFAULT
            print("Primer arranque — cargando canales por defecto (SPY CNF + GLD RCB)")
        for a in ACTIVOS:
            if a not in data:
                continue
            d = data[a]
            canal[a]["on"]             = d.get("on", False)
            canal[a]["apagado"]        = d.get("apagado", False)
            canal[a]["roto"]           = d.get("roto", False)
            canal[a]["fecha_ruptura"]  = d.get("fecha_ruptura", None)
            canal[a]["p1"]             = d.get("p1")
            canal[a]["p2"]             = d.get("p2")
            canal[a]["p3"]             = d.get("p3")
            canal[a]["p2_actual_high"] = d.get("p2_actual_high")
            ts_str = d.get("p2_actual_ts")
            if ts_str and isinstance(ts_str, str):
                try:
                    from datetime import datetime as _dt
                    canal[a]["p2_actual_ts"] = EST.localize(_dt.fromisoformat(ts_str))
                except:
                    canal[a]["p2_actual_ts"] = None
            canal[a]["v1_candidato"] = None
        for a in ACTIVOS:
            if canal[a]["on"]:
                tipo = "RCB" if canal[a]["p3"] else "CNF"
                p1h  = canal[a]["p1"]["high"] if canal[a]["p1"] else "?"
                print(f"  {a}: {tipo} activo — P1={p1h}")
    except Exception as e:
        print(f"Error cargando canales: {e}")
