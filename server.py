#!/usr/bin/env python3
"""
AXIS Breakout Sentinel v9.03
Estrategias: 1VR | 1VR+ | RPG | GNA | GBA | RCB/CNF
Multi-activo: SPY, AAPL, BA, GLD, NVDA, AMZN, GOOG, META, MU, SPCX
v8.43: Portfolio fix — ejecutar_orden_tradier en webhook exec/reto | Panic Button al bid |
       Reto con capital 80% + ±5 strikes + Claude fallback | Reset route | Sin precios live
v8.44: Persistencia ordenes_pendientes en /data/axis_ordenes.json — sobrevive reinicios Railway
v8.45: get_velas — rango único 40 días hábiles, elimina HTTP 400 en rangos viejos
v8.46: Expand ACTIVOS (NVDA,AMZN,GOOG,META) | V7 SPY 4:14/4:16 | Polling GTC+vencimiento | Landing page
Auto-P2 | Apagado automatico si nuevo P2 >= P1
Fix v8.2: 1VR envia alerta durante reconstruccion antes de marcar vr1_fired
v8.3: 1VR+
v8.4: CORS headers para app web
v8.5: Tradier sandbox + botones Telegram EJECUTAR/IGNORAR
v8.5: RPG umbral bajado de 0.5% a 0.2%
v8.6: Manejo robusto error Tradier — alerta llega siempre aunque Tradier falle
v8.7: 1VR reconstruccion ahora usa enviar_senal_con_botones — botones EJECUTAR/IGNORAR
v8.8: Ruta /tradier_test para diagnosticar token y conexion — si V1 roja cae dentro de canal RCB entre techo y media, alerta dice 1VR+
v8.9: TRADIER_TOKEN_REAL para datos historicos — ruta /tradier_history_test verifica velas 1h de produccion
v8.10: Ruta /verificar_velas — compara velas 1h TwelveData vs precio real Tradier para validar consistencia de datos
v8.11: Thread independiente V7 anticipada — AAPL/BA/GLD evaluan V7 a las 3:58 EST y corrigen cierre real a las 4:00 EST sin alerta. SPY sin cambios.
v8.12: Ruta /charts para servir axis_charts.html — dashboard de graficas AXIS
v8.13: Ruta /test_tradier_30min — verifica si Tradier produccion tiene velas de 30min y construye velas AXIS de 1h para comparar vs TradingView
v8.14: Fix parser timestamp ISO en test_tradier_30min — agrupacion correcta de barras 15min en velas AXIS de 1h
v8.15: Fix agrupacion AXIS — ignorar barras pre-AXIS (9:30 y 9:45), V1 empieza en barra 10:00
v8.16: Ruta /comparar_fuentes — compara TwelveData vs Tradier 15min para HOY, muestra OHLC lado a lado por vela AXIS
v8.17: MIGRACION COMPLETA — TwelveData eliminado. get_velas() ahora usa Tradier produccion 15min agrupadas en velas AXIS. 99.8% mas preciso que TwelveData.
v8.23: Ruta /diagnostico — auditoria completa de estrategias por activo y fecha. Muestra valores exactos, umbrales y razon de cada señal disparada o no.
v8.24: Timer 15min ordenes pendientes + thread limpieza.
v8.25: Ruta /canal_estado — devuelve P1/P2/P3 actuales por activo para sincronizar con dashboard. en ordenes pendientes — expiran automaticamente con aviso a Telegram. Webhook mejorado.
v8.26: Persistencia canales en archivo JSON — sobrevive reinicios. Precarga SPY CNF y GLD RCB.
v8.27: Ruta /canal_lineas — Railway calcula techo/mitad/piso por cada vela. Dashboard dibuja exactamente lo mismo que Railway evalua.
v8.63: FIX 1VR reconstruccion — ahora verifica condiciones adicionales (RCB 30% o SMA40>SMA20) igual que evaluacion normal.
       FIX landing page — mercado abierto solo en horario 9:30-16:00 EST.
       FIX /bitacora/data — agrega ahora_est timestamp.
       NEW /source endpoint — expone codigo fuente para lectura de AI.
v8.86: AX-OPS-001A: /version ahora resuelve git_commit desde RAILWAY_GIT_COMMIT_SHA/GIT_COMMIT/SOURCE_VERSION/COMMIT_SHA antes de intentar subprocess. Agrega deploy_id y service_name.
       AX-V7-003: /status velas_db usa ahora.date() (EST) en lugar de date.today() (UTC) — corrige tiene_hoy=false falso despues de medianoche UTC. Expande velas_db con ultima_barra_15m, fecha_ultima_barra, v7_hoy_presente, v7_hoy_completa, v7_bars, v7_bars_expected.
v8.87: AX-V7-005: construir_v7_provisional ahora valida exactamente 3 barras 15min (15:00/15:15/15:30) y 13 barras 1min (15:45-15:57). Sort explicito, validacion OHLC, rechazo si falta cualquier pieza. bars=16, bars_expected=16.
v8.88: AX-V7-005A: evaluar_v7_anticipada retorna True/False. loop_v7_anticipada reintenta V7 provisional cada 30s en ventana 3:58-3:59:30. HED separado (una vez por simbolo). ejecutado_358 solo se actualiza en exito. Telegram unico de omisiones a las 4:01.
v8.89: AX-TRACK-001: expediente JSON persistente para cada alerta, enlazado con orden, decisión, posición y cierre; incluye HED.
v8.90: AX-TRACK-002: seguimiento cada 5 min de posiciones activas con bid, P&L, MFE, MAE, duración y snapshots vinculados al alert_id.
v8.91: AX-FIX-EXP-001: cierre de posiciones vencidas el mismo día a las 16:15 EST y reconciliación al arrancar, incluso fuera de mercado.
v8.92: AX-TRACK-003: updates operativos por Telegram: hitos P&L, fallos/reanudación, cierre con MFE/MAE y resumen diario de posiciones.
v8.93: AX-ASSET-001: MU y SPCX agregados al monitoreo, V1-V7, Telegram, canales, dashboards, backtest y revisión diaria.
v8.94: AX-TRACK-004: seguimiento 5 min silencioso; hitos/fallos se registran sin Telegram y se consolidan al cierre diario.
v8.95: AX-TRACK-NOTIFY-001: cada reconciliación semanal se envía una sola vez por Telegram, con reintentos y estado verificable.
v8.96: AX-SEC-001: control administrativo autenticado, webhook Telegram validado, CORS restringido y rutas mutables solo POST.
v8.97: AX-FIX-EXEC-001: una posición solo se registra tras confirmación de compra de Tradier; huérfanas sin confirmación se anulan y excluyen de métricas.
v8.98: AX-MOBILE-001: Derby móvil se empareja por Telegram privado con sesión HttpOnly; el token administrativo nunca se comparte.
v8.99: AX-RISK-001: telemetría de salidas sombra registra stops y drawdowns hipotéticos; no cierra ni altera posiciones.
v9.00: AX-FIX-FLOW-001: ejecución Tradier ambigua queda en revisión segura; no hay reintento automático ni doble envío Derby.
v9.01: AX-UX-ACCESS-001: dashboards internos reconocen sesión móvil/desktop emparejada antes de solicitar token.
v9.02: AX-DERBY-001: Derby muestra premio actual, P&L y una sola barra de vida hasta vencimiento.
v9.03: AX-DERBY-002: Derby muestra strike junto al contrato activo.
"""

import os
import requests
import threading
import time
import hmac
import hashlib
import secrets
from functools import wraps
from datetime import datetime, timedelta, date
import pytz
from flask import Flask, jsonify, request, Response, redirect

app = Flask(__name__)

# ── CORS — solo el dashboard servido por AXIS puede llamar al API ──
AXIS_ALLOWED_ORIGIN = os.environ.get(
    "AXIS_ALLOWED_ORIGIN", "https://web-production-bf9d0.up.railway.app"
).rstrip("/")

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin", "").rstrip("/")
    if origin == AXIS_ALLOWED_ORIGIN:
        response.headers['Access-Control-Allow-Origin']  = AXIS_ALLOWED_ORIGIN
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-AXIS-Admin-Token'
        response.headers['Vary'] = 'Origin'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Referrer-Policy'] = 'same-origin'
    return response

@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    from flask import Response
    return Response(status=200)


AXIS_ADMIN_TOKEN = os.environ.get("AXIS_ADMIN_TOKEN", "")
TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
AXIS_OWNER_TELEGRAM_USER_ID = os.environ.get("AXIS_OWNER_TELEGRAM_USER_ID", "")
TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "").lstrip("@")


def _forbidden(message="unauthorized", status=401):
    return jsonify({"error": message}), status


def require_admin(view):
    """Protege operaciones internas con token o sesión móvil emparejada."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not AXIS_ADMIN_TOKEN:
            return _forbidden("admin security not configured", 503)
        supplied = request.headers.get("X-AXIS-Admin-Token", "")
        if supplied and hmac.compare_digest(supplied, AXIS_ADMIN_TOKEN):
            return view(*args, **kwargs)
        if _mobile_session_valida(request.cookies.get("axis_mobile_session", "")):
            return view(*args, **kwargs)
        return _forbidden()
    return wrapped


def require_telegram_webhook(view):
    """Acepta callbacks solo cuando Telegram entrega el secreto configurado."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not TELEGRAM_WEBHOOK_SECRET:
            return _forbidden("telegram webhook security not configured", 503)
        supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not supplied or not hmac.compare_digest(supplied, TELEGRAM_WEBHOOK_SECRET):
            return _forbidden("invalid telegram webhook", 403)
        return view(*args, **kwargs)
    return wrapped

# ═══════════════════════════════════════════════════════════
# CONFIGURACION
# ═══════════════════════════════════════════════════════════
TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
# Servicios vestigiales: no se usan desde v8.17; nunca conservar claves en código.
TWELVEDATA_KEY   = os.environ.get("TWELVEDATA_KEY", "")
FINNHUB_KEY       = os.environ.get("FINNHUB_KEY", "")
from axis_config import EST  # AX-003: movido a axis_config.py, mismo valor

# ── TRADIER SANDBOX (ordenes paper trading) ──
import json

TRADIER_TOKEN   = os.environ.get("TRADIER_TOKEN", "")
TRADIER_ACCOUNT = os.environ.get("TRADIER_ACCOUNT", "")
from axis_config import TRADIER_BASE  # AX-003: mismo valor
TRADIER_HEADERS = {
    "Authorization": f"Bearer {TRADIER_TOKEN}",
    "Accept":        "application/json",
}

# ── TRADIER PRODUCCION (datos historicos de mercado) ──
TRADIER_TOKEN_REAL   = os.environ.get("TRADIER_TOKEN_REAL", "")
from axis_config import TRADIER_BASE_REAL  # AX-003: mismo valor
TRADIER_HEADERS_REAL = {
    "Authorization": f"Bearer {TRADIER_TOKEN_REAL}",
    "Accept":        "application/json",
}

# Ordenes pendientes de confirmacion — clave: orden_id
# Valor: { "opcion": {...}, "ts": datetime, "chat_id": int, "message_id": int }
ordenes_pendientes = {}
from axis_config import ORDEN_TIMEOUT_MIN  # AX-003: mismo valor (15)

# AX-007: logica movida a axis_orders.py (recibe ordenes_pendientes como
# parametro en vez de leerlo/escribirlo como global propio del modulo).
# Wrappers mantienen los nombres y firmas originales sin argumentos para
# no romper ninguna llamada existente en server.py.
import axis_orders as _axis_orders

def guardar_ordenes():
    _axis_orders.guardar_ordenes(ordenes_pendientes)

def cargar_ordenes():
    _axis_orders.cargar_ordenes(ordenes_pendientes)

def loop_limpiar_ordenes():
    """Thread que cada 60s revisa ordenes expiradas y las cancela con aviso a Telegram"""
    while True:
        time.sleep(60)
        try:
            ahora = datetime.now(pytz.utc)
            expiradas = [
                oid for oid, d in list(ordenes_pendientes.items())
                if (ahora - d["ts"]).total_seconds() > ORDEN_TIMEOUT_MIN * 60
            ]
            for oid in expiradas:
                datos = ordenes_pendientes.pop(oid, None)
                if not datos:
                    continue
                en_revision = datos.get("estado_ejecucion") == "REVIEW_REQUIRED"
                actualizar_alerta(
                    datos.get("alert_id"), "CANCELLED",
                    "TRADIER_REVIEW_EXPIRED" if en_revision else "ORDER_EXPIRED",
                    decision="REVIEW_EXPIRED" if en_revision else "EXPIRED",
                )
                guardar_ordenes()
                # Editar mensaje original en Telegram
                try:
                    texto_original = datos.get("texto_original", "")
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText",
                        json={
                            "chat_id":    datos["chat_id"],
                            "message_id": datos["message_id"],
                            "text":       (
                                f"{texto_original}\n\n━━━━━━━━━━━━━━━━━━\n"
                                "⚠️ <b>Revisión Tradier vencida</b> — no se reintentó la compra."
                                if en_revision else
                                f"{texto_original}\n\n━━━━━━━━━━━━━━━━━━\n⏰ <b>Orden expirada</b> — no se ejecutó (>{ORDEN_TIMEOUT_MIN} min sin respuesta)"
                            ),
                            "parse_mode": "HTML",
                        },
                        timeout=5
                    )
                except Exception as e:
                    print(f"Error editando mensaje expirado {oid}: {e}")
                print(f"Orden expirada y eliminada — ID: {oid}")
        except Exception as e:
            print(f"Error loop_limpiar_ordenes: {e}")

# ── VERSIÓN ──────────────────────────────────────────────────────────────────
AXIS_VERSION = "9.03"
_BUILD_DATE  = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def _git_commit_short():
    for env_var in ("RAILWAY_GIT_COMMIT_SHA", "GIT_COMMIT", "SOURCE_VERSION", "COMMIT_SHA"):
        val = os.environ.get(env_var, "")
        if val:
            return val[:7]
    try:
        import subprocess, os.path as _osp
        if _osp.isdir(".git"):
            return subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL, timeout=3
            ).decode().strip()
    except Exception:
        pass
    return "unknown"

_GIT_COMMIT   = _git_commit_short()
_ENVIRONMENT  = "production" if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_SERVICE_NAME") else "development"
_DEPLOY_ID    = (os.environ.get("RAILWAY_DEPLOYMENT_ID") or os.environ.get("RAILWAY_DEPLOYMENT_INSTANCE_ID") or "unknown")[:12]
_SERVICE_NAME = os.environ.get("RAILWAY_SERVICE_NAME", "unknown")

# AX-003: ACTIVOS, HORAS_REPORTE, ACTIVOS_SPY, SISTEMA_ACTIVO y switches
# de estrategia movidos a axis_config.py, mismos valores y nombres.
from axis_config import (
    ACTIVOS, HORAS_REPORTE, ACTIVOS_SPY, SISTEMA_ACTIVO,
    VR1_ON, RPG_ON, GNA_ON, GBA_ON,
)

# ═══════════════════════════════════════════════════════════
# ESTADO POR ACTIVO
# ═══════════════════════════════════════════════════════════
def estado_diario_vacio():
    return {
        "fecha":              None,
        "v1_close":           None,
        "v1_open":            None,
        "v1_low":             None,
        "v7_ayer_close":      None,
        "señales_disparadas": [],
        "p2_inicio_dia":      {},
        "rpg_piso":           None,
        "rpg_activo":         False,
        "rpg_fired":          False,
        "rpg_s20":            None,
        "rpg_s40":            None,
        "gna_activo":         False,
        "gna_fired":          False,
        "gba_activo":         False,
        "gba_fired":          False,
        "vr1_fired":          False,
        "hed_fired":          False,
        "cnf_fired":          False,
        "rcb_fired":          False,
        # PM40
        "pm40_p1_high":       None,
        "pm40_p1_idx":        None,
        "pm40_p2_high":       None,
        "pm40_p2_idx":        None,
        "pm40_velas_bajo_p1": 0,
        "pm40_p1_maduro":     False,
        "pm40_activo":        False,
        "pm40_fired":         False,
        "pm40_vela_idx":      0,
        # 4PASOS
        "4ps_p1_low":         None,
        "4ps_p1_idx":         None,
        "4ps_p2_low":         None,
        "4ps_p2_idx":         None,
        "4ps_velas_sobre_p1": 0,
        "4ps_p1_maduro":      False,
        "4ps_activo":         False,
        "4ps_fired":          False,
        "4ps_vela_idx":       0,
        "4ps_ultima_senal":   None,
    }

# AX-009: canal_vacio movida a axis_channels.py.
from axis_channels import canal_vacio

estado_dia = {a: estado_diario_vacio() for a in ACTIVOS}
canal      = {a: canal_vacio()         for a in ACTIVOS}

# ═══════════════════════════════════════════════════════════
# PERSISTENCIA
# ═══════════════════════════════════════════════════════════
# AX-003: rutas de persistencia movidas a axis_config.py, mismos valores.
from axis_config import (
    CANALES_FILE, PORTFOLIO_FILE, ORDENES_FILE, ESTADO_FILE,
    SEÑALES_FILE, ALERTAS_FILE, BITACORA_FILE, MOBILE_ACCESS_FILE, DATA_DIR,
)
from axis_alerts import crear_alerta, actualizar_alerta, listar_alertas
DEBRIEF_FILE  = f"{DATA_DIR}/axis_debrief.json"
JOURNAL_FILE  = f"{DATA_DIR}/axis_journal.json"

# ── AX-MOBILE-001: acceso móvil emparejado con Telegram privado ──────────
# La sesión se entrega solamente al navegador que inició el código; en disco
# se guardan hashes, nunca el token de sesión ni el código de emparejamiento.
MOBILE_PAIR_SECONDS = 10 * 60
MOBILE_SESSION_SECONDS = 30 * 24 * 60 * 60
_mobile_access_lock = threading.RLock()


def _sha256(valor):
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


def _cargar_mobile_access():
    try:
        with open(MOBILE_ACCESS_FILE, "r") as f:
            datos = json.load(f)
        if isinstance(datos, dict):
            return {
                "pending": datos.get("pending", {}) if isinstance(datos.get("pending"), dict) else {},
                "sessions": datos.get("sessions", {}) if isinstance(datos.get("sessions"), dict) else {},
            }
    except (OSError, ValueError, TypeError):
        pass
    return {"pending": {}, "sessions": {}}


_mobile_access = _cargar_mobile_access()


def _guardar_mobile_access():
    os.makedirs(os.path.dirname(MOBILE_ACCESS_FILE), exist_ok=True)
    temporal = f"{MOBILE_ACCESS_FILE}.tmp"
    with open(temporal, "w") as f:
        json.dump(_mobile_access, f, ensure_ascii=False, separators=(",", ":"))
    os.chmod(temporal, 0o600)
    os.replace(temporal, MOBILE_ACCESS_FILE)


def _limpiar_mobile_access(ahora=None):
    ahora = time.time() if ahora is None else ahora
    cambio = False
    for pair_id, datos in list(_mobile_access["pending"].items()):
        try:
            expirado = float(datos.get("expires_at", 0)) <= ahora
        except (TypeError, ValueError, AttributeError):
            expirado = True
        if not isinstance(datos, dict) or expirado:
            _mobile_access["pending"].pop(pair_id, None)
            cambio = True
    for sesion_hash, datos in list(_mobile_access["sessions"].items()):
        try:
            expirada = float(datos.get("expires_at", 0)) <= ahora
        except (TypeError, ValueError, AttributeError):
            expirada = True
        if not isinstance(datos, dict) or expirada:
            _mobile_access["sessions"].pop(sesion_hash, None)
            cambio = True
    return cambio


def _mobile_session_valida(sesion):
    if not sesion or not isinstance(sesion, str):
        return False
    with _mobile_access_lock:
        cambio = _limpiar_mobile_access()
        valida = _sha256(sesion) in _mobile_access["sessions"]
        if cambio:
            _guardar_mobile_access()
        return valida


def _respuesta_mobile_autorizada(sesion):
    respuesta = jsonify({"ok": True, "authorized": True})
    respuesta.set_cookie(
        "axis_mobile_session", sesion, max_age=MOBILE_SESSION_SECONDS,
        secure=True, httponly=True, samesite="Lax", path="/",
    )
    return respuesta


def _procesar_emparejamiento_movil(message):
    """Aprueba un código solo si llega por DM desde el creador autorizado."""
    remitente = message.get("from") or {}
    chat = message.get("chat") or {}
    usuario_id = str(remitente.get("id", ""))
    chat_id = str(chat.get("id", ""))
    texto = (message.get("text") or "").strip()
    partes = texto.split()
    comando = partes[0].split("@", 1)[0].lower() if partes else ""
    if (
        not AXIS_OWNER_TELEGRAM_USER_ID
        or usuario_id != str(AXIS_OWNER_TELEGRAM_USER_ID)
        or chat_id != usuario_id
        or comando != "/axis"
        or len(partes) != 2
    ):
        return False
    if partes[1].lower() == "revoke":
        with _mobile_access_lock:
            if _mobile_access["sessions"]:
                _mobile_access["sessions"] = {}
                _guardar_mobile_access()
        if TELEGRAM_TOKEN:
            try:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": "✅ Todas las sesiones móviles AXIS fueron revocadas."},
                    timeout=5,
                )
            except requests.RequestException:
                pass
        return True
    codigo_hash = _sha256(partes[1].upper())
    with _mobile_access_lock:
        cambio = _limpiar_mobile_access()
        aprobado = False
        for datos in _mobile_access["pending"].values():
            if hmac.compare_digest(datos.get("code_hash", ""), codigo_hash):
                datos["approved_at"] = time.time()
                aprobado = True
                cambio = True
                break
        if cambio:
            _guardar_mobile_access()
    if aprobado and TELEGRAM_TOKEN:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": "✅ Acceso móvil AXIS aprobado. Regresa al navegador para abrir Derby."},
                timeout=5,
            )
        except requests.RequestException:
            pass
    return aprobado

# AX-005: cargar_señales_historicas, guardar_señales_historicas movidas a axis_storage.py
from axis_storage import cargar_señales_historicas, guardar_señales_historicas

def archivar_señales_dia(fecha):
    """v8.84: ahora guarda tambien vela y hora exacta de cada senal (no solo
    el tipo), usando señales_detalle que ya tiene esta info desde v8.81.
    Mantiene compatibilidad: si una senal no tiene detalle (senales viejas
    antes de v8.81), guarda solo el tipo sin vela/hora."""
    historial = cargar_señales_historicas()
    historial[fecha] = {}
    for simbolo in ACTIVOS:
        ed = estado_dia.get(simbolo, {})
        if ed.get("fecha") == fecha:
            detalle = ed.get("señales_detalle", [])
            if detalle:
                historial[fecha][simbolo] = [
                    {"tipo": d["tipo"], "vela": d.get("vela"), "hora": d.get("hora")}
                    for d in detalle
                ]
            else:
                disparadas = ed.get("señales_disparadas", [])
                cortos = []
                for s in disparadas:
                    if "1VR"    in s: cortos.append({"tipo": "1VR", "vela": None, "hora": None})
                    elif "RPG"  in s: cortos.append({"tipo": "RPG", "vela": None, "hora": None})
                    elif "GNA"  in s: cortos.append({"tipo": "GNA", "vela": None, "hora": None})
                    elif "GBA"  in s: cortos.append({"tipo": "GBA", "vela": None, "hora": None})
                    elif "HED"  in s: cortos.append({"tipo": "HED", "vela": None, "hora": None})
                    elif "PM40" in s: cortos.append({"tipo": "PM40", "vela": None, "hora": None})
                    elif "CNF"  in s: cortos.append({"tipo": "CNF", "vela": None, "hora": None})
                    elif "RCB"  in s: cortos.append({"tipo": "RCB", "vela": None, "hora": None})
                    elif "4PS"  in s or "4PASOS" in s: cortos.append({"tipo": "4PS", "vela": None, "hora": None})
                historial[fecha][simbolo] = cortos
        else:
            historial[fecha][simbolo] = []
    guardar_señales_historicas(historial)
    print(f"Señales archivadas para {fecha}: {historial[fecha]}")

# AX-005: logica movida a axis_storage.py (acepta estado_dia como parametro
# en vez de leerlo como global). Wrapper mantiene el nombre y firma original
# sin argumentos para no romper ninguna llamada existente en server.py.
from axis_storage import guardar_estado_dia as _guardar_estado_dia_storage

def guardar_estado_dia():
    _guardar_estado_dia_storage(estado_dia)

def cargar_estado_dia():
    global estado_dia
    try:
        if not os.path.exists(ESTADO_FILE):
            return
        with open(ESTADO_FILE, "r") as f:
            data = json.load(f)
        from datetime import date
        hoy = date.today().isoformat()
        recuperados = 0
        for a in ACTIVOS:
            if a in data and data[a].get("fecha") == hoy:
                base = estado_diario_vacio()
                base.update(data[a])
                estado_dia[a] = base
                recuperados += 1
        if recuperados:
            print(f"Estado día recuperado — {recuperados} activos con señales de hoy")
    except Exception as e:
        print(f"Error cargando estado_dia: {e}")

# ═══════════════════════════════════════════════════════════
# ANTHROPIC — ANÁLISIS DE PORTFOLIO
# ═══════════════════════════════════════════════════════════
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

def analizar_portfolio_claude(posiciones, reto):
    if not ANTHROPIC_API_KEY:
        return "API key de Anthropic no configurada."
    derby = reto  # derby recibe el objeto derby
    if not posiciones and not any(c["posicion"] for c in derby.get("caballos", [])):
        return "Sin posiciones abiertas para analizar."
    try:
        ahora = datetime.now(EST)
        contexto_pos = []
        for pos in posiciones:
            contexto_pos.append(
                f"- {pos['simbolo']} {pos['tipo']} ${pos['strike']} exp {pos['expiration']} "
                f"| Entrada: ${pos['precio_entrada']:.2f} | GTC: ${pos['precio_gtc']:.2f} "
                f"| Estrategia: {pos['estrategia']}"
                f"{' | RETO Carril #' + str(pos['carril_id']) if pos.get('es_reto') else ''}"
            )
        capital_reto = sum(c["capital"] for c in reto.get("caballos", []))
        prompt = (
            f"Eres el analista de AXIS, un sistema de trading de opciones. "
            f"Hora actual: {ahora.strftime('%A %I:%M %p EST')}. "
            f"Analiza estas posiciones abiertas y da recomendaciones concretas y breves:\n\n"
            f"POSICIONES ABIERTAS:\n" + "\n".join(contexto_pos or ["Ninguna"]) + "\n\n"
            f"RETO MILLONARIO: {'Activo' if reto['activo'] else 'Inactivo'} | "
            f"Capital total: ${capital_reto:.2f} de $1,000,000\n\n"
            f"Dame: 1) Estado general del portfolio en 1 oración. "
            f"2) Recomendación específica por posición (mantener/cerrar/subir GTC). "
            f"3) Una observación de mercado relevante. "
            f"Responde en español, máximo 150 palabras, sin markdown."
        )
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      "claude-sonnet-4-5",
                "max_tokens": 300,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=20
        )
        data = r.json()
        if r.status_code == 200:
            return data["content"][0]["text"]
        else:
            print(f"Error Anthropic: {data}")
            return f"Error al consultar Claude: {data.get('error', {}).get('message', 'desconocido')}"
    except Exception as e:
        print(f"Error analizar_portfolio_claude: {e}")
        return f"Error de conexión con Anthropic: {str(e)}"

# ═══════════════════════════════════════════════════════════
# PORTFOLIO — ESTRUCTURA Y PERSISTENCIA
# ═══════════════════════════════════════════════════════════
# AX-008: DERBY_CABALLOS, portfolio_vacio, cargar_portfolio y
# guardar_portfolio movidas a axis_portfolio.py. cargar_portfolio/
# guardar_portfolio ahora reciben/devuelven datos en vez de depender
# del global _portfolio. Wrappers mantienen los nombres y firmas
# originales sin argumentos, preservando el mismo efecto observable
# (incluyendo el guardado automatico en los 3 casos de migracion).
from axis_portfolio import DERBY_CABALLOS, portfolio_vacio
import axis_portfolio as _axis_portfolio

_portfolio = None

def cargar_portfolio():
    global _portfolio
    _portfolio, _debe_guardar = _axis_portfolio.cargar_portfolio()
    if _debe_guardar:
        guardar_portfolio()

def guardar_portfolio():
    _axis_portfolio.guardar_portfolio(_portfolio)


# ── AX-RISK-001: observación de salidas, sin ejecución de trading ─────────
# Estos niveles no son stops activos. Se registran para medir, con datos reales,
# qué protección habría conservado capital sin expulsar ganadoras.
SALIDA_SOMBRA_STOPS_PCT = (-25, -50, -75, -90)
SALIDA_SOMBRA_ACTIVACION_TRAILING_PCT = 25
SALIDA_SOMBRA_DRAWDOWNS_PCT = (-25, -50)


def _salidas_sombra_vacias():
    return {
        "version": "AX-RISK-001",
        "stops_pct": list(SALIDA_SOMBRA_STOPS_PCT),
        "trailing": {
            "activacion_mfe_pct": SALIDA_SOMBRA_ACTIVACION_TRAILING_PCT,
            "drawdowns_pct": list(SALIDA_SOMBRA_DRAWDOWNS_PCT),
        },
        "stops_cruzados": {},
        "trailing_cruzados": {},
    }


def actualizar_salidas_sombra(pos, pl_pct, mfe_pct, ahora, minutos_abierta):
    """Registra cruces hipotéticos; nunca llama a Tradier ni cierra una posición."""
    sombra = pos.setdefault("salidas_sombra", _salidas_sombra_vacias())
    sombra.setdefault("version", "AX-RISK-001")
    stops = sombra.setdefault("stops_cruzados", {})
    trailing = sombra.setdefault("trailing_cruzados", {})
    datos_base = {
        "ts": ahora.isoformat(),
        "pl_pct": round(float(pl_pct), 2),
        "mfe_pct": round(float(mfe_pct), 2),
        "minutos_abierta": int(minutos_abierta),
    }
    for nivel in SALIDA_SOMBRA_STOPS_PCT:
        clave = str(nivel)
        if pl_pct <= nivel and clave not in stops:
            stops[clave] = {"nivel_pct": nivel, **datos_base}
    if mfe_pct >= SALIDA_SOMBRA_ACTIVACION_TRAILING_PCT:
        drawdown_pct = round(float(pl_pct) - float(mfe_pct), 2)
        for nivel in SALIDA_SOMBRA_DRAWDOWNS_PCT:
            clave = str(nivel)
            if drawdown_pct <= nivel and clave not in trailing:
                trailing[clave] = {
                    "drawdown_pct": drawdown_pct,
                    "nivel_pct": nivel,
                    **datos_base,
                }
    return sombra

def registrar_posicion(opcion, estrategia, simbolo, precio_entrada, es_reto=False, carril_id=None,
                       contratos=1, tradier_orden_id=None, tradier_gtc_id=None,
                       alert_id=None, gtc_confirmada=True, gtc_error=None):
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    if not tradier_orden_id:
        raise ValueError("No se puede registrar posición sin confirmación de compra de Tradier")
    import uuid
    pos = {
        "id":               str(uuid.uuid4())[:8],
        "alert_id":         alert_id,
        "simbolo":          simbolo,
        "estrategia":       estrategia,
        "tipo":             opcion["tipo"],
        "strike":           opcion["strike"],
        "expiration":       opcion["expiration"],
        "option_symbol":    opcion["symbol"],
        "precio_entrada":   precio_entrada,
        "contratos":        contratos,
        "costo_total":      round(precio_entrada * 100 * contratos, 2),
        "precio_gtc":       round(precio_entrada * 2, 2),
        "ts_entrada":       datetime.now(EST).isoformat(),
        "es_reto":          es_reto,
        "carril_id":        carril_id,
        "estado":           "abierta",
        "tradier_orden_id": tradier_orden_id,
        "tradier_gtc_id":   tradier_gtc_id,
        "gtc_confirmada":   bool(gtc_confirmada and tradier_gtc_id),
        "gtc_error":        gtc_error,
        "historial_precios": [
            {
                "fecha":   datetime.now(EST).strftime("%Y-%m-%d"),
                "bid":     precio_entrada,
                "pl_pct":  0.0,
                "nota":    "entrada",
            }
        ],
        "pl_pct_actual":  0.0,
        "pl_pct_maximo":  0.0,
        "fecha_maximo":   datetime.now(EST).strftime("%Y-%m-%d"),
        "pl_pct_minimo":  0.0,
        "fecha_minimo":   datetime.now(EST).strftime("%Y-%m-%d"),
        "mfe_pct":        0.0,
        "mae_pct":        0.0,
        "salidas_sombra": _salidas_sombra_vacias(),
        "minutos_abierta": 0,
        "seguimiento": [
            {
                "ts":     datetime.now(EST).isoformat(),
                "bid":    precio_entrada,
                "pl_pct": 0.0,
            }
        ],
    }
    _portfolio["posiciones"].append(pos)
    if es_reto and carril_id:
        for c in _portfolio["derby"]["caballos"]:
            if c["id"] == carril_id:
                c["posicion"] = pos["id"]
                c["ronda"]   += 1
                break
    guardar_portfolio()
    actualizar_alerta(
        alert_id, "ACTIVE", "POSITION_OPENED",
        posicion_id=pos["id"], contratos=contratos,
        precio_entrada=precio_entrada,
        option_symbol=opcion.get("symbol"), strike=opcion.get("strike"),
        expiration=opcion.get("expiration"), tradier_orden_id=tradier_orden_id,
        tradier_gtc_id=tradier_gtc_id, gtc_confirmada=bool(gtc_confirmada and tradier_gtc_id),
        gtc_error=gtc_error,
    )
    return pos

# AX-004: cancelar_orden_tradier, get_bid_opcion_tradier, vender_opcion_tradier
# movidas a axis_tradier.py. Mismos nombres, mismo comportamiento.
from axis_tradier import (
    cancelar_orden_tradier,
    get_bid_opcion_tradier,
    vender_opcion_tradier,
    tiene_posicion_opcion_tradier,
)

def cerrar_posicion(pos_id, precio_cierre, motivo="panic"):
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    pos = next((p for p in _portfolio["posiciones"] if p["id"] == pos_id), None)
    if not pos:
        return None

    try:
        ts_in = datetime.fromisoformat(str(pos["ts_entrada"]).replace("Z",""))
        if ts_in.tzinfo is None:
            ts_in = EST.localize(ts_in)
        ts_out = datetime.now(EST)
        minutos_abierta = int((ts_out - ts_in).total_seconds() / 60)
    except:
        minutos_abierta = 0

    contratos = pos.get("contratos", 1)
    pl_pct = round((precio_cierre - pos["precio_entrada"]) / pos["precio_entrada"] * 100, 2)
    pl_usd = round((precio_cierre - pos["precio_entrada"]) * 100 * contratos, 2)
    pos["precio_cierre"]   = precio_cierre
    pos["pl_pct"]          = pl_pct
    pos["pl_usd"]          = pl_usd
    pos["motivo_cierre"]   = motivo
    pos["ts_cierre"]       = datetime.now(EST).isoformat()
    pos["minutos_abierta"] = minutos_abierta
    pos["estado"]          = "cerrada"
    pos["pl_pct_actual"]   = pl_pct
    pos["pl_usd_actual"]   = pl_usd
    pos["bid_actual"]      = precio_cierre
    pos["ts_ultimo_seguimiento"] = pos["ts_cierre"]
    pos.setdefault("seguimiento", []).append({
        "ts": pos["ts_cierre"], "bid": precio_cierre,
        "pl_pct": pl_pct, "pl_usd": pl_usd, "nota": motivo,
    })

    fecha_cierre = datetime.now(EST).strftime("%Y-%m-%d")
    historial_p  = pos.get("historial_precios", [])
    fechas_exist = [h["fecha"] for h in historial_p]
    if fecha_cierre not in fechas_exist:
        historial_p.append({
            "fecha":  fecha_cierre,
            "bid":    precio_cierre,
            "pl_pct": pl_pct,
            "nota":   motivo,
        })
    else:
        for h in historial_p:
            if h["fecha"] == fecha_cierre:
                h["bid"]    = precio_cierre
                h["pl_pct"] = pl_pct
                h["nota"]   = motivo
    pos["historial_precios"] = historial_p

    if pl_pct > pos.get("pl_pct_maximo", 0):
        pos["pl_pct_maximo"] = pl_pct
        pos["fecha_maximo"]  = fecha_cierre
    if pl_pct < pos.get("pl_pct_minimo", 0):
        pos["pl_pct_minimo"] = pl_pct
        pos["fecha_minimo"]  = fecha_cierre
    pos["mfe_pct"] = pos.get("pl_pct_maximo", 0)
    pos["mae_pct"] = pos.get("pl_pct_minimo", 0)
    actualizar_salidas_sombra(
        pos, pl_pct, pos["mfe_pct"], datetime.now(EST), minutos_abierta,
    )

    if pos.get("es_reto") and pos.get("carril_id"):
        derby = _portfolio["derby"]
        for c in derby["caballos"]:
            if c["id"] == pos["carril_id"] and c.get("capital_inicial", 0) > 0:
                nuevo_capital = round(c["capital"] + pl_usd, 2)
                c["capital"]  = nuevo_capital
                c["posicion"] = None
                c["historial"].append({
                    "ronda":         c["ronda"],
                    "pl_usd":        pl_usd,
                    "pl_pct":        pl_pct,
                    "capital_final": nuevo_capital,
                    "motivo":        motivo,
                })
                CAPITAL_MINIMO = 280
                if nuevo_capital < CAPITAL_MINIMO:
                    c["eliminado"] = True
                    enviar_telegram(
                        f"💀 <b>{c['nombre']} ELIMINADO — REAL LAZARO-PALMA</b>\n"
                        f"Capital final: ${nuevo_capital:.2f} — insuficiente para siguiente carrera\n"
                        f"Capital inicial fue: ${c.get('capital_inicial', 0):.2f}"
                    )
                # Verificar si queda un solo caballo vivo
                vivos = [x for x in derby["caballos"] if not x.get("eliminado")]
                if len(vivos) == 1 and derby["activo"]:
                    ganador = vivos[0]
                    derby["ganador"] = ganador["nombre"]
                    derby["activo"]  = False
                    if ganador["capital"] > 0 and ganador["posicion"] is not None:
                        derby["esperando_cierre"] = True
                        enviar_telegram(
                            f"🏆 <b>GANADOR DEL REAL LAZARO-PALMA: {ganador['nombre']}</b>\n"
                            f"Capital acumulado: ${ganador['capital']:.2f}\n"
                            f"⏳ Esperando cierre de posición para confirmar premio final..."
                        )
                    else:
                        derby["esperando_cierre"] = False
                        enviar_telegram(
                            f"🏆 <b>GANADOR DEL REAL LAZARO-PALMA: {ganador['nombre']}</b>\n"
                            f"Premio metálico: ${ganador['capital']:.2f}\n"
                            f"🏇 Derby finalizado — activa uno nuevo cuando quieras"
                        )
                break

    _portfolio["posiciones"] = [p for p in _portfolio["posiciones"] if p["id"] != pos_id]
    _portfolio["historial"].append(pos)
    guardar_portfolio()

    actualizar_alerta(
        pos.get("alert_id"), "CLOSED", "POSITION_CLOSED",
        precio_cierre=precio_cierre, pl_pct=pl_pct, pl_usd=pl_usd,
        motivo_cierre=motivo, minutos_abierta=minutos_abierta,
        ts_cierre=pos["ts_cierre"], mfe_pct=pos.get("mfe_pct", 0),
        mae_pct=pos.get("mae_pct", 0),
    )

    emoji  = "✅" if pl_pct > 0 else "🔴"
    t_str  = f"{minutos_abierta//60}h {minutos_abierta%60}m" if minutos_abierta >= 60 else f"{minutos_abierta}m"
    enviar_telegram(
        f"{emoji} <b>Posición cerrada — {pos['simbolo']}</b>\n"
        f"<b>Alert ID:</b> {pos.get('alert_id') or 'LEGACY-' + pos['id']}\n"
        f"<b>Estrategia:</b> {pos.get('estrategia', 'AXIS')}\n"
        f"<b>Motivo:</b> {motivo}\n"
        f"<b>{pos['tipo']} ${pos['strike']} exp {pos['expiration']}</b>\n"
        f"<b>Contratos:</b> {contratos} | <b>Tiempo:</b> {t_str}\n"
        f"<b>P&L:</b> {'+' if pl_pct > 0 else ''}{pl_pct}% | ${'+' if pl_usd > 0 else ''}{pl_usd:.2f}\n"
        f"<b>MFE:</b> {pos.get('mfe_pct', 0):+.2f}% | <b>MAE:</b> {pos.get('mae_pct', 0):+.2f}%\n"
        f"<b>Entrada:</b> ${pos['precio_entrada']:.2f} → <b>Cierre:</b> ${precio_cierre:.2f}"
    )
    return pos


INCIDENTE_EJECUCION_SIN_CONFIRMACION_DESDE = date(2026, 8, 3)


def _sin_confirmacion_tradier(pos):
    """Incidente documentado desde 2026-08-03; preserva registros legacy ambiguos."""
    try:
        fecha_entrada = date.fromisoformat(str(pos.get("ts_entrada", ""))[:10])
    except (TypeError, ValueError):
        return False
    return (
        fecha_entrada >= INCIDENTE_EJECUCION_SIN_CONFIRMACION_DESDE
        and not pos.get("alert_id")
        and not pos.get("tradier_orden_id")
        and not pos.get("integridad_ejecucion")
    )


def reconciliar_posiciones_sin_confirmacion(confirmar=False):
    """Anula registros creados por el defecto histórico sin alterar órdenes reales.

    Es idempotente: solo toca el incidente documentado desde 2026-08-03, sin
    alert_id, sin orden Tradier y sin marca previa de integridad. Las
    anulaciones permanecen auditables en historial y quedan fuera de P&L, win
    rate y tuning.
    """
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()

    abiertas = [p for p in _portfolio.get("posiciones", []) if _sin_confirmacion_tradier(p)]
    cerradas = [p for p in _portfolio.get("historial", []) if _sin_confirmacion_tradier(p)]
    resultado = {
        "abiertas_candidatas": [p.get("id") for p in abiertas],
        "cerradas_candidatas": [p.get("id") for p in cerradas],
        "confirmado": bool(confirmar),
    }
    if not confirmar:
        return resultado

    ahora = datetime.now(EST).isoformat()
    for pos in abiertas:
        pos["estado"] = "anulada"
        pos["motivo_cierre"] = "tradier_ejecucion_no_confirmada"
        pos["ts_cierre"] = ahora
        pos["ts_anulacion"] = ahora
        pos["integridad_ejecucion"] = "NO_CONFIRMADA"
        pos["excluida_metricas"] = True
        pos["precio_cierre"] = None
        pos["pl_pct"] = None
        pos["pl_usd"] = None
        if pos.get("es_reto") and pos.get("carril_id"):
            for caballo in _portfolio.get("derby", {}).get("caballos", []):
                if caballo.get("id") == pos["carril_id"] and caballo.get("posicion") == pos["id"]:
                    caballo["posicion"] = None
                    break
    for pos in cerradas:
        pos["integridad_ejecucion"] = "NO_CONFIRMADA"
        pos["excluida_metricas"] = True
        pos["motivo_anulacion"] = "tradier_ejecucion_no_confirmada"
        pos["ts_anulacion"] = ahora

    if abiertas:
        ids_abiertas = {p["id"] for p in abiertas}
        _portfolio["posiciones"] = [p for p in _portfolio["posiciones"] if p.get("id") not in ids_abiertas]
        _portfolio["historial"].extend(abiertas)
    guardar_portfolio()
    resultado["abiertas_anuladas"] = len(abiertas)
    resultado["cerradas_marcadas"] = len(cerradas)
    return resultado

# AX-009: CANALES_DEFAULT, guardar_canales y cargar_canales movidas a
# axis_channels.py. guardar_canales/cargar_canales reciben canal y ACTIVOS
# como parametros (modifican canal in-place). Wrappers mantienen los
# nombres y firmas originales sin argumentos para no romper ninguna
# llamada existente en server.py.
from axis_channels import CANALES_DEFAULT
import axis_channels as _axis_channels

def guardar_canales():
    _axis_channels.guardar_canales(canal, ACTIVOS, CANALES_FILE)

def cargar_canales():
    _axis_channels.cargar_canales(canal, ACTIVOS, CANALES_FILE, EST)

# ═══════════════════════════════════════════════════════════
# FESTIVOS Y DIA DE MERCADO
# ═══════════════════════════════════════════════════════════
def calcular_pascua(year):
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day   = ((h + l - 7 * m + 114) % 31) + 1
    from datetime import date
    return date(year, month, day)

def calcular_festivos(year):
    from datetime import date, timedelta
    festivos = set()
    def observado(d):
        if d.weekday() == 5: return d - timedelta(days=1)
        if d.weekday() == 6: return d + timedelta(days=1)
        return d
    def nth_weekday(year, month, weekday, n):
        d = date(year, month, 1)
        days_ahead = weekday - d.weekday()
        if days_ahead < 0: days_ahead += 7
        return d + timedelta(days=days_ahead) + timedelta(weeks=n-1)
    def last_weekday(year, month, weekday):
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        d = date(year, month, last_day)
        return d - timedelta(days=(d.weekday() - weekday) % 7)
    festivos.add(observado(date(year, 1, 1)))
    festivos.add(nth_weekday(year, 1, 0, 3))
    festivos.add(nth_weekday(year, 2, 0, 3))
    festivos.add(calcular_pascua(year) - timedelta(days=2))
    festivos.add(last_weekday(year, 5, 0))
    festivos.add(observado(date(year, 6, 19)))
    festivos.add(observado(date(year, 7, 4)))
    festivos.add(nth_weekday(year, 9, 0, 1))
    festivos.add(nth_weekday(year, 11, 3, 4))
    festivos.add(observado(date(year, 12, 25)))
    return festivos

_festivos_cache = {}

def es_dia_mercado(dt=None):
    from datetime import date
    if dt is None: dt = datetime.now(EST)
    if dt.weekday() >= 5: return False
    año = dt.year
    if año not in _festivos_cache:
        _festivos_cache[año] = calcular_festivos(año)
    return date(dt.year, dt.month, dt.day) not in _festivos_cache[año]

# ═══════════════════════════════════════════════════════════
# TELEGRAM
# ═══════════════════════════════════════════════════════════
# AX-006: enviar_telegram movida a axis_telegram.py. Mismo nombre,
# mismo comportamiento, mismo parse_mode HTML, mismo timeout.
from axis_telegram import enviar_telegram
from axis_reconciliation_notify import (
    notification_status,
    reconciliation_notification_loop,
)

# ═══════════════════════════════════════════════════════════
# UTILIDAD — Dias habiles
# ═══════════════════════════════════════════════════════════
def restar_dias_habiles(fecha, dias):
    actual = fecha
    contados = 0
    while contados < dias:
        actual -= timedelta(days=1)
        if actual.weekday() < 5:
            contados += 1
    return actual

# ═══════════════════════════════════════════════════════════
# BASE DE DATOS LOCAL DE VELAS
# ═══════════════════════════════════════════════════════════
# AX-005: ruta_velas_local, cargar_velas_local, guardar_velas_local movidas
# a axis_storage.py. Mismos nombres, mismo comportamiento, mismo formato JSON.
from axis_storage import ruta_velas_local, cargar_velas_local, guardar_velas_local

# AX-010: agregar_barra_diaria, rellenar_dias_faltantes,
# construir_base_datos_activo, actualizar_velas_local, construir_base_datos
# y get_velas movidas a axis_market.py. es_dia_mercado y restar_dias_habiles
# permanecen en server.py (se usan en mucho mas que datos de mercado) -- para
# evitar import circular, las funciones de axis_market.py que las necesitan
# las reciben como parametro. Los wrappers aqui las inyectan automaticamente,
# preservando exactamente las mismas firmas publicas originales (sin
# parametros nuevos visibles para el resto de server.py).
import axis_market as _axis_market

def agregar_barra_diaria(simbolo, fecha_str=None):
    return _axis_market.agregar_barra_diaria(simbolo, fecha_str)

def rellenar_dias_faltantes(simbolo, dias_atras=10):
    return _axis_market.rellenar_dias_faltantes(simbolo, es_dia_mercado, dias_atras)

def construir_base_datos_activo(simbolo):
    return _axis_market.construir_base_datos_activo(simbolo, restar_dias_habiles)

def actualizar_velas_local(simbolo):
    return _axis_market.actualizar_velas_local(simbolo, restar_dias_habiles)

def construir_base_datos():
    return _axis_market.construir_base_datos(es_dia_mercado, restar_dias_habiles)

def get_velas(simbolo, outputsize=280):
    return _axis_market.get_velas(simbolo, restar_dias_habiles, outputsize)

# ═══════════════════════════════════════════════════════════
# CALCULAR SMA
# ═══════════════════════════════════════════════════════════
def calcular_sma(velas, periodo):
    if len(velas) < periodo:
        return None
    cierres = [float(v["close"]) for v in velas[:periodo]]
    return sum(cierres) / periodo

# ═══════════════════════════════════════════════════════════
# CANAL — CALCULOS
# ═══════════════════════════════════════════════════════════
def ts_a_datetime(fecha_str, hora_est):
    dt = datetime.strptime(f"{fecha_str} {hora_est:02d}:00:00", "%Y-%m-%d %H:%M:%S")
    return EST.localize(dt)

def velas_mercado_entre(dt_inicio, dt_fin):
    if dt_fin <= dt_inicio:
        return 0
    count = 0
    from datetime import timedelta
    cur = dt_inicio.replace(minute=0, second=0, microsecond=0)
    while cur < dt_fin:
        h = cur.hour
        if es_dia_mercado(cur) and 9 <= h <= 15:
            count += 1
        cur += timedelta(hours=1)
    return count

def calcular_techo_canal(simbolo, ahora_dt):
    c = canal[simbolo]
    if not c["on"] or c["apagado"] or not c["p1"] or not c["p2"]:
        return None
    try:
        p2_high = c["p2_actual_high"] if c["p2_actual_high"] else c["p2"]["high"]
        dt_p2   = c["p2_actual_ts"] if c["p2_actual_ts"] else ts_a_datetime(c["p2"]["fecha"], c["p2"]["hora_est"])
        dt_p1   = ts_a_datetime(c["p1"]["fecha"], c["p1"]["hora_est"])

        velas_p1_p2    = velas_mercado_entre(dt_p1, dt_p2)
        velas_p1_ahora = velas_mercado_entre(dt_p1, ahora_dt)

        if velas_p1_p2 <= 0:
            return None
        slope = (p2_high - c["p1"]["high"]) / velas_p1_p2
        return c["p1"]["high"] + slope * velas_p1_ahora
    except Exception as e:
        print(f"Error calcular techo {simbolo}: {e}")
        return None

def calcular_piso_mitad_canal(simbolo, ahora_dt):
    c = canal[simbolo]
    if not c["p3"]:
        return None, None
    try:
        techo_en_p3_dt = ts_a_datetime(c["p3"]["fecha"], c["p3"]["hora_est"])
        techo_en_p3    = calcular_techo_canal(simbolo, techo_en_p3_dt)
        if not techo_en_p3:
            return None, None
        distancia = techo_en_p3 - c["p3"]["low"]
        if distancia <= 0:
            return None, None
        techo_ahora = calcular_techo_canal(simbolo, ahora_dt)
        if not techo_ahora:
            return None, None
        piso  = techo_ahora - distancia
        mitad = piso + distancia / 2
        return piso, mitad
    except Exception as e:
        print(f"Error calcular piso {simbolo}: {e}")
        return None, None

# ═══════════════════════════════════════════════════════════
# RESET DIARIO POR ACTIVO
# ═══════════════════════════════════════════════════════════
def reset_diario_activo(simbolo, fecha_hoy, v7_ayer_close):
    estado_dia[simbolo] = estado_diario_vacio()
    estado_dia[simbolo]["fecha"]         = fecha_hoy
    estado_dia[simbolo]["v7_ayer_close"] = v7_ayer_close
    print(f"Reset {simbolo} — V7 ayer: ${v7_ayer_close:.2f}" if v7_ayer_close else f"Reset {simbolo} — sin V7 ayer")

# ═══════════════════════════════════════════════════════════
# 4PASOS — VERIFICACION SLOPE (max 2 lows cortados)
# ═══════════════════════════════════════════════════════════
def verificar_slope_4ps(p1_low, p1_idx, p2_low_cand, p2_idx_cand, historial_lows):
    """
    Verifica que el slope P1->P2_candidato no corte NINGUN low intermedio (0 tolerancia).
    historial_lows: lista de (idx, low) de velas entre P1 y P2 candidato.
    Tambien rechaza si P2 candidato es <= P1 (P2 siempre debe ser mayor que P1).
    Retorna True solo si es completamente valido (0 lows cortados).
    """
    if p2_idx_cand <= p1_idx:
        return False
    if p2_low_cand <= p1_low:
        return False
    slope = (p2_low_cand - p1_low) / (p2_idx_cand - p1_idx)
    for idx, low in historial_lows:
        if idx <= p1_idx or idx >= p2_idx_cand:
            continue
        proyeccion = p1_low + slope * (idx - p1_idx)
        if low < proyeccion:
            return False
    return True

# ═══════════════════════════════════════════════════════════
# EVALUAR VELA POR ACTIVO
# ═══════════════════════════════════════════════════════════
def preparar_contexto_vela(simbolo, velas, ahora):
    """AX-012B: extraida de evaluar_activo() sin cambiar comportamiento.
    Localiza la vela correspondiente a la hora actual y extrae sus datos
    basicos. Funcion pura -- no lee ni modifica estado_dia ni canal."""
    hora = ahora.hour

    vela_actual = None
    for v in velas:
        dt_v = datetime.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S")
        if dt_v.hour == hora - 1:
            vela_actual = v
            break

    if not vela_actual:
        print(f"{simbolo}: no se encontro vela para hora {hora-1}")
        return None

    v_open  = float(vela_actual["open"])
    v_close = float(vela_actual["close"])
    v_high  = float(vela_actual["high"])
    v_low   = float(vela_actual["low"])
    fecha_hoy = datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")

    return {
        "hora":        hora,
        "vela_actual": vela_actual,
        "v_open":      v_open,
        "v_close":     v_close,
        "v_high":      v_high,
        "v_low":       v_low,
        "fecha_hoy":   fecha_hoy,
    }

def evaluar_gna(simbolo, ed, velas, v_open, v_close, v_alcista, v7_ayer, v1_close, hora_vela, es_v1):
    """AX-012C: extraida de evaluar_activo() sin cambiar comportamiento.
    Contiene EXACTAMENTE los 2 bloques de GNA que existian inline:
    activacion en V1 (es_v1=True) y disparo en V2-V7 (es_v1=False).
    Recibe explicitamente todas las variables necesarias -- no lee nada
    implicito de un scope compartido."""
    if es_v1:
        # GNA
        if GNA_ON and v7_ayer and v_close > v_open and not ed["gna_fired"]:
            gap_alza = (v_open - v7_ayer) / v7_ayer * 100
            if gap_alza >= 0.1:
                sma20 = calcular_sma(velas, 20)
                sma40 = calcular_sma(velas, 40)
                if sma20 and sma40 and sma20 > sma40:
                    ed["gna_activo"] = True
                    print(f"{simbolo} GNA activado — techo: ${v_close:.2f}")
    else:
        # GNA
        if GNA_ON and ed["gna_activo"] and not ed["gna_fired"] and v1_close:
            if v_alcista and v_close > v1_close:
                ed["gna_fired"]  = True
                ed["gna_activo"] = False
                guardar_estado_dia()
                tipo = "GNA" if hora_vela == 10 else "GNA+2"
                enviar_senal_con_botones(
                    simbolo, f"{tipo} — GAP NORMAL ALZA",
                    f"{hora_vela+1}:00 EST", v_close, "CALL",
                    f"<b>Techo V1:</b> ${v1_close:.2f} | <b>Cierre:</b> ${v_close:.2f}\n"
                )

def evaluar_gba(simbolo, ed, v_open, v_close, v_alcista, v7_ayer, v1_close, hora_vela, es_v1):
    """AX-012D: extraida de evaluar_activo() sin cambiar comportamiento.
    Contiene EXACTAMENTE los 2 bloques de GBA que existian inline:
    activacion en V1 (es_v1=True) y disparo en V2-V7 (es_v1=False).
    Recibe explicitamente todas las variables necesarias -- no lee nada
    implicito de un scope compartido."""
    if es_v1:
        # GBA
        if GBA_ON and v7_ayer and v_close > v_open and not ed["gba_fired"]:
            gap_baja = (v7_ayer - v_open) / v7_ayer * 100
            if gap_baja >= 0.1:
                ed["gba_activo"] = True
                print(f"{simbolo} GBA activado — techo: ${v_close:.2f}")
    else:
        # GBA
        if GBA_ON and ed["gba_activo"] and not ed["gba_fired"] and v1_close:
            if v_alcista and v_close > v1_close:
                ed["gba_fired"]  = True
                ed["gba_activo"] = False
                guardar_estado_dia()
                tipo = "GBA" if hora_vela == 10 else "GBA+2"
                enviar_senal_con_botones(
                    simbolo, f"{tipo} — GAP BAJISTA ALZA",
                    f"{hora_vela+1}:00 EST", v_close, "CALL",
                    f"<b>Techo V1:</b> ${v1_close:.2f} | <b>Cierre:</b> ${v_close:.2f}\n"
                )

def evaluar_rpg_activacion(simbolo, ed, velas, v_open, v_close, v_low, v7_ayer):
    """AX-012E: extraida de evaluar_activo() sin cambiar comportamiento.
    Contiene EXACTAMENTE el bloque de activacion RPG en V1.
    Recibe explicitamente todas las variables necesarias."""
    # RPG — gap mínimo 0.5%, V1 verde
    if RPG_ON and v7_ayer and v_close > v_open and not ed["rpg_fired"]:
        gap = abs(v_open - v7_ayer) / v7_ayer * 100
        if gap >= 0.5:
            ed["rpg_activo"] = True
            ed["rpg_piso"]   = v_low
            ed["rpg_s20"]    = calcular_sma(velas, 20)
            ed["rpg_s40"]    = calcular_sma(velas, 40)
            print(f"{simbolo} RPG activado — gap {gap:.2f}% piso: ${v_low:.2f}")

def evaluar_rpg_disparo(simbolo, ed, vela_actual, v_close, hora_vela):
    """AX-012E: extraida de evaluar_activo() sin cambiar comportamiento.
    Contiene EXACTAMENTE el bloque de disparo RPG en V2-V7.
    Recibe explicitamente todas las variables necesarias."""
    # RPG — dispara siempre con ruptura del piso (v8.77).
    # Condicion adicional (RCB 30% o SMA20>SMA40) solo decide el label RPG vs RPG+,
    # nunca bloquea el disparo. Mismo patron que el fix de 1VR en v8.63.
    if RPG_ON and ed["rpg_activo"] and not ed["rpg_fired"] and ed["rpg_piso"]:
        if v_close < ed["rpg_piso"]:
            ahora_dt_rpg = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))
            techo_rpg    = calcular_techo_canal(simbolo, ahora_dt_rpg)
            _, mitad_rpg = calcular_piso_mitad_canal(simbolo, ahora_dt_rpg)
            c_rpg        = canal[simbolo]
            zona_30_rpg = None
            if techo_rpg and mitad_rpg:
                zona_30_rpg = techo_rpg - (techo_rpg - mitad_rpg) * 0.30
            en_rcb_30_rpg = (
                c_rpg["on"] and not c_rpg["apagado"] and c_rpg["p3"] is not None
                and techo_rpg is not None and zona_30_rpg is not None
                and zona_30_rpg <= v_close <= techo_rpg
            )
            s20_rpg = ed.get("rpg_s20")
            s40_rpg = ed.get("rpg_s40")
            sma20_gt_sma40 = s20_rpg and s40_rpg and s20_rpg > s40_rpg
            ed["rpg_fired"]  = True
            ed["rpg_activo"] = False
            guardar_estado_dia()
            label_rpg = "RPG+" if (en_rcb_30_rpg or sma20_gt_sma40) else "RPG"
            if en_rcb_30_rpg:
                extra_rpg = f"<b>Canal RCB:</b> Techo ${techo_rpg:.2f} | Zona 30%: ${zona_30_rpg:.2f}\n"
            elif sma20_gt_sma40:
                extra_rpg = f"<b>SMA20:</b> ${s20_rpg:.2f} > <b>SMA40:</b> ${s40_rpg:.2f}\n"
            else:
                extra_rpg = ""
            enviar_senal_con_botones(
                simbolo, f"{label_rpg} — RUPTURA PISO GAP",
                f"{hora_vela+1}:00 EST", v_close, "PUT",
                f"<b>Piso V1:</b> ${ed['rpg_piso']:.2f} | <b>Cierre:</b> ${v_close:.2f}\n{extra_rpg}"
            )

def reset_diario_si_aplica(simbolo, velas, fecha_hoy, ed, c, hora):
    """AX-012F: extraida de evaluar_activo() sin cambiar comportamiento.
    Contiene EXACTAMENTE el bloque de reset diario, incluyendo la
    reconstruccion completa de 1VR/RPG/GNA/GBA tal cual existia inline.
    NO reutiliza evaluar_1vr/evaluar_rpg_activacion/evaluar_gna/evaluar_gba
    -- la logica de reconstruccion permanece duplicada, sin cambios,
    segun regla explicita de este sprint.
    Recibe `hora` porque la reconstruccion 1VR la necesita para decidir
    si enviar la alerta (solo si hora == 10).
    Devuelve (ed, c) actualizados."""
    # Reset diario si es nueva fecha
    if ed["fecha"] != fecha_hoy:
        v7_ayer = None
        for v in velas[1:]:
            dt_v = datetime.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S")
            if dt_v.strftime("%Y-%m-%d") != fecha_hoy and dt_v.hour == 15:
                v7_ayer = float(v["close"])
                break
        reset_diario_activo(simbolo, fecha_hoy, v7_ayer)
        ed = estado_dia[simbolo]

        # Guardar P2 al inicio del día
        c = canal[simbolo]
        if c["on"] and not c["apagado"] and c.get("p2_actual_high") is not None:
            ed["p2_inicio_dia"][simbolo] = c["p2_actual_high"]

        # Reconstruir estado desde historico
        for v in velas:
            dt_v = datetime.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S")
            if dt_v.strftime("%Y-%m-%d") == fecha_hoy and dt_v.hour == 9:
                v1_open_r  = float(v["open"])
                v1_close_r = float(v["close"])
                v1_low_r   = float(v["low"])
                ed["v1_close"] = v1_close_r
                ed["v1_open"]  = v1_open_r
                ed["v1_low"]   = v1_low_r
                v7_c = ed["v7_ayer_close"]

                # ══════════════════════════════════════════════════════
                # v8.63 FIX — 1VR reconstrucción verifica condiciones
                # adicionales igual que la evaluación normal
                # ══════════════════════════════════════════════════════
                if VR1_ON and v1_close_r < v1_open_r and not ed["vr1_fired"]:
                    ahora_dt_r  = EST.localize(datetime.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S"))
                    techo_r     = calcular_techo_canal(simbolo, ahora_dt_r)
                    _, mitad_r  = calcular_piso_mitad_canal(simbolo, ahora_dt_r)
                    c_r         = canal[simbolo]
                    sma20_r     = calcular_sma(velas, 20)
                    sma40_r     = calcular_sma(velas, 40)
                    zona_30_r   = None
                    if techo_r and mitad_r:
                        zona_30_r = techo_r - (techo_r - mitad_r) * 0.30
                    en_rcb_30_r = (
                        c_r["on"] and not c_r["apagado"] and c_r["p3"] is not None
                        and techo_r is not None and zona_30_r is not None
                        and zona_30_r <= v1_close_r <= techo_r
                    )
                    sma40_gt_sma20_r = sma40_r and sma20_r and sma40_r > sma20_r
                    # 1VR dispara siempre que V1 cierre roja
                    # Condición adicional solo cambia el label (1VR vs 1VR+)
                    if hora == 10:
                        label_vr = "1VR+" if en_rcb_30_r else "1VR"
                        if en_rcb_30_r:
                            extra_vr = f"<b>Canal RCB:</b> Techo ${techo_r:.2f} | Zona 30%: ${zona_30_r:.2f}\n"
                        elif sma40_gt_sma20_r:
                            extra_vr = f"<b>SMA40:</b> ${sma40_r:.2f} > <b>SMA20:</b> ${sma20_r:.2f}\n"
                        else:
                            extra_vr = ""
                        enviar_senal_con_botones(
                            simbolo, f"{label_vr} — PRIMERA VELA ROJA",
                            "10:00 EST", v1_close_r, "PUT",
                            f"<b>Open:</b> ${v1_open_r:.2f} | <b>Close:</b> ${v1_close_r:.2f}\n{extra_vr}"
                        )
                    ed["vr1_fired"] = True
                    guardar_estado_dia()

                # Reconstruir RPG
                if RPG_ON and v7_c and v1_close_r > v1_open_r:
                    gap = abs(v1_open_r - v7_c) / v7_c * 100
                    if gap >= 0.2:
                        ed["rpg_activo"] = True
                        ed["rpg_piso"]   = v1_low_r

                # Reconstruir GNA
                if GNA_ON and v7_c and v1_close_r > v1_open_r:
                    gap_alza = (v1_open_r - v7_c) / v7_c * 100
                    if gap_alza >= 0.1:
                        sma20 = calcular_sma(velas, 20)
                        sma40 = calcular_sma(velas, 40)
                        if sma20 and sma40 and sma20 > sma40:
                            ed["gna_activo"] = True

                # Reconstruir GBA
                if GBA_ON and v7_c and v1_close_r > v1_open_r:
                    gap_baja = (v7_c - v1_open_r) / v7_c * 100
                    if gap_baja >= 0.1:
                        ed["gba_activo"] = True

                print(f"{simbolo} estado reconstruido — V1 O:{v1_open_r:.2f} C:{v1_close_r:.2f}")
                break

    return ed, c

def evaluar_1vr_normal(simbolo, ed, velas, vela_actual, v_open, v_close, v_roja):
    """AX-012G: extraida de evaluar_activo() sin cambiar comportamiento.
    Contiene EXACTAMENTE el bloque de 1VR en la rama V1 normal (no la
    reconstruccion del reset diario, que permanece intacta dentro de
    reset_diario_si_aplica() segun regla explicita de este sprint).
    Recibe explicitamente todas las variables necesarias."""
    # ── 1VR — Primera Vela Roja ──
    if VR1_ON and v_roja and not ed["vr1_fired"]:
        ahora_dt_vr = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))
        techo_vr    = calcular_techo_canal(simbolo, ahora_dt_vr)
        _, mitad_vr = calcular_piso_mitad_canal(simbolo, ahora_dt_vr)
        c_vr        = canal[simbolo]
        sma20_vr    = calcular_sma(velas, 20)
        sma40_vr    = calcular_sma(velas, 40)

        zona_30 = None
        if techo_vr and mitad_vr:
            zona_30 = techo_vr - (techo_vr - mitad_vr) * 0.30
        en_rcb_30 = (
            c_vr["on"] and not c_vr["apagado"] and c_vr["p3"] is not None
            and techo_vr is not None and zona_30 is not None
            and zona_30 <= v_close <= techo_vr
        )

        sma40_gt_sma20 = sma40_vr and sma20_vr and sma40_vr > sma20_vr

        # 1VR dispara siempre que V1 cierre roja
        # Condición adicional solo cambia el label (1VR vs 1VR+)
        ed["vr1_fired"] = True
        guardar_estado_dia()
        label_vr = "1VR+" if en_rcb_30 else "1VR"
        if en_rcb_30:
            extra_vr = f"<b>Canal RCB:</b> Techo ${techo_vr:.2f} | Zona 30%: ${zona_30:.2f}\n"
        elif sma40_gt_sma20:
            extra_vr = f"<b>SMA40:</b> ${sma40_vr:.2f} > <b>SMA20:</b> ${sma20_vr:.2f}\n"
        else:
            extra_vr = ""
        enviar_senal_con_botones(
            simbolo, f"{label_vr} — PRIMERA VELA ROJA",
            "10:00 EST", v_close, "PUT",
            f"<b>Open:</b> ${v_open:.2f} | <b>Close:</b> ${v_close:.2f}\n{extra_vr}"
        )

def evaluar_canal_v1(simbolo, c, vela_actual, v_high):
    """AX-013: extraida de evaluar_activo() sin cambiar comportamiento.
    Contiene EXACTAMENTE el bloque de Canal V1 -- P2 dinamico especial
    (cualquier tipo de vela, aplica SOLO a V1). NO toca PM40, 4PASOS,
    Canal V2-V7, RPG/GNA/GBA/1VR, ni Reset Diario.
    Recibe explicitamente todas las variables necesarias."""
    # Canal V1 — P2 dinamico especial: cualquier tipo de vela
    # Si V1 rompe el techo (mecha o cuerpo, sin importar tipo de vela)
    # y el high es menor que P1, se convierte directamente en nuevo P2.
    # Esto aplica SOLO a V1 — V2-V7 usan su propia logica mas abajo.
    if c["on"] and not c["apagado"] and c.get("p1") and c.get("p2_actual_high") is not None:
        ahora_dt_v1c = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))
        techo_v1c = calcular_techo_canal(simbolo, ahora_dt_v1c)
        if techo_v1c and v_high > techo_v1c and v_high < c["p1"]["high"]:
            p2_ant_v1c = c["p2_actual_high"]
            c["p2_actual_high"] = v_high
            c["p2"]["high"]     = v_high
            c["p2"]["fecha"]    = ahora_dt_v1c.strftime("%Y-%m-%d")
            c["p2"]["hora_est"] = ahora_dt_v1c.hour
            c["p2_actual_ts"]   = ahora_dt_v1c
            guardar_canales()
            print(f"{simbolo} P2 dinamico (V1): ${p2_ant_v1c:.2f} -> ${v_high:.2f} ({ahora_dt_v1c.strftime('%Y-%m-%d')}) silencioso")

def evaluar_pm40_v1(simbolo, ed, c, velas, v_high):
    """AX-015: extraida de evaluar_activo() sin cambiar comportamiento.
    Contiene EXACTAMENTE el bloque de PM40 en la rama V1 (P1 dinamico:
    inicializacion, actualizacion de P1 si rompe, maduracion tras 3 velas
    bajo P1, y fijacion/actualizacion de P2 con invalidacion si P2>=P1).
    NO toca PM40 V2-V7, 4PASOS, Canal V2-V7, 1VR/RPG/GNA/GBA, ni Reset Diario.
    Recibe explicitamente todas las variables necesarias."""
    # PM40 — P1 dinámico en V1
    if not c["on"] and not ed["pm40_fired"]:
        sma20  = calcular_sma(velas, 20)
        sma40  = calcular_sma(velas, 40)
        sma100 = calcular_sma(velas, 100)
        sma200 = calcular_sma(velas, 200)
        smas_ok = sma20 and sma40 and sma100 and sma200 and sma20 > sma40 > sma100 > sma200
        ed["pm40_vela_idx"] = 1
        if smas_ok:
            if not ed["pm40_activo"]:
                ed["pm40_activo"]         = True
                ed["pm40_p1_high"]        = v_high
                ed["pm40_p1_idx"]         = 1
                ed["pm40_p2_high"]        = None
                ed["pm40_p2_idx"]         = None
                ed["pm40_velas_bajo_p1"]  = 0
                ed["pm40_p1_maduro"]      = False
            elif v_high >= ed["pm40_p1_high"]:
                ed["pm40_p1_high"]        = v_high
                ed["pm40_p1_idx"]         = 1
                ed["pm40_p2_high"]        = None
                ed["pm40_p2_idx"]         = None
                ed["pm40_velas_bajo_p1"]  = 0
                ed["pm40_p1_maduro"]      = False
            else:
                ed["pm40_velas_bajo_p1"] += 1
                if ed["pm40_velas_bajo_p1"] >= 3:
                    ed["pm40_p1_maduro"] = True
                if ed["pm40_p2_high"] is not None and v_high > ed["pm40_p2_high"]:
                    ed["pm40_p2_high"] = v_high
                    ed["pm40_p2_idx"]  = ed["pm40_vela_idx"]
                    canal[simbolo]["p2"]["high"]      = v_high
                    canal[simbolo]["p2_actual_high"]  = v_high
                    if ed["pm40_p2_high"] >= ed["pm40_p1_high"]:
                        ed["pm40_activo"] = False; ed["pm40_p1_high"] = None
                        ed["pm40_p1_idx"] = None; ed["pm40_p2_high"] = None
                        ed["pm40_p2_idx"] = None; ed["pm40_velas_bajo_p1"] = 0
                        ed["pm40_p1_maduro"] = False; canal[simbolo]["on"] = False
                        guardar_canales()
                    else:
                        guardar_canales()

def evaluar_pm40_v2_v7(simbolo, ed, c, v_high, v_close, v_alcista, hora_vela):
    """AX-016: extraida de evaluar_activo() sin cambiar comportamiento.
    Contiene EXACTAMENTE el bloque de PM40 en V2-V7: actualizacion de P1
    si rompe, maduracion tras 3 velas bajo P1, fijacion de P2 (distancia>=4),
    comparacion contra techo proyectado (slope), ruptura con alerta CALL
    (vela alcista y hora_vela>9), o actualizacion/invalidacion de P2 si no
    rompe. NO toca PM40 V1, 4PASOS, Canal V2-V7, 1VR/RPG/GNA/GBA, ni Reset Diario.
    Recibe explicitamente todas las variables necesarias."""
    # PM40 — V2-V7
    if not c["on"] and ed["pm40_activo"] and not ed["pm40_fired"] and ed["pm40_p1_high"]:
        ed["pm40_vela_idx"] += 1
        idx_actual = ed["pm40_vela_idx"]

        if v_high >= ed["pm40_p1_high"]:
            ed["pm40_p1_high"]       = v_high
            ed["pm40_p1_idx"]        = idx_actual
            ed["pm40_p2_high"]       = None
            ed["pm40_p2_idx"]        = None
            ed["pm40_velas_bajo_p1"] = 0
            ed["pm40_p1_maduro"]     = False
        else:
            ed["pm40_velas_bajo_p1"] += 1
            if ed["pm40_velas_bajo_p1"] >= 3:
                ed["pm40_p1_maduro"] = True

            if ed["pm40_p1_maduro"]:
                distancia = idx_actual - ed["pm40_p1_idx"]

                if ed["pm40_p2_idx"] is None and distancia >= 4:
                    ed["pm40_p2_high"] = v_high
                    ed["pm40_p2_idx"]  = idx_actual
                    print(f"{simbolo} PM40 P2 fijado: ${v_high:.2f} idx={idx_actual}")

                elif ed["pm40_p2_idx"] is not None:
                    slope      = (ed["pm40_p2_high"] - ed["pm40_p1_high"]) / (ed["pm40_p2_idx"] - ed["pm40_p1_idx"])
                    techo_pm40 = ed["pm40_p1_high"] + slope * (idx_actual - ed["pm40_p1_idx"])

                    if v_high > techo_pm40:
                        if v_alcista and hora_vela > 9:
                            ed["pm40_fired"]  = True
                            guardar_estado_dia()
                            ed["pm40_activo"] = False
                            enviar_senal_con_botones(
                                simbolo, "PM40 — RUPTURA CANAL BAJISTA",
                                f"{hora_vela+1}:00 EST", v_close, "CALL",
                                f"<b>P1:</b> ${ed['pm40_p1_high']:.2f} | <b>P2:</b> ${ed['pm40_p2_high']:.2f}\n"
                                f"<b>Techo:</b> ${techo_pm40:.2f} | <b>High:</b> ${v_high:.2f}\n"
                            )
                        elif v_high < ed["pm40_p1_high"]:
                            ed["pm40_p2_high"] = v_high
                            ed["pm40_p2_idx"]  = idx_actual
                            canal[simbolo]["p2"]["high"]     = v_high
                            canal[simbolo]["p2_actual_high"] = v_high
                            if ed["pm40_p2_high"] >= ed["pm40_p1_high"]:
                                ed["pm40_activo"] = False; ed["pm40_p1_high"] = None
                                canal[simbolo]["on"] = False
                                guardar_canales()
                            else:
                                guardar_canales()
                    elif v_high > ed["pm40_p2_high"]:
                        ed["pm40_p2_high"] = v_high
                        ed["pm40_p2_idx"]  = idx_actual
                        canal[simbolo]["p2"]["high"]     = v_high
                        canal[simbolo]["p2_actual_high"] = v_high
                        if ed["pm40_p2_high"] >= ed["pm40_p1_high"]:
                            ed["pm40_activo"] = False; ed["pm40_p1_high"] = None
                            canal[simbolo]["on"] = False
                            guardar_canales()
                        else:
                            guardar_canales()

def evaluar_4pasos_v1(simbolo, ed, c, vela_actual, v_low, ahora):
    """AX-017: extraida de evaluar_activo() sin cambiar comportamiento.
    Contiene EXACTAMENTE el bloque 4PASOS en la rama V1 (verificacion de
    espera 24h, zona valida P1, inicializacion/actualizacion de p1_low/p2_low
    e historial de lows)."""
    if not (c["on"] and not c["apagado"] and c["p3"] is not None and not ed["4ps_fired"]):
        return

    ultima_senal = ed.get("4ps_ultima_senal")
    _4ps_en_espera = False
    if ultima_senal:
        try:
            from datetime import datetime as _dt2
            ts_ultima = _dt2.fromisoformat(ultima_senal)
            if ts_ultima.tzinfo is None:
                ts_ultima = EST.localize(ts_ultima)
            _4ps_en_espera = (ahora - ts_ultima).total_seconds() < 86400
        except:
            pass

    if not _4ps_en_espera:
        ed["4ps_vela_idx"] = 1
        ahora_dt_4ps_v1 = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))
        techo_v1_4ps, piso_v1_4ps = calcular_techo_canal(simbolo, ahora_dt_4ps_v1), None
        piso_v1_4ps, mitad_v1_4ps = calcular_piso_mitad_canal(simbolo, ahora_dt_4ps_v1)
        zona_p1_valida = False
        if techo_v1_4ps and piso_v1_4ps and mitad_v1_4ps:
            zona_max_p1 = mitad_v1_4ps + (techo_v1_4ps - piso_v1_4ps) * 0.85 / 2
            zona_p1_valida = piso_v1_4ps <= v_low <= zona_max_p1

        if zona_p1_valida:
            if not ed["4ps_activo"]:
                ed["4ps_activo"]         = True
                ed["4ps_p1_low"]         = v_low
                ed["4ps_p1_idx"]         = 1
                ed["4ps_p2_low"]         = None
                ed["4ps_p2_idx"]         = None
                ed["4ps_historial_lows"] = [(1, v_low)]
            elif v_low <= ed["4ps_p1_low"]:
                ed["4ps_p1_low"]         = v_low
                ed["4ps_p1_idx"]         = 1
                ed["4ps_p2_low"]         = None
                ed["4ps_p2_idx"]         = None
                ed["4ps_historial_lows"] = [(1, v_low)]
            else:
                ed.setdefault("4ps_historial_lows", []).append((1, v_low))


def evaluar_4pasos_v2_v7(simbolo, ed, c, vela_actual, v_low, v_close, v_roja, hora_vela):
    """AX-018: extraida de evaluar_activo() sin cambiar comportamiento.
    Contiene EXACTAMENTE el bloque 4PASOS V2-V7 (incremento de idx, historial,
    reset por salida de canal, actualizacion de P1, fijacion/actualizacion de P2,
    y disparo de senal PUT cuando cierre rompe slope)."""
    if not (c["on"] and not c["apagado"] and c["p3"] is not None and ed["4ps_activo"] and not ed["4ps_fired"]):
        return

    ed["4ps_vela_idx"] += 1
    idx_4ps = ed["4ps_vela_idx"]

    ahora_dt_4ps = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))
    techo_4ps    = calcular_techo_canal(simbolo, ahora_dt_4ps)
    piso_4ps, mitad_4ps = calcular_piso_mitad_canal(simbolo, ahora_dt_4ps)

    # Registrar low de esta vela en historial para verificacion slope
    ed.setdefault("4ps_historial_lows", []).append((idx_4ps, v_low))

    # Reset si precio sale del canal RCB
    if techo_4ps and piso_4ps and (v_close > techo_4ps or v_close < piso_4ps):
        ed["4ps_activo"]          = False
        ed["4ps_p1_low"]          = None
        ed["4ps_p1_idx"]          = None
        ed["4ps_p2_low"]          = None
        ed["4ps_p2_idx"]          = None
        ed["4ps_historial_lows"]  = []

    # P1 se mueve si aparece low menor o igual (solo durante formacion - antes de tener P2)
    elif v_low <= ed["4ps_p1_low"] and ed["4ps_p2_idx"] is None:
        ed["4ps_p1_low"]         = v_low
        ed["4ps_p1_idx"]         = idx_4ps
        ed["4ps_p2_low"]         = None
        ed["4ps_p2_idx"]         = None
        ed["4ps_historial_lows"] = [(idx_4ps, v_low)]

    elif ed["4ps_p2_idx"] is None:
        distancia_4ps = idx_4ps - ed["4ps_p1_idx"]
        historial_lows = ed.get("4ps_historial_lows", [])

        proyeccion_rota = False
        if distancia_4ps > 0:
            slope_proyectado = (v_low - ed["4ps_p1_low"]) / distancia_4ps
            for idx_h, low_h in historial_lows:
                if idx_h <= ed["4ps_p1_idx"] or idx_h >= idx_4ps:
                    continue
                proy = ed["4ps_p1_low"] + slope_proyectado * (idx_h - ed["4ps_p1_idx"])
                if low_h < proy:
                    proyeccion_rota = True
                    break

        if proyeccion_rota:
            ed["4ps_p1_low"]         = v_low
            ed["4ps_p1_idx"]         = idx_4ps
            ed["4ps_p2_low"]         = None
            ed["4ps_p2_idx"]         = None
            ed["4ps_historial_lows"] = [(idx_4ps, v_low)]
            print(f"{simbolo} 4PASOS P1 reiniciado por ruptura de proyeccion: ${v_low:.2f} idx={idx_4ps}")
        elif distancia_4ps >= 6:
            if verificar_slope_4ps(ed["4ps_p1_low"], ed["4ps_p1_idx"], v_low, idx_4ps, historial_lows):
                ed["4ps_p2_low"] = v_low
                ed["4ps_p2_idx"] = idx_4ps
                print(f"{simbolo} 4PASOS P2 fijado: ${v_low:.2f} idx={idx_4ps}")

    # Con P2: evaluar ruptura o actualizacion
    elif ed["4ps_p2_idx"] is not None:
            slope_4ps  = (ed["4ps_p2_low"] - ed["4ps_p1_low"]) / (ed["4ps_p2_idx"] - ed["4ps_p1_idx"])
            piso_slope = ed["4ps_p1_low"] + slope_4ps * (idx_4ps - ed["4ps_p1_idx"])
            historial_lows = ed.get("4ps_historial_lows", [])

            # Caso A — LOW (mecha) rompe slope pero CIERRE queda arriba → nuevo P2
            if v_low < piso_slope and v_close >= piso_slope:
                if verificar_slope_4ps(ed["4ps_p1_low"], ed["4ps_p1_idx"], v_low, idx_4ps, historial_lows):
                    ed["4ps_p2_low"] = v_low
                    ed["4ps_p2_idx"] = idx_4ps
                    print(f"{simbolo} 4PASOS P2 actualizado por mecha: ${v_low:.2f} idx={idx_4ps}")

            # Caso B — CIERRE rompe slope → SEÑAL PUT
            elif v_roja and v_close < piso_slope:
                # Determinar label: 🔥 si ruptura ocurre en 50% superior del canal RCB
                label_4ps = "4PASOS"
                extra_fuego = ""
                if techo_4ps and piso_4ps and mitad_4ps:
                    if v_close >= mitad_4ps:
                        label_4ps  = "4PASOS 🔥"
                        extra_fuego = f"<b>Zona:</b> 50% superior del canal — contexto de alta probabilidad\n"
                ed["4ps_fired"]         = True
                ed["4ps_ultima_senal"]  = ahora_dt_4ps.isoformat()
                guardar_estado_dia()
                ed["4ps_activo"]        = False
                enviar_senal_con_botones(
                    simbolo, f"{label_4ps} — RUPTURA SOPORTE ALCISTA",
                    f"{hora_vela+1}:00 EST", v_close, "PUT",
                    f"<b>P1:</b> ${ed['4ps_p1_low']:.2f} | <b>P2:</b> ${ed['4ps_p2_low']:.2f}\n"
                    f"<b>Soporte:</b> ${piso_slope:.2f} | <b>Cierre:</b> ${v_close:.2f}\n"
                    f"{extra_fuego}"
                    f"<b>Techo RCB:</b> ${techo_4ps:.2f}\n"
                )

            # Caso C — LOW mayor que P2 actual → P2 sube (tendencia alcista continua)
            elif v_low > ed["4ps_p2_low"]:
                if verificar_slope_4ps(ed["4ps_p1_low"], ed["4ps_p1_idx"], v_low, idx_4ps, historial_lows):
                    ed["4ps_p2_low"] = v_low
                    ed["4ps_p2_idx"] = idx_4ps


def evaluar_canal_v2_v7(simbolo, ed, c, vela_actual, v_high, v_close, v_alcista, hora_vela):
    """AX-019: extraida de evaluar_activo() sin cambiar comportamiento.
    Contiene EXACTAMENTE el bloque RCB/CNF V2-V7 (P2 dinamico silencioso,
    ruptura con senal CALL, y apagado de canal por HIGH >= P1)."""
    if not (c["on"] and not c["apagado"] and c.get("p1") and c.get("p2_actual_high") is not None):
        return

    ahora_dt_c = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))
    techo      = calcular_techo_canal(simbolo, ahora_dt_c)
    tipo_canal = "RCB" if c["p3"] else "CNF"
    flag_fired = "rcb_fired" if c["p3"] else "cnf_fired"

    if techo:
        # Caso A — vela NO alcista: HIGH supera techo → P2 dinámico silencioso
        if not v_alcista and v_high > techo and v_high < c["p1"]["high"]:
            p2_ant = c["p2_actual_high"]
            c["p2_actual_high"] = v_high
            c["p2"]["high"]     = v_high
            c["p2"]["fecha"]    = ahora_dt_c.strftime("%Y-%m-%d")
            c["p2"]["hora_est"] = ahora_dt_c.hour
            c["p2_actual_ts"]   = ahora_dt_c
            guardar_canales()
            print(f"{simbolo} P2 dinámico: ${p2_ant:.2f} → ${v_high:.2f} ({ahora_dt_c.strftime('%Y-%m-%d')} hora {ahora_dt_c.hour}) silencioso")

        # Caso B — vela alcista estricta: CLOSE supera techo → alerta + canal apagado
        elif v_alcista and v_close > techo and not ed[flag_fired]:
            if v_high < c["p1"]["high"]:
                enviar_senal_con_botones(
                    simbolo,
                    f"{tipo_canal} — RUPTURA CANAL",
                    f"{hora_vela+1}:00 EST",
                    v_close,
                    "CALL",
                    f"<b>Techo:</b> ${techo:.2f} | <b>Cierre:</b> ${v_close:.2f}\n"
                    f"<b>P1:</b> ${c['p1']['high']:.2f} | <b>P2:</b> ${c['p2_actual_high']:.2f}\n"
                )
                c["roto"]          = True
                c["fecha_ruptura"] = ahora_dt_c.strftime("%Y-%m-%d")
                c["apagado"]       = True
                ed[flag_fired]     = True
                guardar_canales()
                guardar_estado_dia()
                print(f"{simbolo} {tipo_canal} ROTO — canal desactivado, queda en chart hasta {ahora_dt_c.strftime('%Y-%m-%d')}")
            else:
                c["apagado"] = True
                guardar_canales()
                enviar_telegram(
                    f"🔕 <b>Canal APAGADO — {simbolo}</b>\n"
                    f"High ${v_high:.2f} >= P1 ${c['p1']['high']:.2f}"
                )

        # Caso C — HIGH >= P1 en cualquier vela → canal apagado
        elif v_high >= c["p1"]["high"]:
            c["apagado"] = True
            guardar_canales()
            enviar_telegram(
                f"🔕 <b>Canal APAGADO — {simbolo}</b>\n"
                f"High ${v_high:.2f} >= P1 ${c['p1']['high']:.2f}"
            )


def evaluar_activo(simbolo, velas, ahora):
    ed = estado_dia[simbolo]
    c  = canal[simbolo]

    ctx = preparar_contexto_vela(simbolo, velas, ahora)
    if ctx is None:
        return

    hora        = ctx["hora"]
    vela_actual = ctx["vela_actual"]
    v_open      = ctx["v_open"]
    v_close     = ctx["v_close"]
    v_high      = ctx["v_high"]
    v_low       = ctx["v_low"]
    fecha_hoy   = ctx["fecha_hoy"]

    # Reset diario si es nueva fecha
    ed, c = reset_diario_si_aplica(simbolo, velas, fecha_hoy, ed, c, hora)

    # Vela alcista estricta AXIS
    cuerpo    = v_close - v_open
    mecha_sup = v_high - max(v_close, v_open)
    rango     = v_high - v_low
    v_alcista = (
        v_close > v_open and
        (cuerpo / rango >= 0.15 if rango > 0 else False) and
        (mecha_sup / cuerpo <= 0.75 if cuerpo > 0 else False)
    )
    v_roja    = v_close < v_open
    v7_ayer   = ed["v7_ayer_close"]
    hora_vela = hora - 1

    # ── VELA 1 ──
    if hora_vela == 9:
        ed["v1_close"] = v_close
        ed["v1_open"]  = v_open
        ed["v1_low"]   = v_low

        # 1VR
        evaluar_1vr_normal(simbolo, ed, velas, vela_actual, v_open, v_close, v_roja)

        # RPG
        evaluar_rpg_activacion(simbolo, ed, velas, v_open, v_close, v_low, v7_ayer)

        # GNA
        evaluar_gna(simbolo, ed, velas, v_open, v_close, v_alcista, v7_ayer, None, hora_vela, True)

        # GBA
        evaluar_gba(simbolo, ed, v_open, v_close, v_alcista, v7_ayer, None, hora_vela, True)

        # Canal V1
        evaluar_canal_v1(simbolo, c, vela_actual, v_high)

        # PM40
        evaluar_pm40_v1(simbolo, ed, c, velas, v_high)

        # 4PASOS en V1
        evaluar_4pasos_v1(simbolo, ed, c, vela_actual, v_low, ahora)

        return

    # ── VELAS 2-7 ──
    v1_close = ed["v1_close"]

        # RPG
    evaluar_rpg_disparo(simbolo, ed, vela_actual, v_close, hora_vela)

    # GNA
    evaluar_gna(simbolo, ed, velas, v_open, v_close, v_alcista, v7_ayer, v1_close, hora_vela, False)

    # GBA
    evaluar_gba(simbolo, ed, v_open, v_close, v_alcista, v7_ayer, v1_close, hora_vela, False)

    # RCB/CNF — P2 dinámico + ruptura
    evaluar_canal_v2_v7(simbolo, ed, c, vela_actual, v_high, v_close, v_alcista, hora_vela)

    # PM40
    evaluar_pm40_v2_v7(simbolo, ed, c, v_high, v_close, v_alcista, hora_vela)

    # 4PASOS — V2-V7
    evaluar_4pasos_v2_v7(simbolo, ed, c, vela_actual, v_low, v_close, v_roja, hora_vela)

    print(f"{simbolo} V{hora_vela-8} {hora_vela+1}:00 — O:{v_open:.2f} C:{v_close:.2f} | RPG:{ed['rpg_activo']} GNA:{ed['gna_activo']} GBA:{ed['gba_activo']} PM40:{ed['pm40_activo']} 4PS:{ed['4ps_activo']}")


# ═══════════════════════════════════════════════════════════
# TRADIER — AX-004: get_precio_tradier, get_pct_otm, get_opcion_tradier
# y ejecutar_orden_tradier movidas a axis_tradier.py.
# Mismos nombres, mismo comportamiento, mismas URLs/payloads.
# ═══════════════════════════════════════════════════════════
from axis_tradier import (
    get_precio_tradier,
    get_pct_otm,
    get_opcion_tradier,
    ejecutar_orden_tradier,
)

# ═══════════════════════════════════════════════════════════
# TELEGRAM — ENVIAR MENSAJE CON BOTONES
# ═══════════════════════════════════════════════════════════
def botones_orden_actuales(orden_id):
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    derby = _portfolio["derby"]
    derby_activo = derby["activo"]
    caballo_disponible = None
    caballo_nombre = None
    if derby_activo:
        turno = derby.get("turno_actual", 1)
        caballos = derby["caballos"]
        orden = list(range(turno - 1, 4)) + list(range(0, turno - 1))
        for idx in orden:
            c = caballos[idx]
            if not c.get("eliminado") and c["posicion"] is None:
                caballo_disponible = c["id"]
                caballo_nombre = c["nombre"]
                break
    botones = [
        {"text": "✅ x1",     "callback_data": f"exec_c:{orden_id}:1"},
        {"text": "📦 x2-10", "callback_data": f"exec_multi:{orden_id}"},
    ]
    if derby_activo and caballo_disponible:
        botones.insert(2, {"text": "🏇 DERBY", "callback_data": f"reto:{orden_id}:{caballo_disponible}"})
    return botones


def enviar_telegram_botones(mensaje, orden_id):
    botones = botones_orden_actuales(orden_id)
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       mensaje,
        "parse_mode": "HTML",
        "reply_markup": {"inline_keyboard": [botones]}
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        result = r.json()
        if result.get("ok"):
            msg = result.get("result", {})
            return msg.get("message_id"), msg.get("chat", {}).get("id")
    except Exception as e:
        print(f"Error Telegram botones: {e}")
    return None, None

# ═══════════════════════════════════════════════════════════
# PREPARAR Y ENVIAR SEÑAL CON BOTONES
# ═══════════════════════════════════════════════════════════
def registrar_senal_disparada(simbolo, estrategia, hora_label=None):
    ed = estado_dia.get(simbolo)
    if ed is None:
        return
    if "señales_disparadas" not in ed:
        ed["señales_disparadas"] = []
    if estrategia not in ed["señales_disparadas"]:
        ed["señales_disparadas"].append(estrategia)
    if "señales_detalle" not in ed:
        ed["señales_detalle"] = []
    s = estrategia.upper()
    tipo_corto = None
    if "1VR"    in s: ed["vr1_fired"]  = True; tipo_corto = "1VR"
    if "RPG"    in s: ed["rpg_fired"]  = True; tipo_corto = "RPG"
    if "GNA"    in s: ed["gna_fired"]  = True; tipo_corto = "GNA"
    if "GBA"    in s: ed["gba_fired"]  = True; tipo_corto = "GBA"
    if "PM40"   in s: ed["pm40_fired"] = True; tipo_corto = "PM40"
    if "4PS"    in s or "4PASOS" in s: ed["4ps_fired"] = True; tipo_corto = "4PS"
    if "HED"    in s: ed["hed_fired"]  = True; tipo_corto = "HED"
    if "CNF"    in s: ed["cnf_fired"]  = True; tipo_corto = "CNF"
    if "RCB"    in s: ed["rcb_fired"]  = True; tipo_corto = "RCB"
    if tipo_corto and hora_label:
        try:
            hora_num = int(hora_label.split(":")[0])
            mapa_vela = {10:"V1",11:"V2",12:"V3",13:"V4",14:"V5",15:"V6",16:"V7"}
            vela_calc = mapa_vela.get(hora_num)
        except Exception:
            vela_calc = None
        entry = {"tipo": tipo_corto, "vela": vela_calc, "hora": hora_label}
        if _v7_eval_origen:
            entry["origen"] = _v7_eval_origen
        ed["señales_detalle"].append(entry)
    guardar_estado_dia()

def enviar_senal_con_botones(simbolo, estrategia, hora_label, precio_vela, tipo_opcion, extra=""):
    alert_id = crear_alerta(
        simbolo, estrategia, tipo_opcion, precio_vela,
        hora_label=hora_label, origen=_v7_eval_origen or "ESTRATEGIA",
    )
    registrar_senal_disparada(simbolo, estrategia, hora_label=hora_label)
    try:
        precio = get_precio_tradier(simbolo)
        if not precio:
            print(f"{simbolo}: precio Tradier no disponible — usando precio vela ${precio_vela:.2f}")
            precio = precio_vela
    except Exception as e:
        print(f"{simbolo}: error obteniendo precio Tradier: {e}")
        precio = precio_vela

    try:
        opcion = get_opcion_tradier(simbolo, tipo_opcion.lower(), precio)
    except Exception as e:
        print(f"{simbolo}: error obteniendo opcion Tradier: {e}")
        opcion = None

    import uuid
    orden_id = str(uuid.uuid4())[:8]
    emoji = '🔴' if tipo_opcion == 'PUT' else '🟢'
    actualizar_alerta(alert_id, evento="MARKET_DATA_RESOLVED",
                      precio_subyacente=precio, orden_id=orden_id)

    if opcion:
        opcion["subyacente"] = simbolo
        msg = (
            f"{emoji} <b>{estrategia}</b>\n"
            f"<b>Activo:</b> {simbolo}\n"
            f"<b>Hora:</b> {hora_label}\n"
            f"<b>Alert ID:</b> {alert_id}\n"
            f"<b>Precio:</b> ${precio:.2f}\n"
            f"{extra}"
            f"<b>Opcion:</b> {opcion['tipo']} ${opcion['strike']:.0f} exp {opcion['expiration']}\n"
            f"<b>Ask:</b> ${opcion['ask']:.2f} | <b>Bid:</b> ${opcion['bid']:.2f}\n"
            f"⚠️ <b>{tipo_opcion} — ¿Ejecutar?</b> (expira en {ORDEN_TIMEOUT_MIN} min)"
        )
        message_id, chat_id = enviar_telegram_botones(msg, orden_id)
        if message_id is not None:
            actualizar_alerta(alert_id, "NOTIFIED", "TELEGRAM_SENT",
                              telegram_message_id=message_id, telegram_chat_id=chat_id,
                              option_symbol=opcion.get("symbol"), strike=opcion.get("strike"),
                              expiration=opcion.get("expiration"), ask=opcion.get("ask"),
                              bid=opcion.get("bid"))
            ordenes_pendientes[orden_id] = {
                "alert_id":        alert_id,
                "opcion":          opcion,
                "estrategia":      estrategia,
                "ts":              datetime.now(pytz.utc),
                "message_id":      message_id,
                "chat_id":         chat_id,
                "texto_original":  msg,
            }
            guardar_ordenes()
        else:
            actualizar_alerta(alert_id, "CANCELLED", "TELEGRAM_SEND_FAILED",
                              motivo_cancelacion="telegram_send_failed")
        if message_id is not None:
            print(f"{simbolo}: señal enviada con botones — {estrategia} | opcion {opcion['tipo']} ${opcion['strike']:.0f}")
        else:
            print(f"{simbolo}: fallo enviando señal a Telegram — {estrategia}")
    else:
        enviar_telegram(
            f"{emoji} <b>{estrategia}</b>\n"
            f"<b>Activo:</b> {simbolo}\n"
            f"<b>Hora:</b> {hora_label}\n"
            f"<b>Alert ID:</b> {alert_id}\n"
            f"<b>Precio:</b> ${precio:.2f}\n"
            f"{extra}"
            f"⚠️ <b>{tipo_opcion} — Tradier sin datos, evaluar manualmente</b>"
        )
        actualizar_alerta(alert_id, "NOTIFIED", "MANUAL_REVIEW_NOTIFIED",
                          motivo="tradier_sin_opcion")
        actualizar_alerta(alert_id, "CANCELLED", "NO_OPTION_AVAILABLE",
                          decision="MANUAL", motivo_cancelacion="tradier_sin_opcion")
        print(f"{simbolo}: señal enviada SIN botones — Tradier no disponible")

# ═══════════════════════════════════════════════════════════
# REPORTE HORARIO
# ═══════════════════════════════════════════════════════════
def reporte_horario():
    ahora = datetime.now(EST)
    print(f"\n{'='*50}\nReporte horario {ahora.strftime('%H:%M EST')} — evaluando {len(ACTIVOS)} activos\n{'='*50}")
    for simbolo in ACTIVOS:
        try:
            velas = get_velas(simbolo, outputsize=50)
            if velas:
                print(f"Datos: Tradier 15min ✅")
                evaluar_activo(simbolo, velas, ahora)
            else:
                print(f"Tradier sin datos {simbolo} — reintentando en 2 min...")
                time.sleep(120)
                velas = get_velas(simbolo, outputsize=50)
                if velas:
                    print(f"Datos: Tradier 15min ✅ (reintento)")
                    evaluar_activo(simbolo, velas, ahora)
                else:
                    print(f"{simbolo}: sin datos tras reintento — omitiendo evaluación")
                    enviar_telegram(
                        f"⚠️ <b>AXIS — Sin datos Tradier</b>\n"
                        f"<b>Activo:</b> {simbolo}\n"
                        f"<b>Hora:</b> {ahora.strftime('%H:%M EST')}\n"
                        f"Evaluación omitida. Revisar manualmente."
                    )
            time.sleep(2)
        except Exception as e:
            print(f"Error evaluando {simbolo}: {e}")

# ═══════════════════════════════════════════════════════════
# LOOP PRINCIPAL
# ═══════════════════════════════════════════════════════════
def monitor_loop():
    print(f"AXIS Breakout Sentinel v{AXIS_VERSION} iniciado...")
    while True:
        ahora = datetime.now(EST)
        mins  = ahora.hour * 60 + ahora.minute
        en_horario = es_dia_mercado(ahora) and 570 <= mins <= 990
        if not en_horario:
            time.sleep(300)
            continue
        minutos_hasta_01 = (1 - ahora.minute) % 60
        if minutos_hasta_01 == 0:
            minutos_hasta_01 = 60
        segundos_espera = minutos_hasta_01 * 60 - ahora.second
        print(f"Proximo chequeo en {minutos_hasta_01} min | {ahora.strftime('%A %H:%M EST')}")
        time.sleep(segundos_espera)
        ahora = datetime.now(EST)
        if es_dia_mercado(ahora) and ahora.hour in HORAS_REPORTE:
            reporte_horario()
        else:
            print(f"No toca reporte: {ahora.strftime('%A %H:%M EST')}")

# ═══════════════════════════════════════════════════════════
# RUTAS FLASK
# ═══════════════════════════════════════════════════════════
@app.route("/", methods=["GET"])
@app.route("/", defaults={"path": ""}, methods=["GET"])
def home(path=""):
    ahora   = datetime.now(EST)
    # ── v8.63 FIX: verificar horario además de día hábil ──
    mercado = es_dia_mercado(ahora) and (570 <= ahora.hour * 60 + ahora.minute < 960)
    pos_count = len(_portfolio["posiciones"]) if _portfolio else 0
    activos_str = " | ".join(ACTIVOS)
    canales_html = ""
    for a in ACTIVOS:
        c = canal[a]
        tipo  = "RCB" if (c["on"] and c["p3"]) else "CNF" if c["on"] else "—"
        color = "#00e676" if c["on"] and not c["apagado"] else "#666688"
        canales_html += f'<div class="canal-item"><span style="color:{color}">●</span> {a} <span style="color:#666688">{tipo}</span></div>'
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AXIS Trading System</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Space+Grotesk:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0a0a0f; color: #e8e8f0; font-family: 'Space Grotesk', sans-serif;
         min-height: 100vh; display: flex; flex-direction: column; align-items: center;
         justify-content: center; padding: 24px; }}
  .logo {{ font-family: 'JetBrains Mono', monospace; font-size: 48px; font-weight: 700;
           letter-spacing: -2px; margin-bottom: 6px; }}
  .logo span {{ color: #4fc3f7; }}
  .tagline {{ color: #666688; font-size: 14px; margin-bottom: 40px; letter-spacing: 2px;
              text-transform: uppercase; }}
  .status-bar {{ display: flex; gap: 20px; margin-bottom: 40px; flex-wrap: wrap;
                 justify-content: center; }}
  .status-pill {{ background: #111118; border: 1px solid #2a2a3a; border-radius: 20px;
                  padding: 6px 16px; font-family: 'JetBrains Mono', monospace;
                  font-size: 12px; }}
  .mercado-on  {{ border-color: #00e676; color: #00e676; }}
  .mercado-off {{ border-color: #666688; color: #666688; }}
  .nav-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
               width: 100%; max-width: 700px; margin-bottom: 40px; }}
  .nav-card {{ background: #111118; border: 1px solid #2a2a3a; border-radius: 16px;
               padding: 28px; text-decoration: none; color: #e8e8f0;
               transition: all 0.2s; text-align: center; }}
  .nav-card:hover {{ border-color: #4fc3f7; transform: translateY(-2px); }}
  .nav-card .icon {{ font-size: 36px; margin-bottom: 12px; }}
  .nav-card .title {{ font-size: 18px; font-weight: 700; margin-bottom: 4px; }}
  .nav-card .desc {{ font-size: 12px; color: #666688; }}
  .nav-card.portfolio {{ border-color: #3d3000; }}
  .nav-card.portfolio:hover {{ border-color: #ffd700; }}
  .canales-grid {{ display: flex; flex-wrap: wrap; gap: 12px; justify-content: center;
                   max-width: 560px; }}
  .canal-item {{ background: #111118; border: 1px solid #2a2a3a; border-radius: 8px;
                 padding: 6px 14px; font-family: 'JetBrains Mono', monospace; font-size: 12px; }}
  .footer {{ margin-top: 40px; font-size: 11px; color: #444; font-family: 'JetBrains Mono', monospace; }}
  .badge {{ background: #1a1a24; border: 1px solid #2a2a3a; border-radius: 12px;
            padding: 2px 10px; font-size: 11px; color: #666688; margin-left: 6px; }}
  @media (max-width: 480px) {{ .nav-grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
  <div class="logo">AX<span>IS</span></div>
  <div class="tagline">Automated Options Trading System</div>
  <div class="status-bar">
    <div class="status-pill {'mercado-on' if mercado else 'mercado-off'}">
      {'● MERCADO ABIERTO' if mercado else '○ MERCADO CERRADO'}
    </div>
    <div class="status-pill">{ahora.strftime('%H:%M EST')}</div>
    <div class="status-pill">{pos_count} posición{'es' if pos_count != 1 else ''} abierta{'s' if pos_count != 1 else ''}</div>
    <div class="status-pill">v{AXIS_VERSION} · {len(ACTIVOS)} activos</div>
  </div>
  <div class="nav-grid">
    <a href="/charts" class="nav-card">
      <div class="icon">📊</div>
      <div class="title">AXIS Charts</div>
      <div class="desc">Gráficas · Señales · Canales · SMAs</div>
    </a>
    <a href="/portfolio" class="nav-card portfolio">
      <div class="icon">🏆</div>
      <div class="title">Portfolio</div>
      <div class="desc">Posiciones · Reto Millonario · P&L</div>
    </a>
    <a href="/analisis" class="nav-card" style="border-color:#1a3a2a;">
      <div class="icon">📈</div>
      <div class="title">Análisis</div>
      <div class="desc">Historial · Win Rate · Comportamiento</div>
    </a>
    <a href="/bitacora" class="nav-card bitacora">
      <div class="icon">📋</div>
      <div class="title">Bitácora</div>
      <div class="desc">Pendientes · Decisiones · Seguimiento</div>
    </a>
    <a href="/daily_debrief" class="nav-card" style="border-color:#0d1a3a; grid-column: 1 / -1;">
      <div class="icon">🎯</div>
      <div class="title">Daily Debrief</div>
      <div class="desc">Hoy revisa primero &nbsp;•&nbsp; Señales del día &nbsp;•&nbsp; Root Cause</div>
    </a>
    <a href="/journal" class="nav-card" style="border-color:#1a1a3a;">
      <div class="icon">📓</div>
      <div class="title">Signal Journal</div>
      <div class="desc">Revisar &nbsp;•&nbsp; Calificar &nbsp;•&nbsp; Decidir</div>
    </a>
    <a href="/success_rate" class="nav-card" style="border-color:#0d2a1a;">
      <div class="icon">✅</div>
      <div class="title">Success Rate</div>
      <div class="desc">Resultados históricos de revisiones</div>
    </a>
    <a href="/derby" class="nav-card" style="border-color:#3d0000; grid-column: 1 / -1;">
      <div class="icon">🏇</div>
      <div class="title">REAL LAZARO-PALMA</div>
      <div class="desc">Noel · Paula · Noel Andrés · Emilia — Derby de Opciones</div>
    </a>
  </div>
  <div class="canales-grid">
    {canales_html}
  </div>
  <div class="footer"><a href="/version" style="color:inherit;text-decoration:none">AXIS v{AXIS_VERSION}</a> · {activos_str}</div>
</body>
</html>"""
    from flask import Response
    return Response(html, mimetype="text/html")

@app.route("/test", methods=["POST"])
@require_admin
def test():
    ahora = datetime.now(EST)
    lineas_canal = []
    for a in ACTIVOS:
        c = canal[a]
        if c["on"] and not c["apagado"]:
            tipo = "RCB" if c["p3"] else "CNF"
            lineas_canal.append(f"  {a}: {tipo} — P1 ${c['p1']['high']:.2f} | P2 ${c['p2_actual_high']:.2f}")
        elif c["apagado"]:
            lineas_canal.append(f"  {a}: APAGADO")
        else:
            lineas_canal.append(f"  {a}: OFF")
    enviar_telegram(
        f"✅ <b>AXIS Breakout Sentinel v{AXIS_VERSION}</b>\n"
        f"<b>Hora:</b> {ahora.strftime('%A %d/%m/%Y %H:%M EST')}\n"
        f"<b>Mercado:</b> {'Abierto' if es_dia_mercado(ahora) else 'Cerrado'}\n"
        f"<b>1VR:</b> {'ON' if VR1_ON else 'OFF'} | "
        f"<b>RPG:</b> {'ON' if RPG_ON else 'OFF'} | "
        f"<b>GNA:</b> {'ON' if GNA_ON else 'OFF'} | "
        f"<b>GBA:</b> {'ON' if GBA_ON else 'OFF'}\n"
        f"<b>Canales:</b>\n" + "\n".join(lineas_canal)
    )
    return jsonify({"status": "ok"}), 200

@app.route("/reporte", methods=["POST"])
@require_admin
def reporte_manual():
    reporte_horario()
    return jsonify({"status": "reporte enviado"}), 200

@app.route("/activar", methods=["POST"])
@require_admin
def activar():
    simbolo = request.args.get("activo", "SPY").upper()
    if simbolo not in ACTIVOS:
        return jsonify({"error": f"Activo {simbolo} no reconocido. Opciones: {ACTIVOS}"}), 400
    try:
        p1_high = float(request.args["p1_high"])
        p2_high = float(request.args["p2_high"])
        canal[simbolo]["p1"] = {
            "fecha":    request.args["p1_fecha"],
            "hora_est": int(request.args["p1_hora"]),
            "high":     p1_high,
        }
        canal[simbolo]["p2"] = {
            "fecha":    request.args["p2_fecha"],
            "hora_est": int(request.args["p2_hora"]),
            "high":     p2_high,
        }
        canal[simbolo]["p2_actual_high"] = p2_high
        canal[simbolo]["p2_actual_ts"]   = ts_a_datetime(request.args["p2_fecha"], int(request.args["p2_hora"]))
        if "piso_low" in request.args and float(request.args["piso_low"]) > 0:
            canal[simbolo]["p3"] = {
                "fecha":    request.args["piso_fecha"],
                "hora_est": int(request.args["piso_hora"]),
                "low":      float(request.args["piso_low"]),
            }
        else:
            canal[simbolo]["p3"] = None
        canal[simbolo]["on"]           = True
        canal[simbolo]["apagado"]      = False
        canal[simbolo]["v1_candidato"] = None
        guardar_canales()

        ahora_dt = datetime.now(EST)
        techo = calcular_techo_canal(simbolo, ahora_dt)
        piso, mitad = calcular_piso_mitad_canal(simbolo, ahora_dt)
        tipo_canal = "RCB" if canal[simbolo]["p3"] else "CNF"

        enviar_telegram(
            f"✅ <b>Canal {tipo_canal} Activado — {simbolo}</b>\n"
            f"<b>P1:</b> ${p1_high:.2f} — {request.args['p1_fecha']}\n"
            f"<b>P2:</b> ${p2_high:.2f} — {request.args['p2_fecha']}\n" +
            (f"<b>P3 Piso:</b> ${canal[simbolo]['p3']['low']:.2f}\n" if canal[simbolo]["p3"] else "<b>Tipo:</b> CNF — sin piso\n") +
            (f"<b>Techo ahora:</b> ${techo:.2f}\n" if techo else "") +
            (f"<b>Mitad:</b> ${mitad:.2f} | <b>Piso:</b> ${piso:.2f}" if piso else "")
        )
        return jsonify({"status": f"canal {tipo_canal} activado", "activo": simbolo}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/actualizar_p2", methods=["POST"])
@require_admin
def actualizar_p2():
    simbolo = request.args.get("activo", "SPY").upper()
    if simbolo not in ACTIVOS:
        return jsonify({"error": f"Activo {simbolo} no reconocido"}), 400
    c = canal[simbolo]
    if not c.get("p1"):
        return jsonify({"error": f"{simbolo} no tiene P1 definido — usa /activar primero"}), 400
    try:
        p2_high = float(request.args["p2_high"])
        p2_fecha = request.args["p2_fecha"]
        p2_hora  = int(request.args["p2_hora"])

        if p2_high >= c["p1"]["high"]:
            return jsonify({"error": f"P2 ${p2_high} debe ser menor que P1 ${c['p1']['high']:.2f}"}), 400

        c["p2"] = {
            "fecha":    p2_fecha,
            "hora_est": p2_hora,
            "high":     p2_high,
        }
        c["p2_actual_high"] = p2_high
        c["p2_actual_ts"]   = ts_a_datetime(p2_fecha, p2_hora)
        c["on"]             = True
        c["apagado"]        = False
        guardar_canales()

        ahora_dt   = datetime.now(EST)
        techo      = calcular_techo_canal(simbolo, ahora_dt)
        tipo_canal = "RCB" if c["p3"] else "CNF"

        enviar_telegram(
            f"🔄 <b>P2 Actualizado — {simbolo} {tipo_canal}</b>\n"
            f"<b>P1:</b> ${c['p1']['high']:.2f} — {c['p1']['fecha']} (intacto)\n"
            f"<b>P2 nuevo:</b> ${p2_high:.2f} — {p2_fecha} V{p2_hora}\n" +
            (f"<b>Techo ahora:</b> ${techo:.2f}" if techo else "")
        )
        return jsonify({
            "status":  "P2 actualizado",
            "activo":  simbolo,
            "p1":      c["p1"],
            "p2_nuevo": c["p2"],
            "techo":   round(techo, 2) if techo else None,
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/desactivar", methods=["POST"])
@require_admin
def desactivar():
    simbolo = request.args.get("activo", "SPY").upper()
    if simbolo not in ACTIVOS:
        return jsonify({"error": f"Activo {simbolo} no reconocido"}), 400
    canal[simbolo] = canal_vacio()
    guardar_canales()
    enviar_telegram(f"🔕 <b>Canal desactivado manualmente — {simbolo}</b>")
    return jsonify({"status": "canal desactivado", "activo": simbolo}), 200

@app.route("/apagar", methods=["POST"])
@require_admin
def apagar():
    global SISTEMA_ACTIVO
    SISTEMA_ACTIVO = False
    enviar_telegram("🏁 <b>Sistema apagado manualmente.</b>")
    return jsonify({"status": "apagado"}), 200

@app.route("/estrategia", methods=["POST"])
@require_admin
def estrategia():
    global VR1_ON, RPG_ON, GNA_ON, GBA_ON
    if "vr1" in request.args: VR1_ON = request.args["vr1"].lower() == "true"
    if "rpg" in request.args: RPG_ON = request.args["rpg"].lower() == "true"
    if "gna" in request.args: GNA_ON = request.args["gna"].lower() == "true"
    if "gba" in request.args: GBA_ON = request.args["gba"].lower() == "true"
    enviar_telegram(
        f"⚙️ <b>Estrategias actualizadas</b>\n"
        f"1VR: {'ON' if VR1_ON else 'OFF'} | RPG: {'ON' if RPG_ON else 'OFF'}\n"
        f"GNA: {'ON' if GNA_ON else 'OFF'} | GBA: {'ON' if GBA_ON else 'OFF'}"
    )
    return jsonify({"VR1": VR1_ON, "RPG": RPG_ON, "GNA": GNA_ON, "GBA": GBA_ON}), 200

@app.route("/tradier_test", methods=["POST"])
@require_admin
def tradier_test():
    resultados = {}
    try:
        r = requests.get(f"{TRADIER_BASE}/markets/quotes", headers=TRADIER_HEADERS, params={"symbols": "SPY"}, timeout=10)
        resultados["precio_status"] = r.status_code
        resultados["precio_response"] = r.text[:200]
        if r.status_code == 200:
            data = r.json()
            precio = data.get("quotes", {}).get("quote", {}).get("last")
            resultados["SPY_precio"] = precio
    except Exception as e:
        resultados["precio_error"] = str(e)
    try:
        r2 = requests.get(f"{TRADIER_BASE}/markets/options/expirations", headers=TRADIER_HEADERS, params={"symbol": "SPY"}, timeout=10)
        resultados["vencimientos_status"] = r2.status_code
        resultados["vencimientos_response"] = r2.text[:200]
    except Exception as e:
        resultados["vencimientos_error"] = str(e)
    try:
        r3 = requests.get(f"{TRADIER_BASE}/accounts/{TRADIER_ACCOUNT}/balances", headers=TRADIER_HEADERS, timeout=10)
        resultados["cuenta_status"] = r3.status_code
        resultados["cuenta_response"] = r3.text[:200]
    except Exception as e:
        resultados["cuenta_error"] = str(e)
    msg = (
        f"🔧 <b>Tradier Test</b>\n"
        f"<b>Token:</b> {'OK' if resultados.get('precio_status') == 200 else 'ERROR'}\n"
        f"<b>Precio SPY:</b> {resultados.get('SPY_precio', 'N/A')}\n"
        f"<b>Status precio:</b> {resultados.get('precio_status', 'N/A')}\n"
        f"<b>Status vencimientos:</b> {resultados.get('vencimientos_status', 'N/A')}\n"
        f"<b>Status cuenta:</b> {resultados.get('cuenta_status', 'N/A')}"
    )
    enviar_telegram(msg)
    return jsonify(resultados), 200

# ═══════════════════════════════════════════════════════════
# RETO MILLONARIO — HELPERS
# ═══════════════════════════════════════════════════════════
def buscar_opcion_reto(opcion_original, presupuesto):
    try:
        from datetime import date
        simbolo     = opcion_original["subyacente"]
        tipo        = opcion_original["tipo"].lower()
        strike_orig = float(opcion_original["strike"])
        vencimiento = opcion_original["expiration"]
        precio_max  = presupuesto / 100

        hoy = date.today()
        if (date.fromisoformat(vencimiento) - hoy).days < 7:
            r0 = requests.get(f"{TRADIER_BASE}/markets/options/expirations", headers=TRADIER_HEADERS,
                              params={"symbol": simbolo, "includeAllRoots": "true"}, timeout=10)
            fechas = r0.json().get("expirations", {}).get("date", [])
            if isinstance(fechas, str): fechas = [fechas]
            vencimiento = None
            for f in sorted(fechas):
                if (date.fromisoformat(f) - hoy).days >= 7:
                    vencimiento = f
                    break
            if not vencimiento:
                return None

        r = requests.get(f"{TRADIER_BASE}/markets/options/chains", headers=TRADIER_HEADERS,
                         params={"symbol": simbolo, "expiration": vencimiento, "greeks": "false"}, timeout=10)
        opciones = r.json().get("options", {}).get("option", [])
        if not opciones:
            return None

        candidatas = []
        for o in opciones:
            if o.get("option_type") != tipo: continue
            strike = float(o.get("strike", 0))
            ask    = float(o.get("ask", 0))
            if ask <= 0 or abs(strike - strike_orig) > 5: continue
            if ask <= precio_max:
                candidatas.append(o)

        if not candidatas:
            return None

        mejor = min(candidatas, key=lambda o: abs(float(o.get("strike", 0)) - strike_orig))
        return {
            "symbol":     mejor.get("symbol"),
            "strike":     float(mejor.get("strike", 0)),
            "expiration": vencimiento,
            "tipo":       tipo.upper(),
            "ask":        float(mejor.get("ask", 0)),
            "bid":        float(mejor.get("bid", 0)),
            "subyacente": simbolo,
        }
    except Exception as e:
        print(f"Error buscar_opcion_reto: {e}")
        return None

# AX-004: ejecutar_orden_tradier_contratos movida a axis_tradier.py.
from axis_tradier import ejecutar_orden_tradier_contratos

def recomendar_opcion_claude(opcion_original, capital_carril, presupuesto):
    if not ANTHROPIC_API_KEY:
        return "API key Anthropic no configurada."
    try:
        prompt = (
            f"Eres el analista del sistema AXIS de trading de opciones.\n"
            f"El Reto Millonario tiene un carril con capital ${capital_carril:.2f} "
            f"(presupuesto disponible ${presupuesto:.2f} = 80%).\n"
            f"La señal original recomienda: {opcion_original['tipo']} {opcion_original['subyacente']} "
            f"strike ${opcion_original['strike']:.0f} exp {opcion_original['expiration']} "
            f"ask ${opcion_original['ask']:.2f} (costo ${opcion_original['ask']*100:.2f}).\n"
            f"No hay opciones disponibles en ±5 strikes que quepan en el presupuesto.\n"
            f"Da una recomendación concreta en máximo 3 líneas: qué hacer con este carril. Sin markdown, en español."
        )
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-5", "max_tokens": 150, "messages": [{"role": "user", "content": prompt}]},
            timeout=15
        )
        data = r.json()
        if r.status_code == 200:
            return data["content"][0]["text"]
        return "No se pudo obtener recomendación de Claude."
    except Exception as e:
        return f"Error Claude: {str(e)}"

@app.route("/portfolio/reset", methods=["POST"])
@require_admin
def portfolio_reset():
    global _portfolio
    _portfolio = portfolio_vacio()
    guardar_portfolio()
    enviar_telegram("🔄 <b>Portfolio reseteado</b> — todas las posiciones eliminadas")
    return jsonify({"ok": True, "mensaje": "Portfolio reseteado a cero"}), 200

@app.route("/portfolio", methods=["GET"])
def serve_portfolio():
    from flask import Response
    html_path = os.path.join(os.path.dirname(__file__), "axis_portfolio.html")
    if os.path.exists(html_path):
        with open(html_path, "r") as f:
            return Response(f.read(), mimetype="text/html")
    return Response("<h1>axis_portfolio.html no encontrado</h1>", mimetype="text/html"), 404

@app.route("/portfolio/data", methods=["GET"])
@require_admin
def portfolio_data():
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    return jsonify({
        "posiciones": _portfolio["posiciones"],
        "historial":  _portfolio["historial"][-20:],
        "derby":      _portfolio.get("derby", {}),
        "reto":       _portfolio.get("derby", {}),  # compatibilidad
    }), 200


@app.route("/portfolio/reconciliar_ejecuciones", methods=["POST"])
@require_admin
def portfolio_reconciliar_ejecuciones():
    """Dry-run por defecto; confirmar=true anula solo registros sin prueba Tradier."""
    payload = request.get_json(silent=True) or {}
    confirmar = payload.get("confirmar") is True
    return jsonify(reconciliar_posiciones_sin_confirmacion(confirmar=confirmar)), 200

@app.route("/portfolio/cerrar", methods=["POST"])
@require_admin
def portfolio_cerrar():
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    pos_id = request.args.get("id") or (request.get_json(silent=True) or {}).get("id")
    motivo = request.args.get("motivo", "panic")
    if not pos_id:
        return jsonify({"error": "id requerido"}), 400
    pos = next((p for p in _portfolio["posiciones"] if p["id"] == pos_id), None)
    if not pos:
        return jsonify({"error": "Posición no encontrada"}), 404
    bid = get_bid_opcion_tradier(pos["option_symbol"])
    precio_cierre = bid if bid else 0.01
    if pos.get("tradier_gtc_id"):
        cancelar_orden_tradier(pos["tradier_gtc_id"])
    if bid and bid > 0:
        vender_opcion_tradier(pos["option_symbol"], pos["simbolo"], pos.get("contratos", 1), bid)
    pos_cerrada = cerrar_posicion(pos_id, precio_cierre, motivo)
    if not pos_cerrada:
        return jsonify({"error": "Error cerrando posición"}), 500
    return jsonify({"ok": True, "bid_usado": precio_cierre, "posicion": pos_cerrada}), 200

@app.route("/portfolio/claude", methods=["POST"])
@require_admin
def portfolio_claude():
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    analisis = analizar_portfolio_claude(_portfolio["posiciones"], _portfolio["reto"])
    return jsonify({"analisis": analisis}), 200

@app.route("/derby/activar", methods=["POST"])
@require_admin
def derby_activar():
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    derby = _portfolio["derby"]
    derby["activo"]           = True
    derby["ganador"]          = None
    derby["esperando_cierre"] = False
    derby["turno_actual"]     = 1
    # Limpiar posiciones abiertas del portfolio — desvinculadas del derby nuevo
    for pos in _portfolio["posiciones"]:
        if pos.get("estado") == "abierta":
            pos["es_reto"]   = False
            pos["carril_id"] = None
    # Resetear caballos
    for c in derby["caballos"]:
        c["capital"]         = 0
        c["capital_inicial"] = 0
        c["ronda"]           = 0
        c["posicion"]        = None
        c["eliminado"]       = False
        c["historial"]       = []
    guardar_portfolio()
    enviar_telegram(
        f"🏇 <b>REAL LAZARO-PALMA — NUEVO DERBY ACTIVADO</b>\n"
        f"Caballos: Noel · Paula · Noel Andrés · Emilia\n"
        f"¡Que gane el mejor!"
    )
    return jsonify({"ok": True, "derby": _portfolio["derby"]}), 200

@app.route("/derby/desactivar", methods=["POST"])
@require_admin
def derby_desactivar():
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    _portfolio["derby"]["activo"] = False
    guardar_portfolio()
    enviar_telegram("⏸ <b>REAL LAZARO-PALMA PAUSADO</b>")
    return jsonify({"ok": True}), 200

@app.route("/derby/status", methods=["GET"])
@require_admin
def derby_status():
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    derby = _portfolio["derby"]
    posiciones_abiertas = {
        p.get("id"): p for p in _portfolio.get("posiciones", [])
        if p.get("estado") == "abierta"
    }
    caballos_info = []
    for c in derby["caballos"]:
        posicion = posiciones_abiertas.get(c.get("posicion"))
        carrera = None
        premio_actual = c["capital"]
        if posicion:
            pl_usd = posicion.get("pl_usd_actual", 0) or 0
            premio_actual = round(c["capital"] + pl_usd, 2)
            carrera = {
                "simbolo": posicion.get("simbolo"),
                "tipo": posicion.get("tipo"),
                "strike": posicion.get("strike"),
                "expiration": posicion.get("expiration"),
                "entrada": posicion.get("ts_entrada"),
                "pl_pct": posicion.get("pl_pct_actual"),
            }
        caballos_info.append({
            "id":       c["id"],
            "nombre":   c["nombre"],
            "capital":  c["capital"],
            "capital_inicial": c.get("capital_inicial", 0),
            "premio_actual": premio_actual,
            "ronda":    c["ronda"],
            "carrera": carrera,
            "eliminado": c.get("eliminado", False),
        })
    return jsonify({
        "nombre":           derby["nombre"],
        "activo":           derby["activo"],
        "ganador":          derby.get("ganador"),
        "esperando_cierre": derby.get("esperando_cierre", False),
        "turno_actual":     derby.get("turno_actual", 1),
        "caballos":         caballos_info,
    }), 200

# Mantener compatibilidad con rutas antiguas
@app.route("/portfolio/reto/activar", methods=["POST"])
@require_admin
def reto_activar():
    return derby_activar()

@app.route("/portfolio/reto/desactivar", methods=["POST"])
@require_admin
def reto_desactivar():
    return derby_desactivar()


@app.route("/mobile", methods=["GET"])
def mobile_access():
    """Puerta de Derby para celular; no solicita ni muestra el token administrativo."""
    if _mobile_session_valida(request.cookies.get("axis_mobile_session", "")):
        return redirect("/derby")
    bot_json = json.dumps(TELEGRAM_BOT_USERNAME).replace("<", "\\u003c")
    return Response(f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>AXIS · Acceso móvil</title><style>
body{{margin:0;background:#07111f;color:#edf5ff;font:16px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;display:grid;min-height:100vh;place-items:center}}
main{{width:min(92vw,440px);box-sizing:border-box;padding:30px 24px;border:1px solid #23415f;border-radius:18px;background:#0c1b2e;box-shadow:0 16px 45px #0008}}
h1{{margin:0 0 8px;font-size:25px}} p{{line-height:1.5;color:#bcd0e5}} .code{{margin:20px 0;padding:16px;text-align:center;border-radius:10px;background:#07111f;color:#7ee0ff;font:700 26px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:1px}}
a{{display:block;text-align:center;padding:13px;border-radius:10px;background:#20a5d6;color:#04111e;text-decoration:none;font-weight:700}} small{{display:block;margin-top:18px;color:#88a4bd;text-align:center}}
</style></head><body><main><h1>Acceso móvil AXIS</h1><p id="estado">Preparando un código privado…</p><div id="codigo" class="code">—</div><a id="telegram" href="#" target="_blank" rel="noopener">Abrir chat privado del bot</a><small>El código vence en 10 minutos. No compartas el token administrativo.</small></main>
<script>
const bot = {bot_json}; let pareja = null; let temporizador = null;
const estado = document.getElementById('estado'), codigo = document.getElementById('codigo'), enlace = document.getElementById('telegram');
async function iniciar() {{
  const r = await fetch('/mobile/pair/request', {{method:'POST', headers:{{'Content-Type':'application/json'}}, credentials:'same-origin'}});
  const d = await r.json();
  if (!r.ok || !d.ok) {{ estado.textContent = d.error || 'No se pudo iniciar el acceso. Recarga la página.'; codigo.textContent='—'; return; }}
  pareja = d; codigo.textContent = d.code;
  estado.textContent = 'Envíale este mensaje al bot por chat privado: /axis ' + d.code;
  if (d.bot_username) enlace.href = 'https://t.me/' + d.bot_username;
  else {{ enlace.style.display='none'; }}
  temporizador = setInterval(verificar, 3000);
}}
async function verificar() {{
  if (!pareja) return;
  const r = await fetch('/mobile/pair/status', {{method:'POST', headers:{{'Content-Type':'application/json'}}, credentials:'same-origin', body:JSON.stringify({{pair_id:pareja.pair_id, proof:pareja.proof}})}});
  const d = await r.json();
  if (d.authorized) {{ clearInterval(temporizador); estado.textContent='Acceso aprobado. Abriendo Derby…'; window.location.replace('/derby'); }}
  else if (r.status === 410) {{ clearInterval(temporizador); estado.textContent='El código venció. Recarga la página para crear uno nuevo.'; }}
}}
iniciar();
</script></body></html>''', mimetype="text/html")


@app.route("/mobile/pair/request", methods=["POST"])
def mobile_pair_request():
    if not AXIS_OWNER_TELEGRAM_USER_ID or not TELEGRAM_BOT_USERNAME:
        return _forbidden("mobile pairing not configured", 503)
    with _mobile_access_lock:
        cambio = _limpiar_mobile_access()
        if len(_mobile_access["pending"]) >= 20:
            if cambio:
                _guardar_mobile_access()
            return _forbidden("too many pending mobile pairings", 429)
        pair_id = secrets.token_urlsafe(18)
        proof = secrets.token_urlsafe(32)
        codigo = secrets.token_hex(4).upper()
        _mobile_access["pending"][pair_id] = {
            "proof_hash": _sha256(proof),
            "code_hash": _sha256(codigo),
            "expires_at": time.time() + MOBILE_PAIR_SECONDS,
        }
        _guardar_mobile_access()
    return jsonify({
        "ok": True, "pair_id": pair_id, "proof": proof, "code": codigo,
        "expires_in": MOBILE_PAIR_SECONDS, "bot_username": TELEGRAM_BOT_USERNAME,
    }), 201


@app.route("/mobile/pair/status", methods=["POST"])
def mobile_pair_status():
    cuerpo = request.get_json(silent=True) or {}
    pair_id = cuerpo.get("pair_id", "")
    proof = cuerpo.get("proof", "")
    if not isinstance(pair_id, str) or not isinstance(proof, str):
        return _forbidden()
    with _mobile_access_lock:
        cambio = _limpiar_mobile_access()
        datos = _mobile_access["pending"].get(pair_id)
        if not datos:
            if cambio:
                _guardar_mobile_access()
            return jsonify({"ok": False, "authorized": False, "error": "pairing expired"}), 410
        if not hmac.compare_digest(datos.get("proof_hash", ""), _sha256(proof)):
            if cambio:
                _guardar_mobile_access()
            return _forbidden()
        if not datos.get("approved_at"):
            if cambio:
                _guardar_mobile_access()
            return jsonify({"ok": True, "authorized": False}), 200
        sesion = secrets.token_urlsafe(32)
        _mobile_access["sessions"][_sha256(sesion)] = {
            "created_at": time.time(),
            "expires_at": time.time() + MOBILE_SESSION_SECONDS,
        }
        _mobile_access["pending"].pop(pair_id, None)
        _guardar_mobile_access()
    return _respuesta_mobile_autorizada(sesion)


@app.route("/mobile/logout", methods=["POST"])
def mobile_logout():
    sesion = request.cookies.get("axis_mobile_session", "")
    if sesion:
        with _mobile_access_lock:
            if _mobile_access["sessions"].pop(_sha256(sesion), None) is not None:
                _guardar_mobile_access()
    respuesta = jsonify({"ok": True})
    respuesta.delete_cookie("axis_mobile_session", path="/")
    return respuesta

@app.route("/derby", methods=["GET"])
def serve_derby():
    from flask import Response
    import os
    html_path = os.path.join(os.path.dirname(__file__), "axis_derby.html")
    if os.path.exists(html_path):
        with open(html_path, "r") as f:
            return Response(f.read(), mimetype="text/html")
    return Response("<h1>axis_derby.html no encontrado</h1>", mimetype="text/html"), 404

@app.route("/charts", methods=["GET"])
def serve_charts():
    from flask import Response
    import os
    html_path = os.path.join(os.path.dirname(__file__), "axis_charts.html")
    if os.path.exists(html_path):
        with open(html_path, "r") as f:
            return Response(f.read(), mimetype="text/html")
    return Response("<h1>axis_charts.html no encontrado</h1>", mimetype="text/html"), 404

@app.route("/app", methods=["GET"])
def serve_app():
    from flask import Response
    import os
    html_path = os.path.join(os.path.dirname(__file__), "axis_app.html")
    if os.path.exists(html_path):
        with open(html_path, "r") as f:
            return Response(f.read(), mimetype="text/html")
    return Response("<h1>App no encontrada</h1>", mimetype="text/html"), 404

def registrar_ejecucion_confirmada(resultado, opcion, estrategia, alert_id, decision,
                                   contratos=1, es_reto=False, carril_id=None):
    """Único punto de alta: solo después de que Tradier confirmó la compra."""
    if not resultado.get("ok"):
        return None
    venta_confirmada = bool(resultado.get("venta_ok", resultado.get("venta_id")))
    pos = registrar_posicion(
        opcion, estrategia, opcion["subyacente"], opcion["ask"],
        es_reto=es_reto, carril_id=carril_id, contratos=contratos,
        tradier_orden_id=resultado.get("id"), tradier_gtc_id=resultado.get("venta_id"),
        alert_id=alert_id, gtc_confirmada=venta_confirmada,
        gtc_error=resultado.get("venta_error"),
    )
    if not venta_confirmada:
        actualizar_alerta(
            alert_id, "ACTIVE", "GTC_SUBMISSION_FAILED",
            motivo_gtc=resultado.get("venta_error", "Tradier no confirmó GTC de salida"),
        )
    return pos


def iniciar_ejecucion_orden(orden_id, decision, contratos=1):
    """Bloquea un único intento persistente antes de hablar con Tradier."""
    datos = ordenes_pendientes.get(orden_id)
    if not datos:
        return None, "MISSING"
    estado = datos.get("estado_ejecucion", "PENDING")
    if estado != "PENDING":
        return None, estado
    datos.update({
        "estado_ejecucion": "EXECUTING",
        "intentos_ejecucion": int(datos.get("intentos_ejecucion", 0) or 0) + 1,
        "ts_ejecucion": datetime.now(EST).isoformat(),
        "decision_ejecucion": decision,
        "contratos_ejecucion": contratos,
    })
    guardar_ordenes()
    return datos, None


def finalizar_ejecucion_orden(orden_id):
    ordenes_pendientes.pop(orden_id, None)
    guardar_ordenes()


def marcar_ejecucion_fallida(orden_id, datos, resultado, decision):
    """Separa un rechazo definitivo de una respuesta broker ambigua."""
    error = resultado.get("error", "Tradier no confirmó compra")
    if resultado.get("ambiguous"):
        datos.update({
            "estado_ejecucion": "REVIEW_REQUIRED",
            "ultimo_error_ejecucion": error,
            "decision_ejecucion": decision,
        })
        guardar_ordenes()
        actualizar_alerta(
            datos.get("alert_id"), "NOTIFIED", "TRADIER_EXECUTION_REVIEW",
            decision=decision, motivo_ejecucion_no_confirmada=error,
        )
        return "REVIEW_REQUIRED"
    finalizar_ejecucion_orden(orden_id)
    actualizar_alerta(
        datos.get("alert_id"), "CANCELLED", "TRADIER_EXECUTION_FAILED",
        decision=decision, motivo_cancelacion=error,
    )
    return "FAILED"


def revisar_ejecucion_orden(orden_id):
    """Consulta la posición broker antes de permitir un reintento manual."""
    datos = ordenes_pendientes.get(orden_id)
    if not datos:
        return "MISSING", None
    if datos.get("estado_ejecucion") != "REVIEW_REQUIRED":
        return datos.get("estado_ejecucion", "PENDING"), datos
    encontrada = tiene_posicion_opcion_tradier(datos.get("opcion", {}).get("symbol"))
    datos["ts_revision_broker"] = datetime.now(EST).isoformat()
    if encontrada is True:
        datos["estado_ejecucion"] = "BROKER_POSITION_FOUND"
        guardar_ordenes()
        actualizar_alerta(
            datos.get("alert_id"), "NOTIFIED", "TRADIER_BROKER_POSITION_FOUND",
            motivo_ejecucion_no_confirmada=datos.get("ultimo_error_ejecucion"),
        )
        return "BROKER_POSITION_FOUND", datos
    if encontrada is False:
        datos["estado_ejecucion"] = "PENDING"
        guardar_ordenes()
        actualizar_alerta(datos.get("alert_id"), "NOTIFIED", "TRADIER_REVIEW_CLEAR")
        return "REVIEW_CLEAR", datos
    guardar_ordenes()
    return "REVIEW_UNAVAILABLE", datos


@app.route("/telegram_webhook", methods=["POST"])
@require_telegram_webhook
def telegram_webhook():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"ok": True}), 200
        message = data.get("message")
        if message:
            _procesar_emparejamiento_movil(message)
            return jsonify({"ok": True}), 200
        callback = data.get("callback_query")
        if not callback:
            return jsonify({"ok": True}), 200
        callback_id   = callback.get("id")
        callback_data = callback.get("data", "")
        message_id    = callback.get("message", {}).get("message_id")
        chat_id       = callback.get("message", {}).get("chat", {}).get("id")
        if str(chat_id) != str(TELEGRAM_CHAT_ID):
            return _forbidden("unauthorized telegram chat", 403)
        partes = callback_data.split(":")
        if len(partes) < 2:
            return jsonify({"ok": True}), 200
        accion   = partes[0]
        orden_id = partes[1]
        carril_id_reto = int(partes[2]) if len(partes) >= 3 else None
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
                      json={"callback_query_id": callback_id}, timeout=5)

        def editar_mensaje(texto):
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText",
                          json={"chat_id": chat_id, "message_id": message_id, "text": texto, "parse_mode": "HTML"}, timeout=5)

        def agregar_recibo(recibo):
            texto_original = datos.get("texto_original", "")
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText",
                          json={"chat_id": chat_id, "message_id": message_id,
                                "text": f"{texto_original}\n\n{recibo}", "parse_mode": "HTML"}, timeout=5)

        def editar_botones(botones):
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageReplyMarkup",
                json={"chat_id": chat_id, "message_id": message_id,
                      "reply_markup": {"inline_keyboard": botones}},
                timeout=5,
            )

        if accion == "exec_multi":
            # Mostrar menu de contratos 2-10
            datos_menu = ordenes_pendientes.get(orden_id)
            estado_menu = datos_menu.get("estado_ejecucion", "PENDING") if datos_menu else "MISSING"
            if estado_menu != "PENDING":
                editar_mensaje("⚠️ <b>Orden no disponible para otro envío.</b> Revisa su estado actual.")
                return jsonify({"ok": True}), 200
            fila1 = [{"text": str(i), "callback_data": f"exec_c:{orden_id}:{i}"} for i in range(2, 7)]
            fila2 = [{"text": str(i), "callback_data": f"exec_c:{orden_id}:{i}"} for i in range(7, 11)]
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageReplyMarkup",
                json={"chat_id": chat_id, "message_id": message_id,
                      "reply_markup": {"inline_keyboard": [fila1, fila2]}},
                timeout=5
            )

        elif accion == "exec_c":
            # Ejecutar con cantidad elegida
            contratos = int(partes[2]) if len(partes) >= 3 else 1
            datos, estado_orden = iniciar_ejecucion_orden(orden_id, "EXECUTE", contratos)
            if not datos:
                editar_mensaje("⚠️ <b>Orden no disponible.</b> Ya fue expirada, está en curso o requiere revisión Tradier.")
                return jsonify({"ok": True}), 200
            editar_botones([])
            opcion     = datos["opcion"]
            estrategia = datos.get("estrategia", "AXIS")
            alert_id   = datos.get("alert_id")
            resultado_tradier = ejecutar_orden_tradier_contratos(opcion, contratos)
            costo_total = round(opcion["ask"] * 100 * contratos, 2)
            pos = registrar_ejecucion_confirmada(
                resultado_tradier, opcion, estrategia, alert_id, "EXECUTE", contratos=contratos,
            )
            if not pos:
                resultado_flujo = marcar_ejecucion_fallida(orden_id, datos, resultado_tradier, "EXECUTE")
                if resultado_flujo == "REVIEW_REQUIRED":
                    estado_tradier = "⚠️ Compra no confirmada. Revisa Tradier antes de reintentar manualmente."
                    encabezado = "⚠️ <b>EJECUCIÓN EN REVISIÓN</b> — sin alta en Portfolio"
                    editar_botones([[{"text": "🔎 REVISAR TRADIER", "callback_data": f"review:{orden_id}"}]])
                else:
                    estado_tradier = f"⚠️ Compra rechazada: {resultado_tradier.get('error', '')}"
                    encabezado = "⚠️ <b>NO EJECUTADA</b> — no registrada en Portfolio"
            elif resultado_tradier.get("venta_ok"):
                finalizar_ejecucion_orden(orden_id)
                estado_tradier = "✅ Compra y GTC confirmados por Tradier"
                encabezado = f"✅ <b>EJECUTADA</b> — {contratos} contrato{'s' if contratos > 1 else ''}"
            else:
                finalizar_ejecucion_orden(orden_id)
                estado_tradier = f"⚠️ Compra confirmada; GTC no confirmado: {resultado_tradier.get('venta_error', '')}"
                encabezado = "⚠️ <b>COMPRA CONFIRMADA</b> — GTC pendiente"
            agregar_recibo(
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{encabezado}\n"
                f"📋 <b>Opción:</b> {opcion['symbol']}\n"
                f"📊 <b>Contratos:</b> {contratos} × ${opcion['ask']:.2f} = ${costo_total:.2f}\n"
                f"🎯 <b>GTC:</b> ${opcion['ask']*2:.2f} (+100%)\n"
                f"🏦 <b>Tradier:</b> {estado_tradier}"
            )

        elif accion == "exec":
            datos, estado_orden = iniciar_ejecucion_orden(orden_id, "EXECUTE", 1)
            if not datos:
                editar_mensaje("⚠️ <b>Orden no disponible.</b> Ya fue expirada, está en curso o requiere revisión Tradier.")
                return jsonify({"ok": True}), 200
            editar_botones([])
            opcion     = datos["opcion"]
            estrategia = datos.get("estrategia", "AXIS")
            alert_id   = datos.get("alert_id")
            resultado_tradier = ejecutar_orden_tradier(opcion)
            pos = registrar_ejecucion_confirmada(resultado_tradier, opcion, estrategia, alert_id, "EXECUTE")
            if not pos:
                resultado_flujo = marcar_ejecucion_fallida(orden_id, datos, resultado_tradier, "EXECUTE")
                if resultado_flujo == "REVIEW_REQUIRED":
                    estado_tradier = "⚠️ Compra no confirmada. Revisa Tradier antes de reintentar manualmente."
                    encabezado = "⚠️ <b>EJECUCIÓN EN REVISIÓN</b> — sin alta en Portfolio"
                    editar_botones([[{"text": "🔎 REVISAR TRADIER", "callback_data": f"review:{orden_id}"}]])
                else:
                    estado_tradier = f"⚠️ Compra rechazada: {resultado_tradier.get('error', '')}"
                    encabezado = "⚠️ <b>NO EJECUTADA</b> — no registrada en Portfolio"
            elif resultado_tradier.get("venta_ok"):
                finalizar_ejecucion_orden(orden_id)
                estado_tradier = "✅ Compra y GTC confirmados por Tradier"
                encabezado = "✅ <b>EJECUTADA</b> — registrada en Portfolio"
            else:
                finalizar_ejecucion_orden(orden_id)
                estado_tradier = f"⚠️ Compra confirmada; GTC no confirmado: {resultado_tradier.get('venta_error', '')}"
                encabezado = "⚠️ <b>COMPRA CONFIRMADA</b> — GTC pendiente"
            agregar_recibo(
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{encabezado}\n"
                f"📋 <b>Opción:</b> {opcion['symbol']}\n"
                f"💰 <b>Costo:</b> ${opcion['ask']*100:.2f} | <b>GTC:</b> ${opcion['ask']*2:.2f}\n"
                f"🏦 <b>Tradier:</b> {estado_tradier}"
            )

        elif accion == "reto":
            caballo_id = carril_id_reto or 1
            datos, estado_orden = iniciar_ejecucion_orden(orden_id, "DERBY", 1)
            if not datos:
                editar_mensaje("⚠️ <b>Orden no disponible.</b> Ya fue expirada, está en curso o requiere revisión Tradier.")
                return jsonify({"ok": True}), 200
            editar_botones([])
            opcion     = datos["opcion"]
            estrategia = datos.get("estrategia", "AXIS")
            alert_id   = datos.get("alert_id")
            derby = _portfolio["derby"]
            caballo = next((c for c in derby["caballos"] if c["id"] == caballo_id), None)
            if not caballo or caballo.get("eliminado"):
                # Buscar siguiente disponible
                nuevo_id = None
                for c in derby["caballos"]:
                    if not c.get("eliminado") and c["posicion"] is None:
                        nuevo_id = c["id"]
                        break
                if not nuevo_id:
                    finalizar_ejecucion_orden(orden_id)
                    actualizar_alerta(alert_id, "CANCELLED", "NO_DERBY_LANE_AVAILABLE",
                                      decision="DERBY")
                    agregar_recibo(f"━━━━━━━━━━━━━━━━━━\n⚠️ <b>Todos los caballos ocupados o eliminados</b>")
                    return jsonify({"ok": True}), 200
                caballo_id = nuevo_id
                caballo    = next((c for c in derby["caballos"] if c["id"] == caballo_id), None)
            if caballo["posicion"] is not None:
                # Buscar otro caballo libre
                nuevo_id = None
                for c in derby["caballos"]:
                    if not c.get("eliminado") and c["posicion"] is None and c["id"] != caballo_id:
                        nuevo_id = c["id"]
                        break
                if not nuevo_id:
                    finalizar_ejecucion_orden(orden_id)
                    actualizar_alerta(alert_id, "CANCELLED", "NO_DERBY_LANE_AVAILABLE",
                                      decision="DERBY")
                    agregar_recibo(f"━━━━━━━━━━━━━━━━━━\n⚠️ <b>Todos los caballos en carrera</b>")
                    return jsonify({"ok": True}), 200
                caballo_id = nuevo_id
                caballo    = next((c for c in derby["caballos"] if c["id"] == caballo_id), None)
            estado_caballo_previo = {
                "capital": caballo["capital"],
                "capital_inicial": caballo["capital_inicial"],
                "ronda": caballo["ronda"],
                "posicion": caballo["posicion"],
            }
            costo_1cont = round(opcion["ask"] * 100, 2)
            if caballo["capital"] == 0:
                # Primera carrera — sin límite de capital
                caballo["capital"]         = costo_1cont
                caballo["capital_inicial"] = costo_1cont
                contratos   = 1
                presupuesto = costo_1cont
            else:
                # Carreras siguientes — usa capital acumulado
                presupuesto = round(caballo["capital"] * 0.80, 2)
                if costo_1cont > presupuesto:
                    opcion_reto = buscar_opcion_reto(opcion, presupuesto)
                    if not opcion_reto:
                        finalizar_ejecucion_orden(orden_id)
                        actualizar_alerta(alert_id, "CANCELLED", "DERBY_CAPITAL_INSUFFICIENT",
                                          decision="DERBY")
                        rec_claude = recomendar_opcion_claude(opcion, caballo["capital"], presupuesto)
                        agregar_recibo(
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"⚠️ <b>Capital insuficiente — {caballo['nombre']}</b>\n"
                            f"Capital: ${caballo['capital']:.2f} | Presupuesto: ${presupuesto:.2f}\n"
                            f"🤖 <b>Claude recomienda:</b>\n{rec_claude}"
                        )
                        return jsonify({"ok": True}), 200
                    opcion = opcion_reto
                    costo_1cont = round(opcion["ask"] * 100, 2)
                contratos = max(1, int(presupuesto // costo_1cont))
            resultado_tradier = ejecutar_orden_tradier_contratos(opcion, contratos)
            costo_total = round(opcion["ask"] * 100 * contratos, 2)
            pos = registrar_ejecucion_confirmada(
                resultado_tradier, opcion, estrategia, alert_id, "DERBY", contratos=contratos,
                es_reto=True, carril_id=caballo_id,
            )
            if not pos:
                caballo.update(estado_caballo_previo)
                guardar_portfolio()
                resultado_flujo = marcar_ejecucion_fallida(orden_id, datos, resultado_tradier, "DERBY")
                if resultado_flujo == "REVIEW_REQUIRED":
                    estado_tradier = "⚠️ Compra no confirmada. Revisa Tradier antes de reintentar manualmente."
                    encabezado = "⚠️ <b>EJECUCIÓN EN REVISIÓN</b> — carril sin cambios"
                    editar_botones([[{"text": "🔎 REVISAR TRADIER", "callback_data": f"review:{orden_id}"}]])
                else:
                    estado_tradier = f"⚠️ Compra rechazada: {resultado_tradier.get('error', '')}"
                    encabezado = "⚠️ <b>NO EJECUTADA</b> — carril sin cambios"
            else:
                finalizar_ejecucion_orden(orden_id)
                siguiente = next((c["id"] for c in derby["caballos"]
                                  if not c.get("eliminado") and c["posicion"] is None and c["id"] != caballo_id), None)
                derby["turno_actual"] = siguiente if siguiente else caballo_id
                guardar_portfolio()
                if resultado_tradier.get("venta_ok"):
                    estado_tradier = "✅ Compra y GTC confirmados por Tradier"
                    encabezado = f"🏇 <b>{caballo['nombre']} — {'PRIMERA CARRERA' if caballo['ronda'] == 1 else f'CARRERA #{caballo[chr(114)+chr(111)+chr(110)+chr(100)+chr(97)]}'}</b>"
                else:
                    estado_tradier = f"⚠️ Compra confirmada; GTC no confirmado: {resultado_tradier.get('venta_error', '')}"
                    encabezado = f"⚠️ <b>{caballo['nombre']} — COMPRA CONFIRMADA, GTC PENDIENTE</b>"
            agregar_recibo(
                f"━━━━━━━━━━━━━━━━━━\n"
                f"{encabezado}\n"
                f"📋 <b>Opción:</b> {opcion['symbol']}\n"
                f"📊 <b>Contratos:</b> {contratos} × ${opcion['ask']:.2f} = ${costo_total:.2f}\n"
                f"💰 <b>Capital:</b> ${caballo['capital']:.2f}\n"
                f"🎯 <b>GTC:</b> ${opcion['ask']*2:.2f} (+100%)\n"
                f"🔄 <b>Siguiente:</b> {next((x['nombre'] for x in derby['caballos'] if x['id'] == derby['turno_actual']), 'N/A')}\n"
                f"🏦 <b>Tradier:</b> {estado_tradier}"
            )

        elif accion == "review":
            resultado_revision, datos = revisar_ejecucion_orden(orden_id)
            if resultado_revision == "REVIEW_CLEAR":
                editar_botones([botones_orden_actuales(orden_id)])
                editar_mensaje(
                    f"{datos.get('texto_original', '')}\n\n━━━━━━━━━━━━━━━━━━\n"
                    "✅ <b>Tradier sin posición encontrada</b> — puedes reintentar manualmente una vez."
                )
            elif resultado_revision == "BROKER_POSITION_FOUND":
                editar_botones([])
                editar_mensaje(
                    f"{datos.get('texto_original', '')}\n\n━━━━━━━━━━━━━━━━━━\n"
                    "⚠️ <b>Tradier muestra una posición</b> — bloqueado para evitar duplicado; requiere reconciliación."
                )
            elif resultado_revision == "REVIEW_UNAVAILABLE":
                editar_mensaje("⚠️ <b>Tradier aún no responde.</b> No se reintentó la compra; vuelve a revisar más tarde.")
            else:
                editar_mensaje("⚠️ <b>Revisión no disponible.</b> La orden fue expirada o ya se resolvió.")

        elif accion == "skip":
            datos = ordenes_pendientes.get(orden_id)
            if datos and datos.get("estado_ejecucion", "PENDING") == "PENDING":
                finalizar_ejecucion_orden(orden_id)
                actualizar_alerta(datos.get("alert_id"), "CANCELLED", "USER_SKIPPED",
                                  decision="SKIP")
                agregar_recibo("━━━━━━━━━━━━━━━━━━\n❌ <b>Orden ignorada</b>")
            else:
                editar_mensaje("⚠️ <b>Orden no disponible para ignorar.</b> Está en curso o requiere revisión Tradier.")

    except Exception as e:
        print(f"Error webhook: {e}")
    return jsonify({"ok": True}), 200

@app.route("/tradier_history_test", methods=["GET"])
@require_admin
def tradier_history_test():
    if not TRADIER_TOKEN_REAL:
        return jsonify({"error": "TRADIER_TOKEN_REAL no configurado en Railway"}), 400
    resultados = {}
    try:
        r = requests.get(f"{TRADIER_BASE_REAL}/markets/quotes", headers=TRADIER_HEADERS_REAL,
                         params={"symbols": "SPY"}, timeout=10)
        resultados["precio_status"] = r.status_code
        if r.status_code == 200:
            precio = r.json().get("quotes", {}).get("quote", {}).get("last")
            resultados["SPY_precio_real"] = precio
    except Exception as e:
        resultados["error_precio"] = str(e)
    return jsonify(resultados), 200

@app.route("/tradier_raw", methods=["GET"])
@require_admin
def tradier_raw():
    """Endpoint permanente de SOLO LECTURA. Llama Tradier directo (sin pasar
    por la base de datos local de AXIS) para verificar datos crudos contra
    TC2000/TradingView cuando haya dudas de precision. No afecta ninguna
    logica de construccion ni evaluacion de AXIS."""
    from datetime import date as _date, timedelta as _td
    simbolo  = request.args.get("simbolo", "SPY").upper()
    interval = request.args.get("interval", "daily")
    dias     = int(request.args.get("dias", 5))

    try:
        hoy = _date.today()
        if interval == "daily":
            fecha_ini = hoy - _td(days=dias * 2)  # buffer por fines de semana
            r = requests.get(
                f"{TRADIER_BASE_REAL}/markets/history",
                headers=TRADIER_HEADERS_REAL,
                params={
                    "symbol":   simbolo,
                    "interval": "daily",
                    "start":    fecha_ini.strftime("%Y-%m-%d"),
                    "end":      hoy.strftime("%Y-%m-%d"),
                },
                timeout=15
            )
            if r.status_code != 200:
                return jsonify({"error": f"Tradier HTTP {r.status_code}"}), 500
            hist = r.json().get("history") or {}
            data = hist.get("day", [])
            if isinstance(data, dict): data = [data]
            data = data[-dias:]
            resultado = [{
                "fecha": d["date"], "open": float(d["open"]), "high": float(d["high"]),
                "low": float(d["low"]), "close": float(d["close"]),
                "volume": int(d.get("volume", 0))
            } for d in data]
        else:
            fecha_ini = hoy - _td(days=dias)
            r = requests.get(
                f"{TRADIER_BASE_REAL}/markets/timesales",
                headers=TRADIER_HEADERS_REAL,
                params={
                    "symbol": simbolo, "interval": "15min",
                    "start": f"{fecha_ini.strftime('%Y-%m-%d')} 09:00",
                    "end": f"{hoy.strftime('%Y-%m-%d')} 16:30",
                    "session_filter": "open",
                },
                timeout=20
            )
            if r.status_code != 200:
                return jsonify({"error": f"Tradier HTTP {r.status_code}"}), 500
            series = r.json().get("series")
            data = []
            if series and series != "null":
                data = series.get("data", [])
                if isinstance(data, dict): data = [data]
            resultado = [{
                "time": d["time"], "open": float(d["open"]), "high": float(d["high"]),
                "low": float(d["low"]), "close": float(d["close"])
            } for d in data]

        return jsonify({
            "simbolo": simbolo, "interval": interval,
            "fuente": "Tradier directo — sin construccion AXIS",
            "total": len(resultado), "datos": resultado
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/velas_status", methods=["GET"])
def velas_status():
    from datetime import datetime as _dt
    resultado = {}
    for simbolo in ACTIVOS:
        local = cargar_velas_local(simbolo)
        barras_15min = [b for b in local["barras"] if b.get("interval") == "15min"]
        barras_daily = [b for b in local["barras"] if b.get("interval") == "daily"]
        ultima = local.get("ultima_barra")
        hoy = _dt.now().strftime("%Y-%m-%d")
        tiene_hoy = any(b["time"].startswith(hoy) for b in barras_15min) if barras_15min else False
        es_hoy_mercado = es_dia_mercado(datetime.now(EST))
        resultado[simbolo] = {
            "total_registros":  len(local["barras"]),
            "barras_15min":     len(barras_15min),
            "barras_daily":     len(barras_daily),
            "ultima_barra":     ultima,
            "tiene_data_hoy":   tiene_hoy,
            "status": "✅ OK" if (len(barras_15min) > 100 and (tiene_hoy or not es_hoy_mercado)) else
                      "⚠️ SIN DATA HOY" if (len(barras_15min) > 100 and es_hoy_mercado) else
                      "❌ BASE VACÍA"
        }
    return jsonify({"fecha": _dt.now().strftime("%Y-%m-%d %H:%M EST"), "activos": resultado}), 200

@app.route("/tradier_hoy", methods=["GET"])
@require_admin
def tradier_hoy():
    from datetime import date
    hoy = date.today().strftime("%Y-%m-%d")
    resultado = {}
    for simbolo in ACTIVOS:
        try:
            r = requests.get(f"{TRADIER_BASE_REAL}/markets/timesales", headers=TRADIER_HEADERS_REAL,
                             params={"symbol": simbolo, "interval": "15min",
                                     "start": f"{hoy} 09:00", "end": f"{hoy} 16:30",
                                     "session_filter": "open"}, timeout=30)
            data   = r.json()
            series = data.get("series")
            if not series or series == "null":
                resultado[simbolo] = {"total_barras": 0, "ultima_barra": None, "status": "⚠️ SIN DATOS"}
                continue
            barras = series.get("data", [])
            if isinstance(barras, dict): barras = [barras]
            ultima = barras[-1]["time"] if barras else None
            resultado[simbolo] = {
                "total_barras": len(barras), "primera_barra": barras[0]["time"] if barras else None,
                "ultima_barra": ultima,
                "status": "✅ OK" if len(barras) >= 4 else f"⚠️ INCOMPLETO ({len(barras)} barras)",
            }
        except Exception as e:
            resultado[simbolo] = {"total_barras": 0, "ultima_barra": None, "status": f"❌ ERROR: {e}"}
    return jsonify({"fecha": hoy, "activos": resultado}), 200

@app.route("/rellenar_velas", methods=["POST"])
@require_admin
def rellenar_velas():
    from datetime import date as _date, timedelta as _td
    resultado = {}
    hoy = _date.today()
    fecha_ini = restar_dias_habiles(hoy, 38)
    for simbolo in ACTIVOS:
        local = cargar_velas_local(simbolo)
        b15   = [b for b in local["barras"] if b.get("interval") == "15min"]
        antes = len(b15)
        try:
            r = requests.get(f"{TRADIER_BASE_REAL}/markets/timesales", headers=TRADIER_HEADERS_REAL,
                             params={"symbol": simbolo, "interval": "15min",
                                     "start": f"{fecha_ini.strftime('%Y-%m-%d')} 09:00",
                                     "end": f"{(hoy - _td(days=1)).strftime('%Y-%m-%d')} 16:30",
                                     "session_filter": "open"}, timeout=30)
            if r.status_code != 200:
                resultado[simbolo] = f"❌ HTTP {r.status_code}"
                continue
            s = r.json().get("series")
            if not s or s == "null":
                resultado[simbolo] = "⚠️ Sin datos Tradier"
                continue
            barras_tradier = s.get("data", [])
            if isinstance(barras_tradier, dict): barras_tradier = [barras_tradier]
            tiempos_existentes = {b["time"] for b in b15}
            nuevas = []
            for b in barras_tradier:
                t = b["time"]
                if t not in tiempos_existentes:
                    b["interval"] = "15min"
                    nuevas.append(b)
            if nuevas:
                local["barras"].extend(nuevas)
                local["barras"].sort(key=lambda x: x["time"])
                local["ultima_barra"] = local["barras"][-1]["time"]
                guardar_velas_local(simbolo, local)
                resultado[simbolo] = f"✅ +{len(nuevas)} barras nuevas ({antes} → {antes+len(nuevas)})"
            else:
                resultado[simbolo] = f"✅ Sin faltantes ({antes} barras)"
            # Red de seguridad — rellenar barras diarias faltantes tambien
            try:
                daily_agregadas = rellenar_dias_faltantes(simbolo, dias_atras=10)
                if daily_agregadas:
                    resultado[simbolo] += f" | +{daily_agregadas} barras diarias recuperadas"
            except Exception as e:
                resultado[simbolo] += f" | error daily: {e}"
        except Exception as e:
            resultado[simbolo] = f"❌ Error: {e}"
    return jsonify({"fecha": str(hoy), "resultado": resultado}), 200

@app.route("/establecer_p1", methods=["POST"])
@require_admin
def establecer_p1():
    simbolo = request.args.get("activo", "SPY").upper()
    if simbolo not in ACTIVOS:
        return jsonify({"error": f"Activo {simbolo} no reconocido"}), 400
    try:
        p1_high = float(request.args["p1_high"])
        p1_fecha = request.args["p1_fecha"]
        p1_hora  = int(request.args["p1_hora"])
        canal[simbolo]["p1"] = {"fecha": p1_fecha, "hora_est": p1_hora, "high": p1_high}
        canal[simbolo]["p2"] = None
        canal[simbolo]["p3"] = None
        canal[simbolo]["p2_actual_high"] = None
        canal[simbolo]["p2_actual_ts"]   = None
        canal[simbolo]["on"]      = False
        canal[simbolo]["apagado"] = False
        canal[simbolo]["roto"]    = False
        canal[simbolo]["fecha_ruptura"] = None
        guardar_canales()
        return jsonify({"ok": True, "simbolo": simbolo, "p1": canal[simbolo]["p1"]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/reset_canales", methods=["POST"])
@require_admin
def reset_canales():
    for simbolo in ACTIVOS:
        canal[simbolo] = canal_vacio()
    guardar_canales()
    return jsonify({"ok": True, "mensaje": "Todos los canales reseteados a cero"}), 200

@app.route("/archivar_hoy", methods=["POST"])
@require_admin
def archivar_hoy():
    fecha = datetime.now(EST).strftime("%Y-%m-%d")
    archivar_señales_dia(fecha)
    historial = cargar_señales_historicas()
    return jsonify({"ok": True, "fecha": fecha, "señales": historial.get(fecha, {})}), 200

@app.route("/señales_historicas", methods=["GET"])
@require_admin
def ruta_señales_historicas():
    simbolo = request.args.get("simbolo", "").upper()
    historial = cargar_señales_historicas()
    if simbolo:
        resultado = {}
        for fecha, activos in historial.items():
            señales = activos.get(simbolo, [])
            if señales:
                resultado[fecha] = señales
        return jsonify({"simbolo": simbolo, "señales": resultado}), 200
    else:
        return jsonify({"historial": historial}), 200

@app.route("/bitacora", methods=["GET"])
def ruta_bitacora():
    with open(os.path.join(os.path.dirname(__file__), "axis_bitacora.html"), "r") as f:
        return f.read(), 200, {"Content-Type": "text/html"}

@app.route("/bitacora/seed", methods=["POST"])
@require_admin
def ruta_bitacora_seed():
    force = request.args.get("force", "0") == "1"
    if os.path.exists(BITACORA_FILE) and not force:
        with open(BITACORA_FILE, "r") as f:
            data = json.load(f)
        if data.get("entradas"):
            return jsonify({"ok": False, "msg": "Bitácora ya tiene entradas — usa ?force=1 para sobreescribir"}), 200
    data = {
        "proyecto":   "AXIS Trading System",
        "repo":       "https://github.com/lazaronoel69/SPY-ALERT-SERVER",
        "produccion": "https://web-production-bf9d0.up.railway.app",
        "instrucciones_ai": "Lee este archivo completo antes de actuar. NUNCA codifiques sin autorización de Noel. Conversa, diseña, Noel aprueba, luego implementas. Un cambio a la vez. Verifica con /status después de cada deploy.",
        "versiones": {
            "server_py":          f"v{AXIS_VERSION}",
            "axis_charts_html":   "v1.4.1",
            "axis_portfolio_html":"v1.3",
            "axis_bitacora_html": "v1.0"
        },
        "activos": ACTIVOS,
        "entradas": []
    }
    with open(BITACORA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return jsonify({"ok": True, "msg": "Bitácora inicializada"}), 200

@app.route("/bitacora/resolver", methods=["POST"])
@require_admin
def ruta_bitacora_resolver():
    try:
        body = request.get_json()
        id_entrada = int(body.get("id"))
        if not os.path.exists(BITACORA_FILE):
            return jsonify({"error": "Bitácora vacía"}), 404
        with open(BITACORA_FILE, "r") as f:
            data = json.load(f)
        for e in data["entradas"]:
            if e["id"] == id_entrada:
                e["estado"] = "done"
                e["fecha_resuelto"] = datetime.now(EST).strftime("%Y-%m-%d %H:%M EST")
                break
        with open(BITACORA_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/bitacora/data", methods=["GET"])
@require_admin
def ruta_bitacora_data():
    """Devuelve todas las entradas de la bitácora en JSON — para uso de AI."""
    try:
        if not os.path.exists(BITACORA_FILE):
            return jsonify({"entradas": [], "total": 0}), 200
        with open(BITACORA_FILE, "r") as f:
            data = json.load(f)
        # v8.63 — timestamp para que AI sepa hora/día al conectarse
        data["ahora_est"] = datetime.now(EST).strftime("%Y-%m-%d %H:%M EST")
        data["fuentes"] = {
            "server_py":   "https://web-production-bf9d0.up.railway.app/source/server.py",
            "charts_html": "https://web-production-bf9d0.up.railway.app/source/axis_charts.html",
            "status":      "https://web-production-bf9d0.up.railway.app/status",
            "diagnostico": "https://web-production-bf9d0.up.railway.app/diagnostico",
            "auth":        "Todas las fuentes requieren X-AXIS-Admin-Token; no usar secretos en URLs.",
        }
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/bitacora/agregar", methods=["POST"])
@require_admin
def ruta_bitacora_agregar():
    try:
        body = request.get_json()
        if not body:
            return jsonify({"error": "Body vacío"}), 400
        if not os.path.exists(BITACORA_FILE):
            data = {"entradas": []}
        else:
            with open(BITACORA_FILE, "r") as f:
                data = json.load(f)
        entrada = {
            "id":          len(data["entradas"]) + 1,
            "fecha":       datetime.now(EST).strftime("%Y-%m-%d %H:%M EST"),
            "estado":      body.get("estado", "pend"),
            "titulo":      body.get("titulo", ""),
            "descripcion": body.get("descripcion", ""),
            "autor":       body.get("autor", "Noel"),
            "activo":      body.get("activo", ""),
        }
        data["entradas"].insert(0, entrada)
        with open(BITACORA_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return jsonify({"ok": True, "entrada": entrada}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/velas_daily", methods=["GET"])
@require_admin
def ruta_velas_daily():
    simbolo   = request.args.get("simbolo", "SPY").upper()
    timeframe = request.args.get("tf", "daily")
    local = cargar_velas_local(simbolo)
    barras_daily = [b for b in local["barras"] if b.get("interval") == "daily"]
    if not barras_daily:
        return jsonify({"error": f"Sin datos diarios para {simbolo}"}), 500
    barras_daily.sort(key=lambda x: x["time"])
    if timeframe == "daily":
        resultado = [{"datetime": b["time"][:10], "open": str(round(b["open"], 4)),
                      "high": str(round(b["high"], 4)), "low": str(round(b["low"], 4)),
                      "close": str(round(b["close"], 4)), "tf": "daily"} for b in barras_daily]
    elif timeframe == "weekly":
        from datetime import datetime as _dt, timedelta as _td
        grupos = {}
        for b in barras_daily:
            d   = _dt.strptime(b["time"][:10], "%Y-%m-%d")
            lun = (d - _td(days=d.weekday())).strftime("%Y-%m-%d")
            if lun not in grupos: grupos[lun] = []
            grupos[lun].append(b)
        resultado = []
        for lun in sorted(grupos.keys()):
            bs = grupos[lun]
            resultado.append({"datetime": lun, "open": str(round(bs[0]["open"], 4)),
                               "high": str(round(max(b["high"] for b in bs), 4)),
                               "low": str(round(min(b["low"] for b in bs), 4)),
                               "close": str(round(bs[-1]["close"], 4)), "tf": "weekly"})
    elif timeframe == "monthly":
        grupos = {}
        for b in barras_daily:
            mes = b["time"][:7]
            if mes not in grupos: grupos[mes] = []
            grupos[mes].append(b)
        resultado = []
        for mes in sorted(grupos.keys()):
            bs = grupos[mes]
            resultado.append({"datetime": mes + "-01", "open": str(round(bs[0]["open"], 4)),
                               "high": str(round(max(b["high"] for b in bs), 4)),
                               "low": str(round(min(b["low"] for b in bs), 4)),
                               "close": str(round(bs[-1]["close"], 4)), "tf": "monthly"})
    else:
        return jsonify({"error": f"Timeframe desconocido: {timeframe}"}), 400
    resultado.reverse()
    return jsonify({"simbolo": simbolo, "timeframe": timeframe, "total": len(resultado), "velas": resultado}), 200

@app.route("/velas", methods=["GET"])
@require_admin
def ruta_velas():
    simbolo = request.args.get("simbolo", "SPY").upper()
    velas   = get_velas(simbolo, outputsize=280)
    if not velas:
        return jsonify({"error": f"Sin datos para {simbolo}"}), 500
    ed = estado_dia.get(simbolo, {})
    senales_hoy = []
    fecha_hoy = datetime.now(EST).strftime("%Y-%m-%d")
    if ed.get("fecha") == fecha_hoy:
        detalle = ed.get("señales_detalle", [])
        if detalle:
            for d in detalle:
                senales_hoy.append({"tipo": d["tipo"], "fecha": fecha_hoy, "vela": d.get("vela"), "hora": d.get("hora")})
        else:
            if ed.get("vr1_fired"):  senales_hoy.append({"tipo": "1VR",  "fecha": fecha_hoy, "vela": "V1", "hora": None})
            if ed.get("rpg_fired"):  senales_hoy.append({"tipo": "RPG",  "fecha": fecha_hoy, "vela": None, "hora": None})
            if ed.get("gna_fired"):  senales_hoy.append({"tipo": "GNA",  "fecha": fecha_hoy, "vela": None, "hora": None})
            if ed.get("gba_fired"):  senales_hoy.append({"tipo": "GBA",  "fecha": fecha_hoy, "vela": None, "hora": None})
            if ed.get("pm40_fired"): senales_hoy.append({"tipo": "PM40", "fecha": fecha_hoy, "vela": None, "hora": None})
            if ed.get("4ps_fired"):  senales_hoy.append({"tipo": "4PS",  "fecha": fecha_hoy, "vela": None, "hora": None})
    return jsonify({"simbolo": simbolo, "fuente": "Tradier 15min",
                    "total": len(velas), "velas": velas, "senales_hoy": senales_hoy}), 200

@app.route("/status", methods=["GET"])
@require_admin
def system_status():
    ahora    = datetime.now(EST)
    hoy      = ahora.date()  # EST date — avoids UTC-off-by-one after midnight
    import threading
    threads_vivos = [t.name for t in threading.enumerate()]
    mercado_abierto = es_dia_mercado(ahora) and (570 <= ahora.hour * 60 + ahora.minute < 960)
    canales_resumen = {}
    for a in ACTIVOS:
        c = canal[a]
        canales_resumen[a] = {
            "on": c["on"], "tipo": "RCB" if (c["on"] and c.get("p3")) else "CNF" if c["on"] else "OFF",
            "p1": c["p1"]["high"] if c.get("p1") else None, "p2": c.get("p2_actual_high"),
        }
    señales_hoy = {}
    for a in ACTIVOS:
        ed = estado_dia.get(a, {})
        señales_hoy[a] = {
            "fecha": ed.get("fecha"), "señales_disparadas": ed.get("señales_disparadas", []),
            "total": len(ed.get("señales_disparadas", [])),
            "1VR": ed.get("vr1_fired", False), "RPG": ed.get("rpg_fired", False),
            "GNA": ed.get("gna_fired", False), "GBA": ed.get("gba_fired", False),
            "PM40": ed.get("pm40_fired", False), "4PS": ed.get("4ps_fired", False),
            "HED": ed.get("hed_fired", False), "CNF": ed.get("cnf_fired", False),
            "RCB": ed.get("rcb_fired", False),
        }
    if _portfolio is None:
        cargar_portfolio()
    pos_abiertas = len(_portfolio["posiciones"])
    derby = _portfolio.get("derby", _portfolio.get("reto", {}))
    caballos_vivos = [c for c in derby.get("caballos", []) if not c.get("eliminado")]
    reto_resumen = {
        "activo": derby.get("activo", False),
        "turno_actual": derby.get("turno_actual", 1),
        "caballos_vivos": len(caballos_vivos),
        "capital_total": round(sum(c["capital"] for c in caballos_vivos), 2),
        "ganador": derby.get("ganador"),
    }
    archivos_data = {}
    for fname in ["axis_canales.json", "axis_portfolio.json", "axis_ordenes.json", "axis_estado_dia.json"]:
        path = f"/data/{fname}"
        try:
            size = os.path.getsize(path)
            archivos_data[fname] = f"{size} bytes ✅"
        except:
            archivos_data[fname] = "NO ENCONTRADO ❌"
    velas_db = {}
    hoy_str  = hoy.strftime("%Y-%m-%d")
    for a in ACTIVOS:
        try:
            local      = cargar_velas_local(a)
            b15        = [b for b in local["barras"] if b.get("interval") == "15min"]
            b15_hoy    = [b for b in b15 if b["time"].startswith(hoy_str)]
            tiene_hoy  = bool(b15_hoy)
            ultima_15m = b15[-1]["time"] if b15 else "—"
            fecha_ultima = ultima_15m[:10] if ultima_15m != "—" else "—"
            # V7: 15:00–15:45 bars (hour == "15") for today
            v7_hoy     = [b for b in b15_hoy if b["time"][11:13] == "15"]
            v7_bars_n  = len(v7_hoy)
            es_mktday  = es_dia_mercado(ahora)
            velas_db[a] = {
                "barras_15min":       len(b15),
                "ultima_barra_15m":   ultima_15m,
                "fecha_ultima_barra": fecha_ultima,
                "tiene_hoy":          tiene_hoy,
                "v7_hoy_presente":    v7_bars_n > 0,
                "v7_hoy_completa":    v7_bars_n >= 4,
                "v7_bars":            v7_bars_n,
                "v7_bars_expected":   4,
                "status": "✅ OK" if (len(b15) > 100 and (tiene_hoy or not es_mktday)) else
                          "⚠️ SIN HOY" if (len(b15) > 100 and es_mktday) else "❌ VACÍO",
            }
        except Exception as e:
            velas_db[a] = {"status": f"❌ ERROR: {e}"}
    return jsonify({
        "sistema": f"AXIS Breakout Sentinel v{AXIS_VERSION}",
        "hora_est": ahora.strftime("%Y-%m-%d %H:%M:%S EST"),
        "mercado": "ABIERTO ✅" if mercado_abierto else "CERRADO ⏸",
        "threads": threads_vivos, "activos": ACTIVOS,
        "canales": canales_resumen, "señales_hoy": señales_hoy,
        "portfolio": {"posiciones_abiertas": pos_abiertas, "posiciones": _portfolio["posiciones"]},
        "reto": reto_resumen, "archivos_data": archivos_data, "velas_db": velas_db,
    }), 200

@app.route("/estadisticas", methods=["GET"])
@require_admin
def estadisticas():
    if _portfolio is None:
        cargar_portfolio()
    historial_total = _portfolio.get("historial", [])
    historial = [p for p in historial_total if not p.get("excluida_metricas")]
    excluidas_integridad = len(historial_total) - len(historial)
    if not historial:
        return jsonify({"mensaje": "Sin historial aún"}), 200
    from collections import defaultdict
    por_estrategia = defaultdict(lambda: {"total": 0, "wins": 0, "pl_usd": 0.0, "pl_pcts": []})
    por_activo     = defaultdict(lambda: {"total": 0, "wins": 0, "pl_usd": 0.0, "pl_pcts": []})
    pl_total = 0.0; wins_total = 0; total = len(historial); mejor_racha = 0; racha_actual = 0
    for pos in historial:
        pl_usd = pos.get("pl_usd", 0) or 0
        pl_pct = pos.get("pl_pct", 0) or 0
        es_win = pl_usd > 0
        strat  = pos.get("estrategia", "?")
        activo_p = pos.get("simbolo", "?")
        pl_total += pl_usd
        if es_win: wins_total += 1; racha_actual += 1; mejor_racha = max(mejor_racha, racha_actual)
        else: racha_actual = 0
        por_estrategia[strat]["total"] += 1; por_estrategia[strat]["pl_usd"] += pl_usd
        por_estrategia[strat]["pl_pcts"].append(pl_pct)
        if es_win: por_estrategia[strat]["wins"] += 1
        por_activo[activo_p]["total"] += 1; por_activo[activo_p]["pl_usd"] += pl_usd
        por_activo[activo_p]["pl_pcts"].append(pl_pct)
        if es_win: por_activo[activo_p]["wins"] += 1
    def resumen(d):
        return {"total": d["total"], "wins": d["wins"], "losses": d["total"] - d["wins"],
                "win_rate": f"{round(d['wins']/d['total']*100, 1)}%" if d["total"] else "—",
                "pl_usd": round(d["pl_usd"], 2)}
    return jsonify({
        "resumen_general": {"total_operaciones": total, "wins": wins_total, "losses": total - wins_total,
                            "win_rate": f"{round(wins_total/total*100, 1)}%" if total else "—",
                            "pl_total_usd": round(pl_total, 2), "mejor_racha": mejor_racha,
                            "excluidas_integridad": excluidas_integridad},
        "por_estrategia": {k: resumen(v) for k, v in sorted(por_estrategia.items())},
        "por_activo": {k: resumen(v) for k, v in sorted(por_activo.items())},
    }), 200

@app.route("/analisis", methods=["GET"])
def serve_analisis():
    from flask import Response
    html_path = os.path.join(os.path.dirname(__file__), "axis_analisis.html")
    if os.path.exists(html_path):
        with open(html_path, "r") as f:
            return Response(f.read(), mimetype="text/html")
    return Response("<h1>axis_analisis.html no encontrado</h1>", mimetype="text/html"), 404

@app.route("/analisis/data", methods=["GET"])
@require_admin
def analisis_data():
    if _portfolio is None:
        cargar_portfolio()
    return jsonify({
        "posiciones_abiertas": _portfolio["posiciones"],
        "historial": _portfolio["historial"],
        "total_abiertas": len(_portfolio["posiciones"]),
        "total_cerradas": len([p for p in _portfolio["historial"] if not p.get("excluida_metricas")]),
        "total_anuladas_integridad": len([p for p in _portfolio["historial"] if p.get("excluida_metricas")]),
    }), 200

@app.route("/cotizar_opciones", methods=["GET"])
@require_admin
def cotizar_opciones():
    from datetime import date, timedelta
    hoy = date.today()
    resultado = {}
    for simbolo in ACTIVOS:
        try:
            r0 = requests.get(f"{TRADIER_BASE_REAL}/markets/quotes", headers=TRADIER_HEADERS_REAL,
                              params={"symbols": simbolo, "greeks": "false"}, timeout=10)
            precio_actual = float(r0.json().get("quotes", {}).get("quote", {}).get("last", 0))
            if not precio_actual:
                resultado[simbolo] = {"error": "Sin precio"}
                continue
            r1 = requests.get(f"{TRADIER_BASE_REAL}/markets/options/expirations", headers=TRADIER_HEADERS_REAL,
                              params={"symbol": simbolo, "includeAllRoots": "true"}, timeout=10)
            fechas = r1.json().get("expirations", {}).get("date", [])
            if isinstance(fechas, str): fechas = [fechas]
            vencimiento = None
            for f in sorted(fechas):
                if (date.fromisoformat(f) - hoy).days >= 7:
                    vencimiento = f; break
            if not vencimiento:
                resultado[simbolo] = {"error": "Sin vencimiento"}
                continue
            pct = get_pct_otm(precio_actual)
            dist = round(precio_actual * pct / 100, 1)
            resultado[simbolo] = {"precio_actual": round(precio_actual, 2), "vencimiento": vencimiento,
                                   "dias_venc": (date.fromisoformat(vencimiento) - hoy).days, "pct_otm": f"{pct}%"}
        except Exception as e:
            resultado[simbolo] = {"error": str(e)}
    return jsonify(resultado), 200

@app.route("/diagnostico", methods=["GET"])
@require_admin
def diagnostico():
    from datetime import date as date_cls, datetime as dt2, timedelta
    from collections import defaultdict
    simbolo = request.args.get("simbolo", "SPY").upper()
    fecha   = request.args.get("fecha", date_cls.today().strftime("%Y-%m-%d"))
    reporte = {"simbolo": simbolo, "fecha": fecha, "velas": [], "señales": [], "log": []}
    log = reporte["log"]
    try:
        fecha_dt  = dt2.strptime(fecha, "%Y-%m-%d")
        fecha_ini = (fecha_dt - timedelta(days=10)).strftime("%Y-%m-%d")
        r = requests.get(f"{TRADIER_BASE_REAL}/markets/timesales", headers=TRADIER_HEADERS_REAL,
                         params={"symbol": simbolo, "interval": "15min",
                                 "start": f"{fecha_ini} 09:00", "end": f"{fecha} 16:30",
                                 "session_filter": "open"}, timeout=30)
        data   = r.json()
        series = data.get("series")
        barras = []
        if series and series != "null":
            barras = series.get("data", [])
            if isinstance(barras, dict): barras = [barras]
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    dias = defaultdict(lambda: defaultdict(list))
    for b in barras:
        ts  = b["time"].replace("T", " ")
        bdt = dt2.strptime(ts, "%Y-%m-%d %H:%M:%S")
        f   = bdt.strftime("%Y-%m-%d")
        h, m = bdt.hour, bdt.minute
        if h == 9 and m in (30, 45): dias[f]["V1"].append(b)
        elif h == 10: dias[f]["V2"].append(b)
        elif h == 11: dias[f]["V3"].append(b)
        elif h == 12: dias[f]["V4"].append(b)
        elif h == 13: dias[f]["V5"].append(b)
        elif h == 14: dias[f]["V6"].append(b)
        elif h == 15: dias[f]["V7"].append(b)
    def construir_vela(vnum, bs):
        if not bs: return None
        return {"vela": vnum, "open": round(float(bs[0]["open"]), 2),
                "high": round(max(float(b["high"]) for b in bs), 2),
                "low": round(min(float(b["low"]) for b in bs), 2),
                "close": round(float(bs[-1]["close"]), 2), "bars": len(bs)}
    fechas_ordenadas = sorted(dias.keys())
    v7_prev_close = None
    for f in fechas_ordenadas:
        if f < fecha:
            bs = dias[f].get("V7", [])
            if bs: v7_prev_close = round(float(bs[-1]["close"]), 2)
    velas_dia = {}
    for vnum in ["V1","V2","V3","V4","V5","V6","V7"]:
        v = construir_vela(vnum, dias.get(fecha, {}).get(vnum, []))
        if v: velas_dia[vnum] = v
    reporte["velas"] = list(velas_dia.values())
    reporte["v7_dia_anterior"] = v7_prev_close
    if not velas_dia:
        log.append("⚠️ Sin velas para esta fecha")
        return jsonify(reporte), 200
    v1 = velas_dia.get("V1")
    log.append("─── 1VR ───────────────────────────────")
    if v1:
        if v1["close"] < v1["open"]:
            log.append(f"✅ V1 ROJA — 1VR posible: O{v1['open']} C{v1['close']}")
        else:
            log.append(f"❌ V1 VERDE — 1VR NO dispara: O{v1['open']} C{v1['close']}")
    log.append("─── RPG ───────────────────────────────")
    if v1 and v7_prev_close:
        gap = round(abs(v1["open"] - v7_prev_close) / v7_prev_close * 100, 3)
        log.append(f"V7 anterior close: {v7_prev_close} | V1 open: {v1['open']} | gap={gap}%")
        log.append(f"Gap >= 0.5%: {'SI' if gap >= 0.5 else 'NO'} | V1 verde: {'SI' if v1['close'] > v1['open'] else 'NO'}")
    return jsonify(reporte), 200

@app.route("/precio", methods=["GET"])
@require_admin
def precio_rt():
    simbolo = request.args.get("simbolo", "SPY").upper()
    precio  = get_precio_tradier(simbolo)
    if precio:
        return jsonify({"simbolo": simbolo, "precio": precio}), 200
    return jsonify({"error": "No disponible"}), 500

@app.route("/canal_estado", methods=["GET"])
@require_admin
def canal_estado():
    simbolo = request.args.get("activo", "").upper()
    activos = [simbolo] if simbolo in ACTIVOS else ACTIVOS
    resultado = {}
    for a in activos:
        c = canal[a]
        ahora_dt = datetime.now(EST)
        techo = calcular_techo_canal(a, ahora_dt) if c["on"] else None
        piso_mitad = calcular_piso_mitad_canal(a, ahora_dt) if c["on"] and c["p3"] else (None, None)
        resultado[a] = {
            "on": c["on"], "apagado": c.get("apagado", False),
            "roto": c.get("roto", False), "fecha_ruptura": c.get("fecha_ruptura", None),
            "tipo": "RCB" if (c["on"] and c["p3"]) else ("CNF" if c["on"] else "---"),
            "p1": c["p1"], "p2": c["p2"], "p3": c["p3"],
            "techo": round(techo, 2) if techo else None,
            "mitad": round(piso_mitad[1], 2) if piso_mitad[1] else None,
            "piso": round(piso_mitad[0], 2) if piso_mitad[0] else None,
        }
    return jsonify(resultado), 200

@app.route("/canal_lineas", methods=["GET"])
@require_admin
def canal_lineas():
    simbolo = request.args.get("activo", "SPY").upper()
    if simbolo not in ACTIVOS:
        return jsonify({"error": "Activo no reconocido"}), 400
    c = canal[simbolo]
    if not c["on"] or not c["p1"] or not c["p2"]:
        return jsonify({"activo": simbolo, "on": False, "lineas": []}), 200
    velas = get_velas(simbolo, outputsize=280)
    if not velas:
        return jsonify({"error": "Sin velas"}), 500
    lineas = []
    fecha_p1 = c["p1"]["fecha"]
    hora_p1  = c["p1"]["hora_est"]
    for v in velas:
        try:
            v_fecha = v["datetime"][:10]
            v_hora  = int(v["datetime"][11:13])
            if v_fecha < fecha_p1: continue
            if v_fecha == fecha_p1 and v_hora < hora_p1: continue
            ahora_dt = datetime.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S")
            ahora_dt = EST.localize(ahora_dt)
            techo = calcular_techo_canal(simbolo, ahora_dt)
            piso, mitad = calcular_piso_mitad_canal(simbolo, ahora_dt)
            lineas.append({
                "datetime": v["datetime"], "vela": v["vela"],
                "techo": round(techo, 4) if techo else None,
                "mitad": round(mitad, 4) if mitad else None,
                "piso":  round(piso,  4) if piso  else None,
            })
        except:
            continue
    tipo = "RCB" if c["p3"] else "CNF"
    return jsonify({"activo": simbolo, "on": True, "tipo": tipo, "lineas": lineas}), 200

# ═══════════════════════════════════════════════════════════
# POLLING GTC Y VENCIMIENTO
# ═══════════════════════════════════════════════════════════
def get_estado_orden_tradier(orden_id):
    try:
        r = requests.get(f"{TRADIER_BASE}/accounts/{TRADIER_ACCOUNT}/orders/{orden_id}",
                         headers=TRADIER_HEADERS, timeout=10)
        if r.status_code != 200: return None
        orden = r.json().get("order", {})
        return {"status": orden.get("status"), "avg_fill_price": float(orden.get("avg_fill_price", 0) or 0)}
    except Exception as e:
        print(f"Error estado orden {orden_id}: {e}")
        return None

def _duracion_texto(minutos):
    minutos = int(minutos or 0)
    return f"{minutos//60}h {minutos%60}m" if minutos >= 60 else f"{minutos}m"

def registrar_fallo_seguimiento(pos, ahora, motivo="bid_no_disponible"):
    fallos = int(pos.get("fallos_seguimiento", 0) or 0) + 1
    pos["fallos_seguimiento"] = fallos
    pos["ts_ultimo_fallo_seguimiento"] = ahora.isoformat()
    interrupcion_registrada = bool(
        pos.get("fallo_seguimiento_registrado")
        or pos.get("fallo_seguimiento_notificado")
    )
    if fallos >= 3 and not interrupcion_registrada:
        pos["fallo_seguimiento_registrado"] = True
        pos["fallo_seguimiento_notificado"] = False
        actualizar_alerta(pos.get("alert_id"), evento="TRACKING_INTERRUPTED",
                          fallos_seguimiento=fallos, motivo_seguimiento=motivo)
        return True
    return False

def registrar_recuperacion_seguimiento(pos, ahora):
    estaba_interrumpido = bool(
        pos.get("fallo_seguimiento_registrado")
        or pos.get("fallo_seguimiento_notificado")
    )
    fallos = int(pos.get("fallos_seguimiento", 0) or 0)
    pos["fallos_seguimiento"] = 0
    pos["fallo_seguimiento_registrado"] = False
    pos["fallo_seguimiento_notificado"] = False
    if estaba_interrumpido:
        actualizar_alerta(pos.get("alert_id"), evento="TRACKING_RESTORED",
                          fallos_seguimiento=0, ts_seguimiento_restaurado=ahora.isoformat())
        return True
    return False

def actualizar_seguimiento_posicion(pos, bid, ahora=None):
    """AX-TRACK-002: actualiza una posición sin decidir cierres ni trading."""
    if ahora is None:
        ahora = datetime.now(EST)
    precio_entrada = float(pos.get("precio_entrada", 0) or 0)
    bid = float(bid or 0)
    if precio_entrada <= 0 or bid <= 0:
        return False
    try:
        ts_entrada = datetime.fromisoformat(str(pos.get("ts_entrada", "")).replace("Z", ""))
        if ts_entrada.tzinfo is None:
            ts_entrada = EST.localize(ts_entrada)
        minutos_abierta = max(0, int((ahora - ts_entrada).total_seconds() / 60))
    except Exception:
        minutos_abierta = int(pos.get("minutos_abierta", 0) or 0)

    contratos = int(pos.get("contratos", 1) or 1)
    pl_pct = round((bid - precio_entrada) / precio_entrada * 100, 2)
    pl_usd = round((bid - precio_entrada) * 100 * contratos, 2)
    mfe_anterior = float(pos.get("mfe_pct", pos.get("pl_pct_maximo", 0)) or 0)
    mae_anterior = float(pos.get("mae_pct", pos.get("pl_pct_minimo", 0)) or 0)
    mfe_pct = max(mfe_anterior, pl_pct)
    mae_pct = min(mae_anterior, pl_pct)

    pos["bid_actual"] = bid
    pos["pl_pct_actual"] = pl_pct
    pos["pl_usd_actual"] = pl_usd
    pos["mfe_pct"] = mfe_pct
    pos["mae_pct"] = mae_pct
    pos["pl_pct_maximo"] = mfe_pct
    pos["pl_pct_minimo"] = mae_pct
    pos["minutos_abierta"] = minutos_abierta
    pos["ts_ultimo_seguimiento"] = ahora.isoformat()
    if pl_pct > mfe_anterior or not pos.get("fecha_maximo"):
        pos["fecha_maximo"] = ahora.strftime("%Y-%m-%d")
    if pl_pct < mae_anterior or not pos.get("fecha_minimo"):
        pos["fecha_minimo"] = ahora.strftime("%Y-%m-%d")
    actualizar_salidas_sombra(pos, pl_pct, mfe_pct, ahora, minutos_abierta)
    pos.setdefault("seguimiento", []).append({
        "ts": ahora.isoformat(), "bid": bid, "pl_pct": pl_pct, "pl_usd": pl_usd,
    })
    actualizar_alerta(
        pos.get("alert_id"), evento=None,
        bid_actual=bid, pl_pct_actual=pl_pct, pl_usd_actual=pl_usd,
        mfe_pct=mfe_pct, mae_pct=mae_pct, minutos_abierta=minutos_abierta,
        ts_ultimo_seguimiento=ahora.isoformat(),
    )
    return True

VENCIMIENTO_CIERRE_MIN = 16 * 60 + 15

def posicion_debe_cerrar_por_vencimiento(pos, ahora):
    """True si el contrato ya venció o llegó a 16:15 EST en su fecha final."""
    try:
        from datetime import date as date_cls
        expiration = date_cls.fromisoformat(str(pos.get("expiration", "")))
        hoy = ahora.date()
        if expiration < hoy:
            return True
        minutos = ahora.hour * 60 + ahora.minute
        return expiration == hoy and minutos >= VENCIMIENTO_CIERRE_MIN
    except Exception as e:
        print(f"Error fecha vencimiento {pos.get('id', '?')}: {e}")
        return False

def precio_cierre_vencimiento(pos):
    """Mejor precio observable; evita imponer $0 si existe un bid reciente."""
    try:
        bid = get_bid_opcion_tradier(pos.get("option_symbol"))
        if bid and bid > 0:
            return float(bid)
    except Exception as e:
        print(f"Error bid al vencer {pos.get('id', '?')}: {e}")
    bid_actual = float(pos.get("bid_actual", 0) or 0)
    if bid_actual > 0:
        return bid_actual
    historial = pos.get("historial_precios", [])
    if historial:
        ultimo_bid = float(historial[-1].get("bid", 0) or 0)
        if ultimo_bid > 0:
            return ultimo_bid
    return 0.0

def reconciliar_posiciones_vencidas(ahora=None):
    """Cierra vencimientos pendientes aun fuera de horario o tras redeploy."""
    if ahora is None:
        ahora = datetime.now(EST)
    if _portfolio is None:
        return 0
    cerradas = 0
    for pos in list(_portfolio.get("posiciones", [])):
        if not posicion_debe_cerrar_por_vencimiento(pos, ahora):
            continue
        precio_cierre = precio_cierre_vencimiento(pos)
        if cerrar_posicion(pos["id"], precio_cierre, "vencimiento"):
            cerradas += 1
    if cerradas:
        print(f"Reconciliación vencimientos: {cerradas} posición(es) cerrada(s)")
    return cerradas

def loop_polling_posiciones():
    print("Thread polling posiciones iniciado...")
    while True:
        try:
            time.sleep(300)
            ahora = datetime.now(EST)
            reconciliar_posiciones_vencidas(ahora)
            if not es_dia_mercado(ahora): continue
            mins = ahora.hour * 60 + ahora.minute
            if not (570 <= mins <= 1020): continue
            if _portfolio is None: continue
            portfolio_actualizado = False
            for pos in list(_portfolio["posiciones"]):
                pos_id = pos["id"]
                try:
                    bid = get_bid_opcion_tradier(pos.get("option_symbol"))
                    if bid:
                        registrar_recuperacion_seguimiento(pos, ahora)
                    else:
                        registrar_fallo_seguimiento(pos, ahora)
                    if bid and actualizar_seguimiento_posicion(pos, bid, ahora):
                        portfolio_actualizado = True
                except Exception as e:
                    print(f"Error seguimiento {pos_id}: {e}")
                    registrar_fallo_seguimiento(pos, ahora, motivo=str(e))
                portfolio_actualizado = True
                gtc_id = pos.get("tradier_gtc_id")
                if not gtc_id: continue
                try:
                    estado = get_estado_orden_tradier(gtc_id)
                    if not estado: continue
                    if estado["status"] == "filled" and estado["avg_fill_price"] > 0:
                        cerrar_posicion(pos_id, estado["avg_fill_price"], "gtc")
                except Exception as e:
                    print(f"Error check GTC {pos_id}: {e}")
            if portfolio_actualizado:
                guardar_portfolio()
        except Exception as e:
            print(f"Error loop_polling_posiciones: {e}")

# ═══════════════════════════════════════════════════════════
# V7 ANTICIPADA
# ═══════════════════════════════════════════════════════════
ACTIVOS_V7_ANTICIPADA = list(ACTIVOS)
ACTIVOS_V7_ANTICIPADA_NOSPY = [s for s in ACTIVOS_V7_ANTICIPADA if s != "SPY"]
_v7_eval_origen = None  # "V7_ANTICIPADA_1558" | "V7_FINAL_1600" | None

def guardar_snapshot_precios(ahora):
    global _portfolio
    if _portfolio is None: cargar_portfolio()
    if not _portfolio["posiciones"]: return
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    for pos in _portfolio["posiciones"]:
        try:
            option_symbol = pos.get("option_symbol")
            precio_entrada = pos.get("precio_entrada", 0)
            if not option_symbol or not precio_entrada: continue
            bid = get_bid_opcion_tradier(option_symbol)
            if not bid or bid <= 0: continue
            actualizar_seguimiento_posicion(pos, bid, ahora)
            pl_pct = pos["pl_pct_actual"]
            historial = pos.get("historial_precios", [])
            fechas_existentes = [h["fecha"] for h in historial]
            if fecha_hoy not in fechas_existentes:
                historial.append({"fecha": fecha_hoy, "bid": bid, "pl_pct": pl_pct, "nota": "cierre"})
                pos["historial_precios"] = historial
        except Exception as e:
            print(f"Error snapshot {pos.get('option_symbol','?')}: {e}")
    guardar_portfolio()

def enviar_resumen_diario(ahora):
    try:
        if _portfolio is None: cargar_portfolio()
        fecha_hoy = ahora.strftime("%Y-%m-%d")
        señales_lineas = []
        for activo_s in ACTIVOS:
            ed = estado_dia.get(activo_s, {})
            if ed.get("fecha") != fecha_hoy: continue
            disparadas = ed.get("señales_disparadas", [])
            if disparadas:
                señales_lineas.append(f"  • {activo_s}: {', '.join(disparadas)}")
        cerradas_hoy = [p for p in _portfolio["historial"]
                         if not p.get("excluida_metricas") and str(p.get("ts_cierre", "")).startswith(fecha_hoy)]
        pl_dia = sum(p.get("pl_usd", 0) or 0 for p in cerradas_hoy)
        wins   = sum(1 for p in cerradas_hoy if (p.get("pl_usd", 0) or 0) > 0)
        reto   = _portfolio.get("derby", _portfolio.get("reto", {}))
        cap_reto = sum(c["capital"] for c in reto.get("caballos", []) if not c.get("eliminado"))
        vivos  = sum(1 for c in reto.get("caballos", []) if not c.get("eliminado"))
        historial_confirmado = [p for p in _portfolio["historial"] if not p.get("excluida_metricas")]
        hist_total = len(historial_confirmado)
        hist_wins  = sum(1 for p in historial_confirmado if (p.get("pl_usd", 0) or 0) > 0)
        wr = f"{round(hist_wins/hist_total*100,1)}%" if hist_total else "—"
        emoji_pl = "✅" if pl_dia >= 0 else "🔴"
        seguimiento_lineas = []
        posiciones_reporte = [(p, "ABIERTA") for p in _portfolio["posiciones"]]
        posiciones_reporte += [(p, "CERRADA") for p in cerradas_hoy]
        for p, estado_reporte in posiciones_reporte:
            pl_pct_reporte = p.get("pl_pct_actual", p.get("pl_pct", 0)) or 0
            pl_usd_reporte = p.get("pl_usd_actual", p.get("pl_usd", 0)) or 0
            seguimiento_lineas.append(
                f"• <b>{p.get('simbolo','?')} {p.get('tipo','')} ${p.get('strike',0):g}</b> "
                f"({p.get('estrategia','AXIS')}) — {estado_reporte}\n"
                f"  ID {p.get('alert_id') or 'LEGACY-' + p.get('id','?')} | "
                f"P&L {pl_pct_reporte:+.2f}% (${pl_usd_reporte:+.2f})\n"
                f"  MFE {p.get('mfe_pct',p.get('pl_pct_maximo',0)):+.2f}% | "
                f"MAE {p.get('mae_pct',p.get('pl_pct_minimo',0)):+.2f}% | "
                f"{_duracion_texto(p.get('minutos_abierta',0))}"
            )
        msg_general = (
            f"📊 <b>AXIS — Resumen {ahora.strftime('%m/%d/%Y')}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>Señales del día:</b>\n"
            + (("\n".join(señales_lineas) + "\n") if señales_lineas else "  Sin señales hoy\n")
            + f"\n<b>Operaciones cerradas hoy:</b> {len(cerradas_hoy)}"
            + (f" ({wins}W / {len(cerradas_hoy)-wins}L)" if cerradas_hoy else "")
            + f"\n{emoji_pl} <b>P&L del día:</b> ${pl_dia:+.2f}\n"
            f"<b>Win Rate global:</b> {wr} ({hist_wins}/{hist_total})\n\n"
            f"🏇 <b>Derby:</b> {'Activo' if reto['activo'] else 'Inactivo'}\n"
            f"  Caballos vivos: {vivos}/4 | Capital total: ${cap_reto:,.2f}\n\n"
            f"<i>AXIS v{AXIS_VERSION} | {ahora.strftime('%H:%M EST')}</i>"
        )
        enviar_telegram(msg_general)

        if not seguimiento_lineas:
            enviar_telegram("📈 <b>AXIS — Seguimiento diario:</b> sin posiciones monitoreadas")
        else:
            grupos = []
            grupo_actual = []
            longitud = 0
            for linea in seguimiento_lineas:
                if grupo_actual and longitud + len(linea) + 2 > 3400:
                    grupos.append(grupo_actual)
                    grupo_actual = []
                    longitud = 0
                grupo_actual.append(linea)
                longitud += len(linea) + 2
            if grupo_actual:
                grupos.append(grupo_actual)
            for idx, grupo in enumerate(grupos, 1):
                parte = f" ({idx}/{len(grupos)})" if len(grupos) > 1 else ""
                enviar_telegram(
                    f"📈 <b>AXIS — Seguimiento diario: {len(seguimiento_lineas)} posiciones{parte}</b>\n\n"
                    + "\n\n".join(grupo)
                )
    except Exception as e:
        print(f"Error enviar_resumen_diario: {e}")

# ═══════════════════════════════════════════════════════════
# AX-TUNE-001B — Daily Debrief  /  AX-FOCUS-001 — Focus Engine
# ═══════════════════════════════════════════════════════════
_CALL_TIPOS_DB = {"GNA", "GBA"}

def _tipo_corto_db(tipo):
    return (tipo or "").rstrip("+0123456789")

# AX-FOCUS-001: pesos por tipo de anomalía (0 = nunca afecta prioridad por señal)
_FOCUS_WEIGHTS = {
    "CONFLICTO_DIRECCION":   100,
    "MULTIPLES_ESTRATEGIAS":  80,
    "SEÑAL_TARDIA":           60,
    "SIMBOLO_SOBREACTIVO":    40,
    "ESTRATEGIA_DOMINANTE":    0,
}

def calcular_focus_scores(señales, anomalias):
    """
    Post-proceso puro: asigna score a cada señal según las anomalías que la afectan.
    No toca estrategias ni lógica de disparo.
    Retorna hasta 3 señales con score > 0, ordenadas por score desc.
    """
    scores   = [0]   * len(señales)
    motivos  = [[] for _ in señales]
    acciones = ["SIN_ACCION"] * len(señales)

    for a in anomalias:
        w = _FOCUS_WEIGHTS.get(a.get("tipo", ""), 0)
        if w == 0:
            continue
        accion = a.get("accion_recomendada", "SIN_ACCION")
        for idx, s in enumerate(señales):
            aplica = False
            tipo_a = a.get("tipo", "")
            if tipo_a in ("CONFLICTO_DIRECCION", "MULTIPLES_ESTRATEGIAS"):
                aplica = (s["simbolo"] == a.get("simbolo") and
                          (s.get("vela") or "?") == (a.get("vela") or "?"))
            elif tipo_a == "SIMBOLO_SOBREACTIVO":
                aplica = s["simbolo"] == a.get("simbolo")
            elif tipo_a == "SEÑAL_TARDIA":
                aplica = (s["simbolo"] == a.get("simbolo") and
                          s.get("vela") == a.get("vela") and
                          s.get("tipo") in (a.get("estrategias") or []))
            if aplica:
                scores[idx] += w
                motivos[idx].append(a.get("motivo_corto", ""))
                if accion == "REVISAR_GRAFICO":
                    acciones[idx] = "REVISAR_GRAFICO"
                elif accion == "MONITOREAR" and acciones[idx] == "SIN_ACCION":
                    acciones[idx] = "MONITOREAR"

    ranked = []
    for idx, s in enumerate(señales):
        if scores[idx] <= 0:
            continue
        sc = scores[idx]
        if sc >= 100:   est = 5
        elif sc >= 80:  est = 4
        elif sc >= 60:  est = 3
        elif sc >= 40:  est = 2
        else:           est = 1
        ranked.append({
            **s,
            "focus_score":    sc,
            "focus_estrellas": est,
            "focus_motivos":  list(dict.fromkeys(m for m in motivos[idx] if m)),
            "focus_accion":   acciones[idx],
        })

    ranked.sort(key=lambda x: -x["focus_score"])
    return ranked[:3]

def construir_debrief_data(fecha=None):
    """Payload completo del debrief para una fecha (default: hoy)."""
    ahora     = datetime.now(EST)
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    if fecha is None:
        fecha = fecha_hoy

    señales = []
    if fecha == fecha_hoy:
        # Fuente viva: estado_dia en proceso
        for sym in ACTIVOS:
            ed = estado_dia.get(sym, {})
            if ed.get("fecha") != fecha_hoy:
                continue
            disparadas = ed.get("señales_disparadas", [])
            detalle    = ed.get("señales_detalle", [])
            label_map  = {}
            for lbl in disparadas:
                for k in ("1VR","RPG","GNA","GBA","PM40","CNF","RCB","4PS","HED"):
                    if k in lbl.upper():
                        label_map[k] = lbl
                        break
            if detalle:
                for d in detalle:
                    tipo = d.get("tipo", "?")
                    señales.append({
                        "simbolo": sym, "tipo": tipo,
                        "label":  label_map.get(tipo, tipo),
                        "hora":   d.get("hora"), "vela": d.get("vela"),
                    })
            else:
                for lbl in disparadas:
                    for k in ("1VR","RPG","GNA","GBA","PM40","CNF","RCB","4PS","HED"):
                        if k in lbl.upper():
                            señales.append({"simbolo": sym, "tipo": k, "label": lbl,
                                            "hora": None, "vela": None})
                            break
    else:
        # Fuente histórica
        historial = cargar_señales_historicas()
        dia = historial.get(fecha, {})
        for sym in ACTIVOS:
            for s in dia.get(sym, []):
                if isinstance(s, str):
                    tipo, hora, vela = s, None, None
                else:
                    tipo = s.get("tipo", "?")
                    hora = s.get("hora")
                    vela = s.get("vela")
                señales.append({"simbolo": sym, "tipo": tipo, "label": tipo,
                                "hora": hora, "vela": vela})

    call_count = sum(1 for s in señales if _tipo_corto_db(s["tipo"]) in _CALL_TIPOS_DB)
    put_count  = len(señales) - call_count

    por_estrategia = {}
    por_simbolo    = {}
    for s in señales:
        base = _tipo_corto_db(s["tipo"])
        por_estrategia.setdefault(base, []).append(s["simbolo"])
        por_simbolo.setdefault(s["simbolo"], []).append(base)
    por_estrategia = dict(sorted(por_estrategia.items(), key=lambda x: -len(x[1])))
    por_simbolo    = {k: v for k, v in por_simbolo.items() if v}

    anomalias_list = detectar_anomalias_db(señales, por_simbolo, por_estrategia)
    return {
        "fecha":          fecha,
        "total_señales":  len(señales),
        "call_count":     call_count,
        "put_count":      put_count,
        "señales":        señales,
        "por_estrategia": por_estrategia,
        "por_simbolo":    por_simbolo,
        "anomalias":      anomalias_list,
        "focus":          calcular_focus_scores(señales, anomalias_list),
    }

def detectar_anomalias_db(señales, por_simbolo, por_estrategia):
    """AX-TUNE-002A: devuelve lista de dicts estructurados con prioridad/motivo/accion."""
    anomalias = []
    total = len(señales)

    by_sym_vela = {}
    for s in señales:
        key = (s["simbolo"], s.get("vela") or "?")
        by_sym_vela.setdefault(key, []).append(s)

    conflictos = set()

    # A. CONFLICTO_DIRECCION: mismo símbolo + misma vela con CALL y PUT
    for (sym, vela), grupo in by_sym_vela.items():
        tipos_base = [_tipo_corto_db(g["tipo"]) for g in grupo]
        if len(tipos_base) > 1 and any(t in _CALL_TIPOS_DB for t in tipos_base) and any(t not in _CALL_TIPOS_DB for t in tipos_base):
            conflictos.add((sym, vela))
            ests = [g["tipo"] for g in grupo]
            hora = next((g.get("hora") for g in grupo if g.get("hora")), None)
            anomalias.append({
                "tipo":               "CONFLICTO_DIRECCION",
                "prioridad":          "ALTA",
                "simbolo":            sym,
                "vela":               vela,
                "hora":               hora,
                "estrategias":        ests,
                "motivo_corto":       f"CALL y PUT en {sym} {vela}",
                "motivo_detallado":   f"{', '.join(ests)} generaron señales con direcciones opuestas en la misma vela. El motor no puede determinar dirección.",
                "accion_recomendada": "REVISAR_GRAFICO",
            })

    # B. MULTIPLES_ESTRATEGIAS: mismo símbolo + misma vela, 2+ estrategias (sin conflicto)
    for (sym, vela), grupo in by_sym_vela.items():
        if len(grupo) >= 2 and (sym, vela) not in conflictos:
            ests = [g["tipo"] for g in grupo]
            hora = next((g.get("hora") for g in grupo if g.get("hora")), None)
            anomalias.append({
                "tipo":               "MULTIPLES_ESTRATEGIAS",
                "prioridad":          "MEDIA",
                "simbolo":            sym,
                "vela":               vela,
                "hora":               hora,
                "estrategias":        ests,
                "motivo_corto":       f"{len(ests)} estrategias en {sym} {vela}",
                "motivo_detallado":   f"{', '.join(ests)} coincidieron en {sym} {vela}. Confluencia de señales en la misma apertura horaria.",
                "accion_recomendada": "REVISAR_GRAFICO",
            })

    # C. SIMBOLO_SOBREACTIVO: símbolo con 3+ señales en el día
    for sym, tipos in por_simbolo.items():
        if len(tipos) >= 3:
            anomalias.append({
                "tipo":               "SIMBOLO_SOBREACTIVO",
                "prioridad":          "MEDIA",
                "simbolo":            sym,
                "vela":               None,
                "hora":               None,
                "estrategias":        tipos,
                "motivo_corto":       f"{sym} acumuló {len(tipos)} señales",
                "motivo_detallado":   f"{sym} disparó {', '.join(tipos)} en el mismo día. Alta frecuencia puede indicar volatilidad extrema o acumulación de falsos positivos.",
                "accion_recomendada": "MONITOREAR",
            })

    # D. ESTRATEGIA_DOMINANTE: estrategia >=50% de señales del día
    if total >= 2:
        for tipo, syms in por_estrategia.items():
            pct = len(syms) / total * 100
            if pct >= 50:
                anomalias.append({
                    "tipo":               "ESTRATEGIA_DOMINANTE",
                    "prioridad":          "BAJA",
                    "simbolo":            None,
                    "vela":               None,
                    "hora":               None,
                    "estrategias":        [tipo],
                    "motivo_corto":       f"{tipo} en {pct:.0f}% de señales",
                    "motivo_detallado":   f"{tipo} se disparó en {len(syms)}/{total} señales del día ({pct:.0f}%). Posible sesgo sistémico o condición de mercado uniforme.",
                    "accion_recomendada": "MONITOREAR",
                })

    # E. SEÑAL_TARDIA: V6 (V7 se evalúa siempre por la ruta anticipada — no es tardía)
    for s in señales:
        if s.get("vela") == "V6":
            anomalias.append({
                "tipo":               "SEÑAL_TARDIA",
                "prioridad":          "BAJA",
                "simbolo":            s["simbolo"],
                "vela":               s.get("vela"),
                "hora":               s.get("hora"),
                "estrategias":        [s["tipo"]],
                "motivo_corto":       f"Señal tardía {s['simbolo']} {s.get('vela', '?')}",
                "motivo_detallado":   f"{s['simbolo']} {s['tipo']} se disparó en {s.get('vela','?')} ({s.get('hora') or '?'}). Las señales en velas tardías tienen menor ventana de acción.",
                "accion_recomendada": "MONITOREAR",
            })

    return anomalias

def enviar_daily_debrief(force=False):
    """Envía el debrief a Telegram. Evita duplicados salvo force=True."""
    try:
        ahora     = datetime.now(EST)
        fecha_hoy = ahora.strftime("%Y-%m-%d")

        # Evitar duplicado
        if not force:
            try:
                with open(DEBRIEF_FILE, "r") as f:
                    ultimo = json.load(f).get("ultimo_debrief", "")
            except Exception:
                ultimo = ""
            if ultimo == fecha_hoy:
                print(f"Debrief ya enviado hoy ({fecha_hoy}) — omitido")
                return

        data = construir_debrief_data(fecha_hoy)

        lineas_est = "\n".join(
            f"  {tipo}: {len(syms)}"
            for tipo, syms in list(data["por_estrategia"].items())[:6]
        ) or "  Sin señales"
        lineas_sym = "\n".join(
            f"  {sym}: {', '.join(tipos)}"
            for sym, tipos in data["por_simbolo"].items()
        ) or "  Sin señales"
        anomalias_txt = ""
        alta_media = [a for a in data["anomalias"] if a.get("prioridad") in ("ALTA", "MEDIA")]
        if alta_media:
            items = "\n".join(
                f"{i+1}. [{a['prioridad']}] {a['motivo_corto']}"
                for i, a in enumerate(alta_media[:5])
            )
            anomalias_txt = f"\n\n🔍 <b>Señales que merecen tu atención ({len(alta_media)}):</b>\n{items}"

        msg = (
            f"📊 <b>AXIS DAILY DEBRIEF</b>\n"
            f"<b>Fecha:</b> {fecha_hoy}\n"
            f"<b>Total señales:</b> {data['total_señales']}\n"
            f"<b>CALL:</b> {data['call_count']}  |  <b>PUT:</b> {data['put_count']}\n\n"
            f"<b>Por estrategia:</b>\n{lineas_est}\n\n"
            f"<b>Por símbolo:</b>\n{lineas_sym}"
            f"{anomalias_txt}\n\n"
            f"🔗 <a href='https://web-production-bf9d0.up.railway.app/daily_debrief'>Ver reporte completo</a>"
        )
        enviar_telegram(msg)

        with open(DEBRIEF_FILE, "w") as f:
            json.dump({"ultimo_debrief": fecha_hoy, "ts": ahora.isoformat()}, f)
        print(f"Daily debrief enviado: {fecha_hoy}")
    except Exception as e:
        print(f"Error enviar_daily_debrief: {e}")

def loop_v7_anticipada():
    """Thread V7 anticipada:
    - 3:58–3:59 PM : V7 PROVISIONAL para los 7 activos no-SPY (retry cada 30s
                     hasta 15:59:30). HED para todos los activos (una sola vez).
    - 4:01 PM      : avisa omisiones de V7 provisional (Telegram único);
                     corrige cierre V7 final para todos los activos.
    - 4:01–4:13 PM : reintenta evaluar SPY con V7 final cada 30s.
                     Avisa una sola vez si hay espera.
    - Cierre diario: cuando SPY está listo O a las 4:14. Ejecuta una sola vez.
    v8.88"""
    print("Thread V7 anticipada iniciado...")
    ejecutado_358 = set(); ejecutado_400 = set()
    fecha_actual = None
    while True:
        try:
            ahora     = datetime.now(EST)
            fecha_hoy = ahora.strftime("%Y-%m-%d")
            if fecha_hoy != fecha_actual:
                fecha_actual = fecha_hoy
                ejecutado_358 = set(); ejecutado_400 = set()
            if es_dia_mercado(ahora):
                # ── 3:58–3:59 PM — V7 provisional + HED ─────────────────────
                # Ventana: 15:58:00–15:59:30 (4 ticks de 30s). HED solo una vez
                # por símbolo; V7 se reintenta en cada tick hasta éxito.
                if ahora.hour == 15 and ahora.minute in (58, 59):
                    # HED: ejecutar una sola vez por símbolo dentro de la ventana
                    for simbolo in ACTIVOS_V7_ANTICIPADA_NOSPY:
                        if f"hed_{simbolo}" not in ejecutado_358:
                            evaluar_hed(simbolo)
                            ejecutado_358.add(f"hed_{simbolo}")
                    if "hed_spy" not in ejecutado_358:
                        evaluar_hed("SPY")
                        ejecutado_358.add("hed_spy")
                    # V7 provisional: reintentar cada tick hasta que True
                    for simbolo in ACTIVOS_V7_ANTICIPADA_NOSPY:
                        if simbolo not in ejecutado_358:
                            if evaluar_v7_anticipada(simbolo):
                                ejecutado_358.add(simbolo)

                # ── 4:01 PM — Omisiones + corrección V7 final ────────────────
                if ahora.hour == 16 and ahora.minute == 1:
                    # Telegram único si algún símbolo no pudo evaluarse
                    if "v7_358_omitidos" not in ejecutado_400:
                        ejecutado_400.add("v7_358_omitidos")
                        omitidos = [s for s in ACTIVOS_V7_ANTICIPADA_NOSPY
                                    if s not in ejecutado_358]
                        if omitidos:
                            enviar_telegram(
                                f"⚠️ <b>AXIS</b> — V7 provisional omitida para: "
                                f"{', '.join(omitidos)}. Datos incompletos en "
                                f"ventana 3:58–3:59."
                            )
                    for simbolo in ACTIVOS_V7_ANTICIPADA:
                        if simbolo not in ejecutado_400:
                            corregir_cierre_v7(simbolo); ejecutado_400.add(simbolo)

                # ── 4:01–4:13 — Espera SPY V7 final, reintento cada 30s ──────
                if ahora.hour == 16 and 1 <= ahora.minute <= 13:
                    if "spy_final" not in ejecutado_400:
                        if evaluar_v7_final_spy():
                            ejecutado_400.add("spy_final")
                        elif "spy_wait_notified" not in ejecutado_400:
                            enviar_telegram(
                                "⏳ <b>AXIS</b> — Esperando V7 final de SPY "
                                "antes de cerrar el reporte diario."
                            )
                            ejecutado_400.add("spy_wait_notified")

                # ── Cierre diario: SPY listo O ventana agotada (≥ 4:14) ───────
                _spy_done   = "spy_final" in ejecutado_400
                _ventana_ok = ahora.hour == 16 and ahora.minute >= 14
                if (_spy_done or _ventana_ok) and "cierre_diario" not in ejecutado_400:
                    ejecutado_400.add("cierre_diario")
                    if _spy_done and "spy_wait_notified" in ejecutado_400:
                        enviar_telegram(
                            "✅ <b>AXIS</b> — V7 final de SPY confirmada. "
                            "Evaluación y cierre diario completados."
                        )
                    elif not _spy_done:
                        enviar_telegram(
                            "⚠️ <b>AXIS</b> — V7 final de SPY no estuvo disponible "
                            "antes del límite operativo. SPY fue omitido del cierre "
                            "de hoy por datos incompletos."
                        )
                    fecha_cierre = ahora.strftime("%Y-%m-%d")
                    for simbolo_daily in ACTIVOS:
                        try:
                            agregar_barra_diaria(simbolo_daily, fecha_cierre)
                        except Exception as e:
                            print(f"Error agregando barra diaria {simbolo_daily}: {e}")
                    guardar_snapshot_precios(ahora)
                    archivar_señales_dia(fecha_cierre)
                    enviar_resumen_diario(ahora)
                    enviar_daily_debrief()

            time.sleep(30)
        except Exception as e:
            print(f"Error loop V7 anticipada: {e}")
            time.sleep(30)

def construir_v7_provisional(simbolo, ahora):
    """Construye una V7 PROVISIONAL para evaluacion anticipada a las 3:58 PM
    usando exactamente 3 barras 15min (15:00/15:15/15:30) + 13 barras 1min
    (15:45–15:57). Rechaza la construccion si falta cualquier pieza, hay
    duplicados, barras fuera de rango o campos OHLC invalidos.
    Retorna un dict con bars=16/bars_expected=16, o None si falla validacion.
    v8.87"""
    hoy_str = ahora.strftime("%Y-%m-%d")

    ESPERADAS_15 = ["15:00", "15:15", "15:30"]
    ESPERADAS_1  = ["15:45", "15:46", "15:47", "15:48", "15:49", "15:50",
                    "15:51", "15:52", "15:53", "15:54", "15:55", "15:56", "15:57"]

    def ts_hhmm(b):
        t = b.get("time", "")
        return t[11:16] if len(t) >= 16 else ""

    def ohlc_valido(b):
        for campo in ("open", "high", "low", "close"):
            try:
                float(b[campo])
            except (KeyError, TypeError, ValueError):
                return False
        return True

    try:
        r15 = requests.get(
            f"{TRADIER_BASE_REAL}/markets/timesales",
            headers=TRADIER_HEADERS_REAL,
            params={
                "symbol": simbolo, "interval": "15min",
                "start": f"{hoy_str} 15:00", "end": f"{hoy_str} 15:44",
                "session_filter": "open",
            },
            timeout=15
        )
        barras_15 = []
        if r15.status_code == 200:
            s15 = r15.json().get("series")
            if s15 and s15 != "null":
                b15 = s15.get("data", [])
                if isinstance(b15, dict): b15 = [b15]
                barras_15 = b15

        r1 = requests.get(
            f"{TRADIER_BASE_REAL}/markets/timesales",
            headers=TRADIER_HEADERS_REAL,
            params={
                "symbol": simbolo, "interval": "1min",
                "start": f"{hoy_str} 15:45", "end": f"{hoy_str} 15:57",
                "session_filter": "open",
            },
            timeout=15
        )
        barras_1 = []
        if r1.status_code == 200:
            s1 = r1.json().get("series")
            if s1 and s1 != "null":
                b1 = s1.get("data", [])
                if isinstance(b1, dict): b1 = [b1]
                barras_1 = b1

        # Sort explícito — no dependemos del orden de la respuesta Tradier
        barras_15 = sorted(barras_15, key=lambda b: b.get("time", ""))
        barras_1  = sorted(barras_1,  key=lambda b: b.get("time", ""))

        # Validar timestamps exactos: count + valores + orden + sin duplicados
        ts15 = [ts_hhmm(b) for b in barras_15]
        ts1  = [ts_hhmm(b) for b in barras_1]

        if ts15 != ESPERADAS_15:
            print(f"{simbolo} V7 provisional RECHAZADA: 15min esperadas {ESPERADAS_15} obtenidas {ts15}")
            return None
        if ts1 != ESPERADAS_1:
            print(f"{simbolo} V7 provisional RECHAZADA: 1min esperadas {ESPERADAS_1} obtenidas {ts1}")
            return None

        # Validar OHLC de cada barra
        for b in barras_15 + barras_1:
            if not ohlc_valido(b):
                print(f"{simbolo} V7 provisional RECHAZADA: OHLC invalido en barra {b.get('time','?')}")
                return None

        # Las 16 piezas están validadas y ordenadas
        todas    = barras_15 + barras_1        # [15:00 15min … 15:57 1min]
        v7_open  = float(todas[0]["open"])     # open de la barra 15:00 15min
        v7_high  = max(float(b["high"]) for b in todas)
        v7_low   = min(float(b["low"])  for b in todas)
        v7_close = float(todas[-1]["close"])   # close de la barra 15:57 1min

        print(f"{simbolo} V7 PROVISIONAL OK (3x15min + 13x1min) "
              f"O:{v7_open:.2f} H:{v7_high:.2f} L:{v7_low:.2f} C:{v7_close:.2f}")

        return {
            "datetime":      f"{hoy_str} 15:00:00",
            "open":          str(round(v7_open, 4)),
            "high":          str(round(v7_high, 4)),
            "low":           str(round(v7_low, 4)),
            "close":         str(round(v7_close, 4)),
            "vela":          "V7",
            "completa":      False,
            "bars":          16,
            "bars_expected": 16,
            "origen":        "V7_ANTICIPADA_1558",
        }
    except Exception as e:
        print(f"Error construyendo V7 provisional {simbolo}: {e}")
        return None

def evaluar_v7_anticipada(simbolo):
    """Evalua estrategias usando una V7 PROVISIONAL (3:58–3:59 PM).
    Retorna True si evaluar_activo() se ejecutó con éxito.
    Retorna False en cualquier otro caso (sin velas, sin provisional, excepción).
    No envía Telegram ni duerme — el loop gestiona reintentos y notificaciones.
    v8.88"""
    global _v7_eval_origen
    ahora = datetime.now(EST)
    print(f"V7 anticipada {simbolo} — {ahora.strftime('%H:%M:%S EST')}")
    try:
        velas = get_velas(simbolo, outputsize=50)
        if not velas:
            print(f"{simbolo} V7 anticipada: sin datos de velas")
            return False

        v7_provisional = construir_v7_provisional(simbolo, ahora)
        if not v7_provisional:
            return False

        fecha_hoy_str = ahora.strftime("%Y-%m-%d")
        velas_con_provisional = [v for v in velas if not (v.get("vela") == "V7" and v["datetime"].startswith(fecha_hoy_str))]
        velas_con_provisional.insert(0, v7_provisional)

        _v7_eval_origen = "V7_ANTICIPADA_1558"
        evaluar_activo(simbolo, velas_con_provisional, ahora.replace(hour=16, minute=1))
        return True
    except Exception as e:
        print(f"Error V7 anticipada {simbolo}: {e}")
        return False
    finally:
        _v7_eval_origen = None


def evaluar_v7_final_spy():
    """Evalúa SPY con su V7 FINAL real (4 barras 15min completas).
    Retorna True si la evaluación se completó con éxito.
    Retorna False en cualquier otro caso (velas ausentes, V7 incompleta,
    excepción) — el loop gestiona el reintento y los mensajes de estado,
    de modo que esta función NO envía Telegram propia para evitar spam."""
    global _v7_eval_origen
    ahora = datetime.now(EST)
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    try:
        velas = get_velas("SPY", outputsize=50)
        if not velas:
            print("SPY V7 final: sin datos de velas — reintentando en 30s")
            return False

        # Guard: V7 de hoy con completa=True y al menos 4 barras
        v7_hoy = next(
            (v for v in velas
             if v.get("vela") == "V7"
             and v["datetime"].startswith(fecha_hoy)
             and v.get("completa") is True
             and v.get("bars", 0) >= 4),
            None
        )
        if v7_hoy is None:
            bars = next(
                (v.get("bars", 0) for v in velas
                 if v.get("vela") == "V7" and v["datetime"].startswith(fecha_hoy)),
                0
            )
            print(f"SPY V7 final aún no completa ({bars}/4 barras) — reintentando en 30s")
            return False

        print(f"SPY V7 final lista ({v7_hoy.get('bars','?')}/4 barras) — evaluando estrategias")
        _v7_eval_origen = "V7_FINAL_1600"
        evaluar_activo("SPY", velas, ahora.replace(hour=16, minute=1))
        return True
    except Exception as e:
        print(f"Error V7 final SPY: {e}")
        return False
    finally:
        _v7_eval_origen = None

def corregir_cierre_v7(simbolo):
    print(f"Correccion cierre V7 {simbolo} — {datetime.now(EST).strftime('%H:%M EST')}")
    try:
        velas = get_velas(simbolo, outputsize=10)
        if not velas: return
        fecha_hoy = datetime.now(EST).strftime("%Y-%m-%d")
        for v in velas:
            if v["datetime"].startswith(fecha_hoy) and int(v["datetime"][11:13]) == 15:
                estado_dia[simbolo]["v7_ayer_close"] = float(v["close"])
                print(f"Correccion V7 {simbolo}: ${float(v['close']):.2f} registrado")
                return
    except Exception as e:
        print(f"Error correccion V7 {simbolo}: {e}")

def evaluar_hed(simbolo):
    try:
        ed = estado_dia.get(simbolo, {})
        if ed.get("hed_fired"):
            return
        velas = get_velas(simbolo, outputsize=2)
        if not velas: return
        v = velas[-1]
        v_open = float(v["open"]); v_close = float(v["close"])
        v_high = float(v["high"]); v_low   = float(v["low"])
        cuerpo   = abs(v_close - v_open)
        mecha_sup = v_high - max(v_close, v_open)
        mecha_inf = min(v_close, v_open) - v_low
        rango    = v_high - v_low
        if cuerpo <= 0 or rango <= 0: return
        es_shooting_star = (mecha_sup >= 1.25 * cuerpo and mecha_inf <= 0.25 * cuerpo)
        if not es_shooting_star: return
        velas_hist = get_velas(simbolo, outputsize=60)
        closes = [float(x["close"]) for x in velas_hist]
        sma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
        sma40 = sum(closes[-40:]) / 40 if len(closes) >= 40 else None
        cond_a = sma20 and sma40 and sma20 > sma40
        ahora_dt = datetime.now(EST)
        techo_h  = calcular_techo_canal(simbolo, ahora_dt)
        _, mitad_h = calcular_piso_mitad_canal(simbolo, ahora_dt)
        c_hed = canal[simbolo]
        zona_30_h = None
        if techo_h and mitad_h:
            zona_30_h = techo_h - (techo_h - mitad_h) * 0.30
        cond_b = (c_hed["on"] and not c_hed["apagado"] and c_hed["p3"] is not None
                  and techo_h is not None and zona_30_h is not None
                  and zona_30_h <= v_close <= techo_h)
        if not (cond_a or cond_b): return
        alert_id = crear_alerta(
            simbolo, "HED — SHOOTING STAR DIARIA", "PUT", v_close,
            hora_label=ahora_dt.strftime("%H:%M EST"), origen="HED_AUTO",
        )
        precio_actual = get_precio_tradier(simbolo) or v_close
        opcion = get_opcion_tradier(simbolo, "put", precio_actual)
        if not opcion:
            enviar_telegram(f"⚠️ <b>HED {simbolo}</b> — Shooting star detectada pero sin opción disponible")
            actualizar_alerta(alert_id, "CANCELLED", "NO_OPTION_AVAILABLE",
                              decision="AUTO", motivo_cancelacion="tradier_sin_opcion")
            return
        opcion["subyacente"] = simbolo
        resultado = ejecutar_orden_tradier(opcion)
        cond_str = "RCB 30%" if cond_b else f"SMA20({sma20:.2f})>SMA40({sma40:.2f})"
        pos = registrar_ejecucion_confirmada(
            resultado, opcion, "HED — SHOOTING STAR DIARIA", alert_id, "AUTO",
        )
        if pos:
            registrar_senal_disparada(simbolo, "HED — SHOOTING STAR DIARIA")
            gtc_texto = (
                f"GTC: ${resultado['precio_venta']:.2f}"
                if resultado.get("venta_ok")
                else f"GTC PENDIENTE — {resultado.get('venta_error', 'sin confirmación')}"
            )
            enviar_telegram(
                f"🕯 <b>HED — SHOOTING STAR DIARIA</b>\n"
                f"<b>Activo:</b> {simbolo} | <b>Condición:</b> {cond_str}\n"
                f"<b>Alert ID:</b> {alert_id}\n"
                f"<b>Mecha:</b> {mecha_sup:.2f} / <b>Cuerpo:</b> {cuerpo:.2f} = {mecha_sup/cuerpo:.2f}×\n"
                f"✅ <b>COMPRA CONFIRMADA</b> | ID: {resultado['id']} | {gtc_texto}"
            )
        else:
            enviar_telegram(f"⚠️ <b>HED {simbolo}</b> — compra no confirmada: {resultado.get('error','?')}")
    except Exception as e:
        print(f"Error evaluar_hed {simbolo}: {e}")

# ═══════════════════════════════════════════════════════════
# DAILY DEBRIEF — AX-TUNE-001B
# ═══════════════════════════════════════════════════════════
@app.route("/daily_debrief", methods=["GET"])
def serve_daily_debrief():
    from flask import Response
    html_path = os.path.join(os.path.dirname(__file__), "axis_debrief.html")
    if os.path.exists(html_path):
        with open(html_path, "r") as f:
            return Response(f.read(), mimetype="text/html")
    return Response("<h1>axis_debrief.html no encontrado</h1>", mimetype="text/html"), 404

@app.route("/daily_debrief/data", methods=["GET"])
@require_admin
def daily_debrief_data():
    fecha = request.args.get("fecha", datetime.now(EST).strftime("%Y-%m-%d"))
    return jsonify(construir_debrief_data(fecha)), 200

@app.route("/daily_debrief/send", methods=["POST"])
@require_admin
def daily_debrief_send():
    force = request.args.get("force", "0") == "1"
    if force:
        try:
            with open(DEBRIEF_FILE, "w") as f:
                json.dump({"ultimo_debrief": ""}, f)
        except Exception:
            pass
    enviar_daily_debrief(force=force)
    return jsonify({"ok": True, "mensaje": "Debrief enviado"}), 200

# ═══════════════════════════════════════════════════════════
# AX-TUNE-003 — Signal Journal v1
# ═══════════════════════════════════════════════════════════

def cargar_journal():
    try:
        with open(JOURNAL_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"entries": []}

def guardar_journal(data):
    os.makedirs(os.path.dirname(JOURNAL_FILE), exist_ok=True)
    with open(JOURNAL_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route("/journal", methods=["GET"])
def serve_journal():
    from flask import Response
    html_path = os.path.join(os.path.dirname(__file__), "axis_journal.html")
    if os.path.exists(html_path):
        with open(html_path, "r") as f:
            return Response(f.read(), mimetype="text/html")
    return Response("<h1>axis_journal.html no encontrado</h1>", mimetype="text/html"), 404

@app.route("/alerts/data", methods=["GET"])
@require_admin
def alerts_data():
    """AX-TRACK-001: consulta de solo lectura del ciclo de alertas."""
    alertas = listar_alertas(
        alert_id=request.args.get("alert_id"),
        fecha=request.args.get("fecha"),
        simbolo=request.args.get("simbolo"),
        estrategia=request.args.get("estrategia"),
        estado=request.args.get("estado"),
    )
    limite = min(max(request.args.get("limit", 500, type=int), 1), 5000)
    return jsonify({"alertas": list(reversed(alertas[-limite:])), "total": len(alertas)}), 200

@app.route("/journal/data", methods=["GET"])
@require_admin
def journal_data():
    data = cargar_journal()
    entries = data.get("entries", [])
    simbolo    = request.args.get("simbolo", "").upper()
    estrategia = request.args.get("estrategia", "").upper()
    decision   = request.args.get("decision", "").upper()
    fecha      = request.args.get("fecha", "")
    if simbolo:
        entries = [e for e in entries if e.get("simbolo", "").upper() == simbolo]
    if estrategia:
        entries = [e for e in entries if e.get("estrategia", "").upper() == estrategia]
    if decision:
        entries = [e for e in entries if e.get("decision", "").upper() == decision]
    if fecha:
        entries = [e for e in entries if e.get("fecha", "") == fecha]
    return jsonify({"entries": list(reversed(entries)), "total": len(entries)}), 200

@app.route("/journal/save", methods=["POST"])
@require_admin
def journal_save():
    try:
        body = request.get_json(force=True)
        required = ["fecha", "simbolo", "estrategia", "direccion", "calificacion", "decision"]
        for field in required:
            if not body.get(field):
                return jsonify({"ok": False, "error": f"Campo requerido: {field}"}), 400
        entry = {
            "fecha":        body.get("fecha", ""),
            "simbolo":      (body.get("simbolo", "") or "").upper()[:10],
            "estrategia":   (body.get("estrategia", "") or "").upper()[:10],
            "direccion":    (body.get("direccion", "") or "").upper()[:4],
            "vela":         (body.get("vela", "") or "")[:3],
            "precio":       float(body["precio"]) if body.get("precio") not in (None, "") else None,
            "prioridad":    (body.get("prioridad", "NORMAL") or "NORMAL").upper()[:6],
            "motivo":       (body.get("motivo", "") or "")[:280],
            "calificacion": int(body.get("calificacion", 3)),
            "decision":     (body.get("decision", "") or "").upper()[:12],
            "comentario":   (body.get("comentario", "") or "")[:280],
            "ts_revision":  datetime.now(EST).isoformat(),
        }
        data = cargar_journal()
        data.setdefault("entries", []).append(entry)
        guardar_journal(data)
        return jsonify({"ok": True, "total": len(data["entries"])}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ═══════════════════════════════════════════════════════════
# AX-TUNE-004 — Success Rate Engine v1
# ═══════════════════════════════════════════════════════════

@app.route("/success_rate", methods=["GET"])
def serve_success_rate():
    from flask import Response
    html_path = os.path.join(os.path.dirname(__file__), "axis_success_rate.html")
    if os.path.exists(html_path):
        with open(html_path, "r") as f:
            return Response(f.read(), mimetype="text/html")
    return Response("<h1>axis_success_rate.html no encontrado</h1>", mimetype="text/html"), 404

@app.route("/success_rate/data", methods=["GET"])
@require_admin
def success_rate_data():
    entries = cargar_journal().get("entries", [])
    total   = len(entries)

    def _pct(n, t):  return round(n / t * 100, 1) if t > 0 else 0
    def _avg(group):
        vals = [e.get("calificacion", 3) for e in group if e.get("calificacion")]
        return round(sum(vals) / len(vals), 2) if vals else 0.0
    def _stats(group):
        t   = len(group)
        k   = sum(1 for e in group if e.get("decision") == "KEEP")
        tu  = sum(1 for e in group if e.get("decision") == "TUNE")
        inv = sum(1 for e in group if e.get("decision") == "INVESTIGATE")
        return {
            "total":        t,
            "keep":         k,  "keep_pct":    _pct(k,   t),
            "tune":         tu, "tune_pct":    _pct(tu,  t),
            "investigate":  inv,"invest_pct":  _pct(inv, t),
            "avg_estrellas": _avg(group),
        }

    # Por estrategia
    por_est = {}
    for e in entries:
        por_est.setdefault(e.get("estrategia", "?"), []).append(e)
    estrategias = [
        {"estrategia": k, **_stats(v)}
        for k, v in sorted(por_est.items(), key=lambda x: -len(x[1]))
    ]

    # Por símbolo
    por_sym = {}
    for e in entries:
        por_sym.setdefault(e.get("simbolo", "?"), []).append(e)
    simbolos = [
        {"simbolo": k, **_stats(v)}
        for k, v in sorted(por_sym.items(), key=lambda x: -len(x[1]))
    ]

    keep  = sum(1 for e in entries if e.get("decision") == "KEEP")
    tune  = sum(1 for e in entries if e.get("decision") == "TUNE")
    inv   = sum(1 for e in entries if e.get("decision") == "INVESTIGATE")
    return jsonify({
        "total":         total,
        "keep":          keep,    "keep_pct":   _pct(keep, total),
        "tune":          tune,    "tune_pct":   _pct(tune, total),
        "investigate":   inv,     "invest_pct": _pct(inv,  total),
        "avg_estrellas": _avg(entries),
        "por_estrategia": estrategias,
        "por_simbolo":    simbolos,
    }), 200

# ═══════════════════════════════════════════════════════════
# VERSION
# ═══════════════════════════════════════════════════════════

@app.route("/version", methods=["GET"])
def version_endpoint():
    import sys
    return jsonify({
        "axis_version":   AXIS_VERSION,
        "git_commit":     _GIT_COMMIT,
        "build_date":     _BUILD_DATE,
        "environment":    _ENVIRONMENT,
        "deploy_id":      _DEPLOY_ID,
        "service_name":   _SERVICE_NAME,
        "python_version": sys.version.split()[0],
        "status":         "OK",
    }), 200

@app.route("/reconciliation/notification-status", methods=["GET"])
@require_admin
def reconciliation_notification_status_endpoint():
    """Estado de entrega Telegram; nunca expone token ni chat_id."""
    return jsonify(notification_status()), 200

# ═══════════════════════════════════════════════════════════
# SOURCE — expone archivos para lectura de AI
# GET /source/<filename> con encabezado X-AXIS-Admin-Token
# ═══════════════════════════════════════════════════════════
ARCHIVOS_FUENTE = ['server.py', 'axis_charts.html', 'axis_portfolio.html', 'axis_bitacora.html', 'axis_analisis.html']

@app.route("/source/<filename>")
@require_admin
def get_source(filename):
    if filename not in ARCHIVOS_FUENTE:
        return jsonify({"error": "not found"}), 404
    try:
        with open(os.path.join(os.path.dirname(__file__), filename), 'r', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except FileNotFoundError:
        return jsonify({"error": "file not found on disk"}), 404

def arrancar_monitor():
    time.sleep(5)
    # AX-TRACK-NOTIFY-001 no depende de mercado ni del Core. Inicia primero
    # para que un fallo posterior de carga no bloquee la entrega semanal.
    threading.Thread(target=reconciliation_notification_loop, daemon=True).start()
    cargar_canales()
    cargar_portfolio()
    reconciliar_posiciones_vencidas(datetime.now(EST))
    cargar_ordenes()
    cargar_estado_dia()
    construir_base_datos()
    threading.Thread(target=monitor_loop,              daemon=True).start()
    threading.Thread(target=loop_v7_anticipada,        daemon=True).start()
    threading.Thread(target=loop_limpiar_ordenes,      daemon=True).start()
    threading.Thread(target=loop_polling_posiciones,   daemon=True).start()

threading.Thread(target=arrancar_monitor, daemon=True).start()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
