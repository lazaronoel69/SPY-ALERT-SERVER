#!/usr/bin/env python3
"""
AXIS Storage — AX-005 Storage Baseline
Funciones de persistencia JSON de bajo riesgo, extraidas de server.py sin
cambiar formato JSON, rutas, ni comportamiento.

NO incluye (quedan en server.py por depender de estado global complejo,
segun regla explicita del sprint AX-005):
- guardar_ordenes / cargar_ordenes (dependen de ordenes_pendientes)
- guardar_portfolio / cargar_portfolio (dependen de _portfolio)
- guardar_canales / cargar_canales (dependen de canal[] y CANALES_DEFAULT)
- archivar_señales_dia (depende de estado_dia[] y ACTIVOS)

guardar_estado_dia() se incluye aqui aceptando el diccionario estado_dia
como parametro (en vez de leerlo como variable global), ya que axis_storage.py
no debe depender de globals definidos en server.py. server.py mantiene un
wrapper con el mismo nombre original sin argumentos para no romper ninguna
llamada existente.
"""

import os
import json

from axis_config import SEÑALES_FILE, ESTADO_FILE, DATA_DIR


def cargar_señales_historicas():
    if not os.path.exists(SEÑALES_FILE):
        return {}
    try:
        with open(SEÑALES_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error cargando señales históricas: {e}")
        return {}


def guardar_señales_historicas(data):
    try:
        with open(SEÑALES_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error guardando señales históricas: {e}")


def guardar_estado_dia(estado_dia):
    """AX-005: recibe estado_dia como parametro (antes era variable global
    leida directamente). server.py mantiene un wrapper guardar_estado_dia()
    sin argumentos que llama a esta version pasando su propio global,
    para no romper ninguna llamada existente."""
    try:
        with open(ESTADO_FILE, "w") as f:
            json.dump(estado_dia, f, indent=2)
    except Exception as e:
        print(f"Error guardando estado_dia: {e}")


def ruta_velas_local(simbolo):
    return f"{DATA_DIR}/axis_velas_{simbolo}.json"


def cargar_velas_local(simbolo):
    ruta = ruta_velas_local(simbolo)
    if not os.path.exists(ruta):
        return {"simbolo": simbolo, "ultima_barra": None, "barras": []}
    try:
        with open(ruta) as f:
            return json.load(f)
    except Exception as e:
        print(f"Error cargando velas locales {simbolo}: {e}")
        return {"simbolo": simbolo, "ultima_barra": None, "barras": []}


def guardar_velas_local(simbolo, data):
    try:
        with open(ruta_velas_local(simbolo), "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error guardando velas locales {simbolo}: {e}")
