#!/usr/bin/env python3
"""
AXIS Portfolio — AX-008 Portfolio Baseline
Estructura y persistencia basica del portfolio, extraida de server.py sin
cambiar estructura JSON ni comportamiento observable.

Como _portfolio es un dict global en server.py, cargar_portfolio() aqui
DEVUELVE el dict cargado (en vez de asignarlo a un global propio), y
guardar_portfolio(data) recibe el dict como parametro. server.py mantiene
wrappers cargar_portfolio() y guardar_portfolio() sin argumentos que
asignan/leen su propio global _portfolio, para no romper ninguna llamada
existente.

IMPORTANTE sobre el guardado interno de cargar_portfolio():
La version original llamaba a guardar_portfolio() (sin argumentos, el
global) en 3 puntos durante la migracion reto->derby y la creacion de
portfolio nuevo. Esta version devuelve una tupla (data, debe_guardar)
para que el WRAPPER en server.py decida cuando llamar a su propio
guardar_portfolio() -- preservando el mismo efecto observable (el archivo
se guarda en los mismos 3 casos) sin que este modulo dependa del global.

NO incluye (segun regla explicita del sprint AX-008):
- registrar_posicion, cerrar_posicion: logica de negocio del portfolio.
- Funciones de Derby (derby_activar, derby_desactivar, derby_status, etc).
"""

import os
import json

from axis_config import PORTFOLIO_FILE

DERBY_CABALLOS = [
    {"id": 1, "nombre": "Noel"},
    {"id": 2, "nombre": "Paula"},
    {"id": 3, "nombre": "Noel Andres"},
    {"id": 4, "nombre": "Emilia"},
]


def portfolio_vacio():
    return {
        "posiciones":  [],
        "historial":   [],
        "derby": {
            "nombre":          "REAL LAZARO-PALMA",
            "activo":          False,
            "turno_actual":    1,
            "ganador":         None,
            "esperando_cierre": False,
            "caballos": [
                {
                    "id":              c["id"],
                    "nombre":          c["nombre"],
                    "capital":         0,
                    "capital_inicial": 0,
                    "ronda":           0,
                    "posicion":        None,
                    "eliminado":       False,
                    "historial":       []
                }
                for c in DERBY_CABALLOS
            ]
        }
    }


def guardar_portfolio(data):
    try:
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"Error guardando portfolio: {e}")


def cargar_portfolio():
    """Devuelve el dict de portfolio cargado/migrado/creado.
    Devuelve (data, debe_guardar): debe_guardar es True en los mismos
    3 casos donde la version original llamaba a guardar_portfolio()
    internamente (migracion reto->derby, derby faltante, portfolio nuevo).
    El wrapper en server.py es responsable de llamar a su propio
    guardar_portfolio() si debe_guardar es True, preservando el mismo
    efecto observable."""
    debe_guardar = False
    try:
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE, 'r') as f:
                data = json.load(f)
            # Migrar reto→derby si viene de versión anterior
            if "reto" in data and "derby" not in data:
                vacio = portfolio_vacio()
                data["derby"] = vacio["derby"]
                print("Migración: reto→derby completada")
                debe_guardar = True
            elif "derby" not in data:
                vacio = portfolio_vacio()
                data["derby"] = vacio["derby"]
                debe_guardar = True
            print(f"Portfolio cargado — {len(data['posiciones'])} posiciones abiertas")
        else:
            data = portfolio_vacio()
            debe_guardar = True
            print("Portfolio nuevo creado")
    except Exception as e:
        print(f"Error cargando portfolio: {e}")
        data = portfolio_vacio()
    return data, debe_guardar
