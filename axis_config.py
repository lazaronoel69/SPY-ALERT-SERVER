#!/usr/bin/env python3
"""
AXIS Config — AX-003 Configuration Baseline
Constantes de configuracion simple, extraidas de server.py sin cambiar
ningun valor ni comportamiento. server.py las importa desde aqui.

NO incluye:
- Tokens/claves (TELEGRAM_TOKEN, TRADIER_TOKEN, ANTHROPIC_API_KEY, etc.)
  Esos permanecen en server.py leidos via os.environ.get(), sin cambios,
  por seguridad y para no tocar el flujo de variables de entorno de Railway.
- Logica de trading, evaluacion, Telegram webhook, ejecucion de ordenes,
  Portfolio ni Derby -- nada de eso vive aqui, solo configuracion simple.
"""

import pytz

# ── Zona horaria ──
EST = pytz.timezone("America/New_York")

# ── Activos monitoreados ──
ACTIVOS     = ["SPY", "AAPL", "BA", "GLD", "NVDA", "AMZN", "GOOG", "META"]
ACTIVOS_SPY = ["SPY"]

# ── Horario de reportes (monitor_loop) ──
# v8.84: hora 16 (4:00 PM / V7) eliminada -- V7 se evalua EXCLUSIVAMENTE
# a las 3:58 PM via loop_v7_anticipada() con la vela provisional.
HORAS_REPORTE = [10, 11, 12, 13, 14, 15]

# ── Switches del sistema y estrategias ──
SISTEMA_ACTIVO = True
VR1_ON = True
RPG_ON = True
GNA_ON = True
GBA_ON = True

# ── Ordenes pendientes ──
ORDEN_TIMEOUT_MIN = 15  # minutos antes de expirar

# ── Persistencia — directorio y archivos ──
DATA_DIR       = "/data"
CANALES_FILE   = "/data/axis_canales.json"
PORTFOLIO_FILE = "/data/axis_portfolio.json"
ORDENES_FILE   = "/data/axis_ordenes.json"
ESTADO_FILE    = "/data/axis_estado_dia.json"
SEÑALES_FILE   = "/data/axis_señales_historicas.json"
BITACORA_FILE  = "/data/axis_bitacora.json"

# ── Tradier — bases de URL (sin tokens) ──
TRADIER_BASE      = "https://sandbox.tradier.com/v1"
TRADIER_BASE_REAL = "https://api.tradier.com/v1"
