#!/usr/bin/env python3
"""
AXIS Breakout Sentinel v8.50
Estrategias: 1VR | 1VR+ | RPG | GNA | GBA | RCB/CNF
Multi-activo: SPY, AAPL, BA, GLD
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
"""

import requests
import threading
import time
from datetime import datetime, timedelta
import pytz
from flask import Flask, jsonify, request

app = Flask(__name__)

# ── CORS — permite llamadas desde la app web ──
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    from flask import Response
    return Response(status=200)

# ═══════════════════════════════════════════════════════════
# CONFIGURACION
# ═══════════════════════════════════════════════════════════
TELEGRAM_TOKEN   = "8668514895:AAGWRxFmA9c8tZKIe-5i9tJ31RQtzi1-NYs"
TELEGRAM_CHAT_ID = "-5010153427"
TWELVEDATA_KEY   = "66dd71373a884f7bb7da8e6e5e469571"
FINNHUB_KEY      = "d71aocpr01qot5jcnohgd71aocpr01qot5jcnoi0"
EST              = pytz.timezone("America/New_York")

# ── TRADIER SANDBOX (ordenes paper trading) ──
import os
import json

TRADIER_TOKEN   = os.environ.get("TRADIER_TOKEN", "")
TRADIER_ACCOUNT = os.environ.get("TRADIER_ACCOUNT", "")
TRADIER_BASE    = "https://sandbox.tradier.com/v1"
TRADIER_HEADERS = {
    "Authorization": f"Bearer {TRADIER_TOKEN}",
    "Accept":        "application/json",
}

# ── TRADIER PRODUCCION (datos historicos de mercado) ──
TRADIER_TOKEN_REAL   = os.environ.get("TRADIER_TOKEN_REAL", "")
TRADIER_BASE_REAL    = "https://api.tradier.com/v1"
TRADIER_HEADERS_REAL = {
    "Authorization": f"Bearer {TRADIER_TOKEN_REAL}",
    "Accept":        "application/json",
}

# Ordenes pendientes de confirmacion — clave: orden_id
# Valor: { "opcion": {...}, "ts": datetime, "chat_id": int, "message_id": int }
ordenes_pendientes = {}
ORDEN_TIMEOUT_MIN = 15  # minutos antes de expirar

def guardar_ordenes():
    """Persiste ordenes_pendientes en /data para sobrevivir reinicios."""
    try:
        data = {}
        for oid, d in ordenes_pendientes.items():
            data[oid] = {
                "opcion":         d["opcion"],
                "estrategia":     d.get("estrategia", "AXIS"),
                "ts":             d["ts"].isoformat() if hasattr(d["ts"], "isoformat") else str(d["ts"]),
                "message_id":     d["message_id"],
                "chat_id":        d["chat_id"],
                "texto_original": d.get("texto_original", ""),
            }
        with open(ORDENES_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error guardando ordenes: {e}")

def cargar_ordenes():
    """Carga ordenes_pendientes desde /data al arrancar."""
    global ordenes_pendientes
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
        guardar_ordenes()
    except Exception as e:
        print(f"Error cargando ordenes: {e}")

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
                guardar_ordenes()
                # Editar mensaje original en Telegram
                try:
                    texto_original = datos.get("texto_original", "")
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText",
                        json={
                            "chat_id":    datos["chat_id"],
                            "message_id": datos["message_id"],
                            "text":       f"{texto_original}\n\n━━━━━━━━━━━━━━━━━━\n⏰ <b>Orden expirada</b> — no se ejecutó (>{ORDEN_TIMEOUT_MIN} min sin respuesta)",
                            "parse_mode": "HTML",
                        },
                        timeout=5
                    )
                except Exception as e:
                    print(f"Error editando mensaje expirado {oid}: {e}")
                print(f"Orden expirada y eliminada — ID: {oid}")
        except Exception as e:
            print(f"Error loop_limpiar_ordenes: {e}")

ACTIVOS          = ["SPY", "AAPL", "BA", "GLD", "NVDA", "AMZN", "GOOG", "META"]
HORAS_REPORTE    = [10, 11, 12, 13, 14, 15, 16]
# SPY cierra 4:15 PM EST — excepción única
ACTIVOS_SPY      = ["SPY"]
SISTEMA_ACTIVO   = True

# Switches estrategias globales
VR1_ON  = True
RPG_ON  = True
GNA_ON  = True
GBA_ON  = True

# ═══════════════════════════════════════════════════════════
# ESTADO POR ACTIVO
# ═══════════════════════════════════════════════════════════
def estado_diario_vacio():
    return {
        "fecha":         None,
        "v1_close":      None,
        "v1_open":       None,
        "v1_low":        None,
        "v7_ayer_close": None,
        "rpg_piso":      None,
        "rpg_activo":    False,
        "rpg_fired":     False,
        "rpg_s20":       None,
        "rpg_s40":       None,
        "gna_activo":    False,
        "gna_fired":     False,
        "gba_activo":    False,
        "gba_fired":     False,
        "vr1_fired":     False,
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
    }

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
    }

estado_dia = {a: estado_diario_vacio() for a in ACTIVOS}
canal      = {a: canal_vacio()         for a in ACTIVOS}

# ═══════════════════════════════════════════════════════════
# PERSISTENCIA DE CANALES — archivo JSON en /tmp
# Sobrevive reinicios de Railway dentro del mismo deployment
# Al primer deploy usa CANALES_DEFAULT con SPY y GLD preconfigurados
# ═══════════════════════════════════════════════════════════
CANALES_FILE    = "/data/axis_canales.json"
PORTFOLIO_FILE  = "/data/axis_portfolio.json"
ORDENES_FILE    = "/data/axis_ordenes.json"

# ═══════════════════════════════════════════════════════════
# ANTHROPIC — ANÁLISIS DE PORTFOLIO
# ═══════════════════════════════════════════════════════════
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

def analizar_portfolio_claude(posiciones, reto):
    """Llama a Claude para analizar el portfolio y dar recomendaciones."""
    if not ANTHROPIC_API_KEY:
        return "API key de Anthropic no configurada."
    if not posiciones and not any(c["posicion"] for c in reto["carriles"]):
        return "Sin posiciones abiertas para analizar."
    try:
        # Construir contexto del portfolio
        ahora = datetime.now(EST)
        contexto_pos = []
        for pos in posiciones:
            contexto_pos.append(
                f"- {pos['simbolo']} {pos['tipo']} ${pos['strike']} exp {pos['expiration']} "
                f"| Entrada: ${pos['precio_entrada']:.2f} | GTC: ${pos['precio_gtc']:.2f} "
                f"| Estrategia: {pos['estrategia']}"
                f"{' | RETO Carril #' + str(pos['carril_id']) if pos.get('es_reto') else ''}"
            )
        capital_reto = sum(c["capital"] for c in reto["carriles"])
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
def portfolio_vacio():
    return {
        "posiciones":  [],
        "historial":   [],
        "reto": {
            "activo":          False,
            "turno_actual":    1,      # próximo carril en orden rotativo
            "carriles": [
                {
                    "id":              i+1,
                    "capital":         0,       # empieza en 0 — se asigna en primera compra
                    "capital_inicial": 0,       # se fija en primera compra real
                    "ronda":           0,
                    "posicion":        None,
                    "eliminado":       False,
                    "historial":       []
                }
                for i in range(10)
            ]
        }
    }

_portfolio = None

def cargar_portfolio():
    global _portfolio
    try:
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE, 'r') as f:
                _portfolio = json.load(f)
            print(f"Portfolio cargado — {len(_portfolio['posiciones'])} posiciones abiertas")
        else:
            _portfolio = portfolio_vacio()
            guardar_portfolio()
            print("Portfolio nuevo creado")
    except Exception as e:
        print(f"Error cargando portfolio: {e}")
        _portfolio = portfolio_vacio()

def guardar_portfolio():
    try:
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump(_portfolio, f, indent=2, default=str)
    except Exception as e:
        print(f"Error guardando portfolio: {e}")

def registrar_posicion(opcion, estrategia, simbolo, precio_entrada, es_reto=False, carril_id=None,
                       contratos=1, tradier_orden_id=None, tradier_gtc_id=None):
    """Registra una posición abierta en el portfolio."""
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    import uuid
    pos = {
        "id":               str(uuid.uuid4())[:8],
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
    }
    _portfolio["posiciones"].append(pos)
    if es_reto and carril_id:
        for c in _portfolio["reto"]["carriles"]:
            if c["id"] == carril_id:
                c["posicion"] = pos["id"]
                c["ronda"]   += 1
                break
    guardar_portfolio()
    return pos

def cancelar_orden_tradier(orden_id):
    """Cancela una orden activa en Tradier sandbox."""
    try:
        r = requests.delete(
            f"{TRADIER_BASE}/accounts/{TRADIER_ACCOUNT}/orders/{orden_id}",
            headers=TRADIER_HEADERS,
            timeout=10
        )
        print(f"Cancelar orden Tradier {orden_id}: HTTP {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"Error cancelar orden Tradier {orden_id}: {e}")
        return False

def get_bid_opcion_tradier(option_symbol):
    """Obtiene el bid actual de una opción en Tradier sandbox."""
    try:
        r = requests.get(
            f"{TRADIER_BASE}/markets/quotes",
            headers=TRADIER_HEADERS,
            params={"symbols": option_symbol, "greeks": "false"},
            timeout=10
        )
        data  = r.json()
        quote = data.get("quotes", {}).get("quote", {})
        bid   = float(quote.get("bid", 0))
        return bid if bid > 0 else None
    except Exception as e:
        print(f"Error bid opcion {option_symbol}: {e}")
        return None

def vender_opcion_tradier(option_symbol, simbolo, contratos, precio_limit):
    """Coloca orden de venta limit al bid en Tradier sandbox (Panic)."""
    try:
        payload = {
            "class":         "option",
            "symbol":        simbolo,
            "option_symbol": option_symbol,
            "side":          "sell_to_close",
            "quantity":      str(contratos),
            "type":          "limit",
            "price":         str(round(precio_limit, 2)),
            "duration":      "day",
        }
        r = requests.post(
            f"{TRADIER_BASE}/accounts/{TRADIER_ACCOUNT}/orders",
            headers=TRADIER_HEADERS,
            data=payload,
            timeout=10
        )
        data     = r.json()
        orden_id = data.get("order", {}).get("id")
        status   = data.get("order", {}).get("status", "unknown")
        return {"ok": True, "id": orden_id, "status": status}
    except Exception as e:
        print(f"Error vender opcion Tradier: {e}")
        return {"ok": False, "error": str(e)}

def cerrar_posicion(pos_id, precio_cierre, motivo="panic"):
    """Cierra una posición y la mueve al historial."""
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    pos = next((p for p in _portfolio["posiciones"] if p["id"] == pos_id), None)
    if not pos:
        return None

    # Duración abierta
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

    # Actualizar carril del Reto si aplica
    if pos.get("es_reto") and pos.get("carril_id"):
        for c in _portfolio["reto"]["carriles"]:
            if c["id"] == pos["carril_id"]:
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
                # Eliminar carril si capital insuficiente para comprar 1 contrato mínimo
                # Mínimo referencial: $280 (SPY ~$350 × 80% presupuesto)
                CAPITAL_MINIMO = 280
                if nuevo_capital < CAPITAL_MINIMO:
                    c["eliminado"] = True
                    enviar_telegram(
                        f"💀 <b>Carril #{c['id']} ELIMINADO</b>\n"
                        f"Capital final: ${nuevo_capital:.2f} — insuficiente para siguiente ronda\n"
                        f"Capital inicial fue: ${c.get('capital_inicial', 0):.2f}"
                    )
                break

    _portfolio["posiciones"] = [p for p in _portfolio["posiciones"] if p["id"] != pos_id]
    _portfolio["historial"].append(pos)
    guardar_portfolio()

    # Notificar Telegram
    emoji  = "✅" if pl_pct > 0 else "🔴"
    t_str  = f"{minutos_abierta//60}h {minutos_abierta%60}m" if minutos_abierta >= 60 else f"{minutos_abierta}m"
    enviar_telegram(
        f"{emoji} <b>Posición cerrada — {pos['simbolo']}</b>\n"
        f"<b>Motivo:</b> {motivo}\n"
        f"<b>{pos['tipo']} ${pos['strike']} exp {pos['expiration']}</b>\n"
        f"<b>Contratos:</b> {contratos} | <b>Tiempo:</b> {t_str}\n"
        f"<b>P&L:</b> {'+' if pl_pct > 0 else ''}{pl_pct}% | ${'+' if pl_usd > 0 else ''}{pl_usd:.2f}\n"
        f"<b>Entrada:</b> ${pos['precio_entrada']:.2f} → <b>Cierre:</b> ${precio_cierre:.2f}"
    )
    return pos

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

def guardar_canales():
    try:
        data = {}
        for a in ACTIVOS:
            c = canal[a]
            ts = c["p2_actual_ts"]
            data[a] = {
                "on":             c["on"],
                "apagado":        c["apagado"],
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

def cargar_canales():
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
def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        print(f"Telegram: {r.status_code} — {mensaje[:60]}")
    except Exception as e:
        print(f"Error Telegram: {e}")

# ═══════════════════════════════════════════════════════════
# UTILIDAD — Dias habiles (funcion global)
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
# GET_VELAS — Tradier produccion 15min → velas AXIS
# V1 = 9:30+9:45 | V2-V7 = 4 barras de 15min cada una
# ═══════════════════════════════════════════════════════════
def get_velas(simbolo, outputsize=50):
    try:
        from datetime import date, datetime as dt2
        from collections import defaultdict

        # Tradier soporta ~40 dias habiles de timesales 15min
        # Un solo rango elimina los HTTP 400 de rangos viejos
        fecha_fin = date.today()
        fecha_ini = restar_dias_habiles(fecha_fin, 40)

        todas_barras = []

        r = requests.get(
            f"{TRADIER_BASE_REAL}/markets/timesales",
            headers=TRADIER_HEADERS_REAL,
            params={
                "symbol":         simbolo,
                "interval":       "15min",
                "start":          f"{fecha_ini.strftime('%Y-%m-%d')} 09:00",
                "end":            f"{fecha_fin.strftime('%Y-%m-%d')} 16:30",
                "session_filter": "open",
            },
            timeout=30
        )
        if r.status_code != 200:
            print(f"Tradier error {simbolo}: HTTP {r.status_code}")
            return None
        data   = r.json()
        series = data.get("series")
        if not series or series == "null":
            print(f"Tradier sin datos {simbolo}")
            return None
        barras = series.get("data", [])
        if isinstance(barras, dict):
            barras = [barras]
        todas_barras = barras

        # Agrupar barras por fecha y vela AXIS
        # Estructura: { "2026-05-12": { "V1": [barras], ... }, ... }
        dias_dict = defaultdict(lambda: defaultdict(list))

        for b in todas_barras:
            ts_str = b["time"].replace("T", " ")
            bdt    = dt2.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            fecha  = bdt.strftime("%Y-%m-%d")
            h, m   = bdt.hour, bdt.minute

            # V1 = barras 9:30 y 9:45
            if h == 9 and m in (30, 45):
                dias_dict[fecha]["V1"].append(b)
            elif h == 10: dias_dict[fecha]["V2"].append(b)
            elif h == 11: dias_dict[fecha]["V3"].append(b)
            elif h == 12: dias_dict[fecha]["V4"].append(b)
            elif h == 13: dias_dict[fecha]["V5"].append(b)
            elif h == 14: dias_dict[fecha]["V6"].append(b)
            elif h == 15: dias_dict[fecha]["V7"].append(b)

        # Construir lista de velas en formato compatible con el resto del codigo
        # Ordenadas de mas reciente a mas antigua (igual que TwelveData)
        vela_hora = {"V1":"09:30:00","V2":"10:00:00","V3":"11:00:00",
                     "V4":"12:00:00","V5":"13:00:00","V6":"14:00:00","V7":"15:00:00"}
        resultado_velas = []

        for fecha in sorted(dias_dict.keys(), reverse=True):
            for vela in ["V7","V6","V5","V4","V3","V2","V1"]:
                bs = dias_dict[fecha].get(vela, [])
                if not bs:
                    continue
                o = float(bs[0]["open"])
                h = max(float(b["high"]) for b in bs)
                l = min(float(b["low"])  for b in bs)
                c = float(bs[-1]["close"])
                resultado_velas.append({
                    "datetime": f"{fecha} {vela_hora[vela]}",
                    "open":     str(round(o, 4)),
                    "high":     str(round(h, 4)),
                    "low":      str(round(l, 4)),
                    "close":    str(round(c, 4)),
                    "vela":     vela,
                })

        if not resultado_velas:
            print(f"get_velas {simbolo}: sin velas construidas")
            return None

        # Limitar a outputsize
        return resultado_velas[:outputsize]

    except Exception as e:
        print(f"Error get_velas Tradier {simbolo}: {e}")
        return None

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

def calcular_techo_canal(simbolo, ahora_dt):
    c = canal[simbolo]
    if not c["on"] or c["apagado"] or not c["p1"] or not c["p2"]:
        return None
    try:
        # Usar p2_actual si está disponible, sino usar p2 base
        p2_high = c["p2_actual_high"] if c["p2_actual_high"] else c["p2"]["high"]
        if c["p2_actual_ts"]:
            dt_p2 = c["p2_actual_ts"]
        else:
            dt_p2 = ts_a_datetime(c["p2"]["fecha"], c["p2"]["hora_est"])

        dt_p1 = ts_a_datetime(c["p1"]["fecha"], c["p1"]["hora_est"])
        horas_p1_p2 = (dt_p2 - dt_p1).total_seconds() / 3600
        if horas_p1_p2 <= 0:
            return None
        slope = (p2_high - c["p1"]["high"]) / horas_p1_p2
        horas_desde_p1 = (ahora_dt - dt_p1).total_seconds() / 3600
        return c["p1"]["high"] + slope * horas_desde_p1
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
# EVALUAR VELA POR ACTIVO
# ═══════════════════════════════════════════════════════════
def evaluar_activo(simbolo, velas, ahora):
    hora = ahora.hour
    ed   = estado_dia[simbolo]
    c    = canal[simbolo]

    vela_actual = None
    for v in velas:
        dt_v = datetime.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S")
        if dt_v.hour == hora - 1:
            vela_actual = v
            break

    if not vela_actual:
        print(f"{simbolo}: no se encontro vela para hora {hora-1}")
        return

    v_open  = float(vela_actual["open"])
    v_close = float(vela_actual["close"])
    v_high  = float(vela_actual["high"])
    v_low   = float(vela_actual["low"])
    fecha_hoy = datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")

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

                # ── v8.7: 1VR / 1VR+ — con botones EJECUTAR/IGNORAR ──
                if VR1_ON and v1_close_r < v1_open_r and not ed["vr1_fired"]:
                    if hora == 10:
                        ahora_dt_r = EST.localize(datetime.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S"))
                        techo_r = calcular_techo_canal(simbolo, ahora_dt_r)
                        _, mitad_r = calcular_piso_mitad_canal(simbolo, ahora_dt_r)
                        c_r = canal[simbolo]
                        en_canal_rcb = (
                            c_r["on"] and not c_r["apagado"] and c_r["p3"] is not None
                            and techo_r is not None and mitad_r is not None
                            and mitad_r <= v1_close_r <= techo_r
                        )
                        label = "1VR+" if en_canal_rcb else "1VR"
                        extra = f"<b>Canal RCB:</b> Techo ${techo_r:.2f} | Mitad ${mitad_r:.2f}\n" if en_canal_rcb else ""
                        enviar_senal_con_botones(
                            simbolo, f"{label} — PRIMERA VELA ROJA",
                            "10:00 EST", v1_close_r, "PUT",
                            f"<b>Open:</b> ${v1_open_r:.2f} | <b>Close:</b> ${v1_close_r:.2f}\n{extra}"
                        )
                    ed["vr1_fired"] = True

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

        # ── 1VR — Primera Vela Roja ──
        if VR1_ON and v_roja and not ed["vr1_fired"]:
            ahora_dt_vr = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))
            techo_vr    = calcular_techo_canal(simbolo, ahora_dt_vr)
            _, mitad_vr = calcular_piso_mitad_canal(simbolo, ahora_dt_vr)
            c_vr        = canal[simbolo]
            sma20_vr    = calcular_sma(velas, 20)
            sma40_vr    = calcular_sma(velas, 40)

            # Condición A: dentro de RCB entre techo y 30% hacia la media
            zona_30 = None
            if techo_vr and mitad_vr:
                zona_30 = techo_vr - (techo_vr - mitad_vr) * 0.30
            en_rcb_30 = (
                c_vr["on"] and not c_vr["apagado"] and c_vr["p3"] is not None
                and techo_vr is not None and zona_30 is not None
                and zona_30 <= v_close <= techo_vr
            )

            # Condición B: SMA40 > SMA20
            sma40_gt_sma20 = sma40_vr and sma20_vr and sma40_vr > sma20_vr

            # Necesita UNA de las dos condiciones
            if en_rcb_30 or sma40_gt_sma20:
                ed["vr1_fired"] = True
                label_vr = "1VR+" if en_rcb_30 else "1VR"
                extra_vr = f"<b>Canal RCB:</b> Techo ${techo_vr:.2f} | Zona 30%: ${zona_30:.2f}\n" if en_rcb_30 else \
                           f"<b>SMA40:</b> ${sma40_vr:.2f} > <b>SMA20:</b> ${sma20_vr:.2f}\n"
                enviar_senal_con_botones(
                    simbolo, f"{label_vr} — PRIMERA VELA ROJA",
                    "10:00 EST", v_close, "PUT",
                    f"<b>Open:</b> ${v_open:.2f} | <b>Close:</b> ${v_close:.2f}\n{extra_vr}"
                )
            else:
                print(f"{simbolo} 1VR sin condición adicional — no dispara")

        # RPG — gap mínimo 0.5%, V1 verde
        if RPG_ON and v7_ayer and v_close > v_open and not ed["rpg_fired"]:
            gap = abs(v_open - v7_ayer) / v7_ayer * 100
            if gap >= 0.5:
                ed["rpg_activo"] = True
                ed["rpg_piso"]   = v_low
                ed["rpg_s20"]    = calcular_sma(velas, 20)
                ed["rpg_s40"]    = calcular_sma(velas, 40)
                print(f"{simbolo} RPG activado — gap {gap:.2f}% piso: ${v_low:.2f}")

        # GNA
        if GNA_ON and v7_ayer and v_close > v_open and not ed["gna_fired"]:
            gap_alza = (v_open - v7_ayer) / v7_ayer * 100
            if gap_alza >= 0.1:
                sma20 = calcular_sma(velas, 20)
                sma40 = calcular_sma(velas, 40)
                if sma20 and sma40 and sma20 > sma40:
                    ed["gna_activo"] = True
                    print(f"{simbolo} GNA activado — techo: ${v_close:.2f}")

        # GBA
        if GBA_ON and v7_ayer and v_close > v_open and not ed["gba_fired"]:
            gap_baja = (v7_ayer - v_open) / v7_ayer * 100
            if gap_baja >= 0.1:
                ed["gba_activo"] = True
                print(f"{simbolo} GBA activado — techo: ${v_close:.2f}")

        # Canal V1 candidato
        if c["on"] and not c["apagado"]:
            ahora_dt = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))
            techo = calcular_techo_canal(simbolo, ahora_dt)
            if techo and v_close > techo and v_alcista:
                c["v1_candidato"] = v_high
                print(f"{simbolo} Canal V1 candidato Auto-P2: ${v_high:.2f}")

        # PM40 — P1 dinámico en V1 (solo si no hay canal manual activo)
        if not c["on"] and not ed["pm40_fired"]:
            sma20  = calcular_sma(velas, 20)
            sma40  = calcular_sma(velas, 40)
            sma100 = calcular_sma(velas, 100)
            sma200 = calcular_sma(velas, 200)
            smas_ok = sma20 and sma40 and sma100 and sma200 and sma20 > sma40 > sma100 > sma200
            ed["pm40_vela_idx"] = 1  # V1 = posición 1
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

                    # P2 dinámico en V1 — si HIGH > P2 actual → actualizar P2
                    if ed["pm40_p2_high"] is not None and v_high > ed["pm40_p2_high"]:
                        ed["pm40_p2_high"] = v_high
                        ed["pm40_p2_idx"]  = ed["pm40_vela_idx"]
                        canal[simbolo]["p2"]["high"]      = v_high
                        canal[simbolo]["p2_actual_high"]  = v_high
                        # P2 >= P1 → canal bajista inválido → reset completo
                        if ed["pm40_p2_high"] >= ed["pm40_p1_high"]:
                            ed["pm40_activo"] = False; ed["pm40_p1_high"] = None
                            ed["pm40_p1_idx"] = None; ed["pm40_p2_high"] = None
                            ed["pm40_p2_idx"] = None; ed["pm40_velas_bajo_p1"] = 0
                            ed["pm40_p1_maduro"] = False; canal[simbolo]["on"] = False
                            guardar_canales()
                            print(f"{simbolo} PM40 reset — P2 >= P1")
                        else:
                            guardar_canales()
                            print(f"{simbolo} PM40 P2 dinámico V1: ${v_high:.2f}")

        # 4PASOS en V1 — solo si hay canal RCB activo
        if c["on"] and not c["apagado"] and c["p3"] is not None and not ed["4ps_fired"]:
            ed["4ps_vela_idx"] = 1
            if not ed["4ps_activo"]:
                ed["4ps_activo"]         = True
                ed["4ps_p1_low"]         = v_low
                ed["4ps_p1_idx"]         = 1
                ed["4ps_p2_low"]         = None
                ed["4ps_p2_idx"]         = None
                ed["4ps_velas_sobre_p1"] = 0
                ed["4ps_p1_maduro"]      = False
            elif v_low <= ed["4ps_p1_low"]:
                ed["4ps_p1_low"]         = v_low
                ed["4ps_p1_idx"]         = 1
                ed["4ps_p2_low"]         = None
                ed["4ps_p2_idx"]         = None
                ed["4ps_velas_sobre_p1"] = 0
                ed["4ps_p1_maduro"]      = False
            else:
                ed["4ps_velas_sobre_p1"] += 1
                if ed["4ps_velas_sobre_p1"] >= 3:
                    ed["4ps_p1_maduro"] = True

        return

    # ── VELAS 2-7 ──
    v1_close = ed["v1_close"]

    # RPG — cualquier vela que cierre < piso + UNA de (RCB 30%) O (SMA20>SMA40)
    if RPG_ON and ed["rpg_activo"] and not ed["rpg_fired"] and ed["rpg_piso"]:
        if v_close < ed["rpg_piso"]:
            ahora_dt_rpg = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))
            techo_rpg    = calcular_techo_canal(simbolo, ahora_dt_rpg)
            _, mitad_rpg = calcular_piso_mitad_canal(simbolo, ahora_dt_rpg)
            c_rpg        = canal[simbolo]

            # Condición A: dentro RCB entre techo y 30% hacia la media
            zona_30_rpg = None
            if techo_rpg and mitad_rpg:
                zona_30_rpg = techo_rpg - (techo_rpg - mitad_rpg) * 0.30
            en_rcb_30_rpg = (
                c_rpg["on"] and not c_rpg["apagado"] and c_rpg["p3"] is not None
                and techo_rpg is not None and zona_30_rpg is not None
                and zona_30_rpg <= v_close <= techo_rpg
            )

            # Condición B: SMA20 > SMA40
            s20_rpg = ed.get("rpg_s20")
            s40_rpg = ed.get("rpg_s40")
            sma20_gt_sma40 = s20_rpg and s40_rpg and s20_rpg > s40_rpg

            if en_rcb_30_rpg or sma20_gt_sma40:
                ed["rpg_fired"]  = True
                ed["rpg_activo"] = False
                label_rpg = "RPG+" if en_rcb_30_rpg else "RPG"
                extra_rpg = f"<b>Canal RCB:</b> Techo ${techo_rpg:.2f} | Zona 30%: ${zona_30_rpg:.2f}\n" if en_rcb_30_rpg else \
                            f"<b>SMA20:</b> ${s20_rpg:.2f} > <b>SMA40:</b> ${s40_rpg:.2f}\n"
                enviar_senal_con_botones(
                    simbolo, f"{label_rpg} — RUPTURA PISO GAP",
                    f"{hora_vela+1}:00 EST", v_close, "PUT",
                    f"<b>Piso V1:</b> ${ed['rpg_piso']:.2f} | <b>Cierre:</b> ${v_close:.2f}\n{extra_rpg}"
                )
            else:
                print(f"{simbolo} RPG ruptura sin condición adicional — no dispara")

    # GNA
    if GNA_ON and ed["gna_activo"] and not ed["gna_fired"] and v1_close:
        if v_alcista and v_close > v1_close:
            ed["gna_fired"]  = True
            ed["gna_activo"] = False
            tipo = "GNA" if hora_vela == 10 else "GNA+2"
            enviar_senal_con_botones(
                simbolo, f"{tipo} — GAP NORMAL ALZA",
                f"{hora_vela+1}:00 EST", v_close, "CALL",
                f"<b>Techo V1:</b> ${v1_close:.2f} | <b>Cierre:</b> ${v_close:.2f}\n"
            )

    # GBA
    if GBA_ON and ed["gba_activo"] and not ed["gba_fired"] and v1_close:
        if v_alcista and v_close > v1_close:
            ed["gba_fired"]  = True
            ed["gba_activo"] = False
            tipo = "GBA" if hora_vela == 10 else "GBA+2"
            enviar_senal_con_botones(
                simbolo, f"{tipo} — GAP BAJISTA ALZA",
                f"{hora_vela+1}:00 EST", v_close, "CALL",
                f"<b>Techo V1:</b> ${v1_close:.2f} | <b>Cierre:</b> ${v_close:.2f}\n"
            )

    # RCB/CNF — ruptura con botones igual que todas las estrategias
    if c["on"] and not c["apagado"]:
        ahora_dt = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))
        techo = calcular_techo_canal(simbolo, ahora_dt)

        if techo and v_alcista and v_close > techo:
            tipo_canal = "RCB" if c["p3"] else "CNF"
            if v_high < c["p1"]["high"]:
                # Ruptura válida — señal con botones
                enviar_senal_con_botones(
                    simbolo,
                    f"{tipo_canal} — RUPTURA CANAL",
                    f"{hora_vela+1}:00 EST",
                    v_close,
                    "CALL",
                    f"<b>Techo:</b> ${techo:.2f} | <b>Cierre:</b> ${v_close:.2f}\n"
                    f"<b>P1:</b> ${c['p1']['high']:.2f} | <b>P2:</b> ${c['p2_actual_high']:.2f}\n"
                )
                # Actualizar P2 con este high
                c["p2_actual_high"] = v_high
                c["p2"]["high"]     = v_high
                c["p2_actual_ts"]   = ahora_dt
                # P2 >= P1 → canal inválido → apagar
                if c["p2_actual_high"] >= c["p1"]["high"]:
                    c["on"] = False; c["apagado"] = True
                    guardar_canales()
                    enviar_telegram(f"🔕 <b>Canal APAGADO — {simbolo}</b>\nP2 ${v_high:.2f} >= P1 ${c['p1']['high']:.2f}")
                else:
                    guardar_canales()
                print(f"{simbolo} {tipo_canal} ruptura V{hora_vela-8} techo=${techo:.2f} close=${v_close:.2f}")
            else:
                # High >= P1 — canal apagado
                c["apagado"] = True
                guardar_canales()
                enviar_telegram(
                    f"🔕 <b>Canal APAGADO — {simbolo}</b>\n"
                    f"High ${v_high:.2f} >= P1 ${c['p1']['high']:.2f}"
                )

    # PM40 — V2-V7
    if not c["on"] and ed["pm40_activo"] and not ed["pm40_fired"] and ed["pm40_p1_high"]:
        ed["pm40_vela_idx"] += 1
        idx_actual = ed["pm40_vela_idx"]

        if v_high >= ed["pm40_p1_high"]:
            # HIGH >= P1 → P1 se mueve
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
                    # Fijar P2
                    ed["pm40_p2_high"] = v_high
                    ed["pm40_p2_idx"]  = idx_actual
                    print(f"{simbolo} PM40 P2 fijado: ${v_high:.2f} idx={idx_actual}")

                elif ed["pm40_p2_idx"] is not None:
                    slope      = (ed["pm40_p2_high"] - ed["pm40_p1_high"]) / (ed["pm40_p2_idx"] - ed["pm40_p1_idx"])
                    techo_pm40 = ed["pm40_p1_high"] + slope * (idx_actual - ed["pm40_p1_idx"])

                    if v_high > techo_pm40:
                        if v_alcista and hora_vela > 9:
                            # SEÑAL PM40
                            ed["pm40_fired"]  = True
                            ed["pm40_activo"] = False
                            enviar_senal_con_botones(
                                simbolo, "PM40 — RUPTURA CANAL BAJISTA",
                                f"{hora_vela+1}:00 EST", v_close, "CALL",
                                f"<b>P1:</b> ${ed['pm40_p1_high']:.2f} | <b>P2:</b> ${ed['pm40_p2_high']:.2f}\n"
                                f"<b>Techo:</b> ${techo_pm40:.2f} | <b>High:</b> ${v_high:.2f}\n"
                            )
                        elif v_high < ed["pm40_p1_high"]:
                            # P2 dinámico — high supera techo pero < P1 → actualizar P2
                            ed["pm40_p2_high"] = v_high
                            ed["pm40_p2_idx"]  = idx_actual
                            canal[simbolo]["p2"]["high"]     = v_high
                            canal[simbolo]["p2_actual_high"] = v_high
                            if ed["pm40_p2_high"] >= ed["pm40_p1_high"]:
                                ed["pm40_activo"] = False; ed["pm40_p1_high"] = None
                                ed["pm40_p1_idx"] = None; ed["pm40_p2_high"] = None
                                ed["pm40_p2_idx"] = None; ed["pm40_velas_bajo_p1"] = 0
                                ed["pm40_p1_maduro"] = False; canal[simbolo]["on"] = False
                                guardar_canales()
                                print(f"{simbolo} PM40 reset — P2 >= P1")
                            else:
                                guardar_canales()
                                print(f"{simbolo} PM40 P2 dinámico actualizado: ${v_high:.2f}")
                    elif v_high > ed["pm40_p2_high"]:
                        # P2 dinámico — high mayor que P2 actual → actualizar P2
                        ed["pm40_p2_high"] = v_high
                        ed["pm40_p2_idx"]  = idx_actual
                        canal[simbolo]["p2"]["high"]     = v_high
                        canal[simbolo]["p2_actual_high"] = v_high
                        if ed["pm40_p2_high"] >= ed["pm40_p1_high"]:
                            ed["pm40_activo"] = False; ed["pm40_p1_high"] = None
                            ed["pm40_p1_idx"] = None; ed["pm40_p2_high"] = None
                            ed["pm40_p2_idx"] = None; ed["pm40_velas_bajo_p1"] = 0
                            ed["pm40_p1_maduro"] = False; canal[simbolo]["on"] = False
                            guardar_canales()
                            print(f"{simbolo} PM40 reset — P2 >= P1")
                        else:
                            guardar_canales()
                            print(f"{simbolo} PM40 P2 dinámico mejorado: ${v_high:.2f}")

    # 4PASOS — V2-V7 (solo dentro de canal RCB activo)
    if c["on"] and not c["apagado"] and c["p3"] is not None and ed["4ps_activo"] and not ed["4ps_fired"]:
        ed["4ps_vela_idx"] += 1
        idx_4ps = ed["4ps_vela_idx"]

        # Calcular zona válida: 25% superior del canal (cerca del techo)
        ahora_dt_4ps = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))
        techo_4ps    = calcular_techo_canal(simbolo, ahora_dt_4ps)
        piso_4ps, mitad_4ps = calcular_piso_mitad_canal(simbolo, ahora_dt_4ps)
        en_zona_valida = False
        if techo_4ps and piso_4ps:
            altura_canal = techo_4ps - piso_4ps
            zona_25      = techo_4ps - altura_canal * 0.25
            en_zona_valida = v_close >= zona_25

        # Si precio sale del canal RCB → reset completo
        if techo_4ps and piso_4ps and (v_close > techo_4ps or v_close < piso_4ps):
            ed["4ps_activo"]         = False
            ed["4ps_p1_low"]         = None
            ed["4ps_p1_idx"]         = None
            ed["4ps_p2_low"]         = None
            ed["4ps_p2_idx"]         = None
            ed["4ps_velas_sobre_p1"] = 0
            ed["4ps_p1_maduro"]      = False
            print(f"{simbolo} 4PASOS reset — precio fuera del canal")

        elif v_low <= ed["4ps_p1_low"]:
            # Low <= P1 → P1 se mueve, P2 resetea
            ed["4ps_p1_low"]         = v_low
            ed["4ps_p1_idx"]         = idx_4ps
            ed["4ps_p2_low"]         = None
            ed["4ps_p2_idx"]         = None
            ed["4ps_velas_sobre_p1"] = 0
            ed["4ps_p1_maduro"]      = False

        else:
            ed["4ps_velas_sobre_p1"] += 1
            if ed["4ps_velas_sobre_p1"] >= 3:
                ed["4ps_p1_maduro"] = True

            if ed["4ps_p1_maduro"]:
                distancia_4ps = idx_4ps - ed["4ps_p1_idx"]

                if ed["4ps_p2_idx"] is None and distancia_4ps >= 4:
                    # Fijar P2 primera vez
                    ed["4ps_p2_low"] = v_low
                    ed["4ps_p2_idx"] = idx_4ps
                    print(f"{simbolo} 4PASOS P2 fijado: ${v_low:.2f}")

                elif ed["4ps_p2_idx"] is not None:
                    slope_4ps   = (ed["4ps_p2_low"] - ed["4ps_p1_low"]) / (ed["4ps_p2_idx"] - ed["4ps_p1_idx"])
                    piso_slope  = ed["4ps_p1_low"] + slope_4ps * (idx_4ps - ed["4ps_p1_idx"])

                    # P2 dinámico — si low actual > P2 actual (mejor slope ascendente)
                    if v_low > ed["4ps_p2_low"] and v_low > ed["4ps_p1_low"]:
                        ed["4ps_p2_low"] = v_low
                        ed["4ps_p2_idx"] = idx_4ps
                        print(f"{simbolo} 4PASOS P2 dinámico: ${v_low:.2f}")

                    # Señal — vela roja rompe el soporte + en zona válida (25% superior)
                    elif v_roja and v_close < piso_slope and en_zona_valida:
                        ed["4ps_fired"]  = True
                        ed["4ps_activo"] = False
                        enviar_senal_con_botones(
                            simbolo, "4PASOS — RUPTURA SOPORTE ALCISTA",
                            f"{hora_vela+1}:00 EST", v_close, "PUT",
                            f"<b>P1:</b> ${ed['4ps_p1_low']:.2f} | <b>P2:</b> ${ed['4ps_p2_low']:.2f}\n"
                            f"<b>Soporte:</b> ${piso_slope:.2f} | <b>Cierre:</b> ${v_close:.2f}\n"
                            f"<b>Techo RCB:</b> ${techo_4ps:.2f}\n"
                        )
                        print(f"{simbolo} 4PASOS señal — ruptura ${piso_slope:.2f}")

    # Log estado
    print(f"{simbolo} V{hora_vela-8} {hora_vela+1}:00 — O:{v_open:.2f} C:{v_close:.2f} | RPG:{ed['rpg_activo']} GNA:{ed['gna_activo']} GBA:{ed['gba_activo']} PM40:{ed['pm40_activo']} 4PS:{ed['4ps_activo']}")


# ═══════════════════════════════════════════════════════════
# TRADIER — PRECIO ACTUAL
# ═══════════════════════════════════════════════════════════
def get_precio_tradier(simbolo):
    try:
        r = requests.get(
            f"{TRADIER_BASE}/markets/quotes",
            headers=TRADIER_HEADERS,
            params={"symbols": simbolo},
            timeout=10
        )
        data = r.json()
        return float(data["quotes"]["quote"]["last"])
    except Exception as e:
        print(f"Error precio Tradier {simbolo}: {e}")
        return None

# ═══════════════════════════════════════════════════════════
# TRADIER — BUSCAR OPCION
# ═══════════════════════════════════════════════════════════
def get_pct_otm(precio):
    """Porcentaje OTM según rango de precio del subyacente."""
    if precio < 150:  return 1.50
    if precio < 300:  return 1.25
    if precio < 500:  return 0.85
    if precio < 700:  return 0.65
    return 0.50

def get_opcion_tradier(simbolo, tipo, precio_actual):
    """
    tipo: 'call' o 'put'
    Busca el contrato con strike OTM según sistema de rangos por precio,
    vencimiento mínimo 7 días calendario.
    Sistema de rangos:
      < $150  → 1.50% OTM
      $150-300 → 1.25% OTM
      $300-500 → 0.85% OTM
      $500-700 → 0.65% OTM
      > $700   → 0.50% OTM
    """
    try:
        from datetime import date, timedelta
        hoy = date.today()

        # Vencimientos disponibles
        r = requests.get(
            f"{TRADIER_BASE}/markets/options/expirations",
            headers=TRADIER_HEADERS,
            params={"symbol": simbolo, "includeAllRoots": "true"},
            timeout=10
        )
        data  = r.json()
        fechas = data.get("expirations", {}).get("date", [])
        if isinstance(fechas, str):
            fechas = [fechas]

        # Primer vencimiento con mínimo 7 días calendario
        vencimiento = None
        for f in sorted(fechas):
            fd = date.fromisoformat(f)
            if (fd - hoy).days >= 7:
                vencimiento = f
                break

        if not vencimiento:
            print(f"Sin vencimiento ≥7 días para {simbolo}")
            return None

        # Strike objetivo según sistema de rangos OTM
        pct  = get_pct_otm(precio_actual)
        dist = precio_actual * pct / 100
        if tipo == 'call':
            strike_obj = round(precio_actual + dist)
        else:
            strike_obj = round(precio_actual - dist)

        print(f"  {simbolo} {tipo.upper()} — precio ${precio_actual:.2f} | {pct}% OTM | strike obj ${strike_obj} | venc {vencimiento}")

        # Cadena de opciones
        r2 = requests.get(
            f"{TRADIER_BASE}/markets/options/chains",
            headers=TRADIER_HEADERS,
            params={"symbol": simbolo, "expiration": vencimiento, "greeks": "false"},
            timeout=10
        )
        data2   = r2.json()
        opciones = data2.get("options", {}).get("option", [])
        if not opciones:
            return None

        # Filtrar por tipo y buscar strike más cercano al objetivo
        filtradas = [o for o in opciones if o.get("option_type") == tipo and float(o.get("ask", 0)) > 0]
        if not filtradas:
            return None

        mejor = min(filtradas, key=lambda o: abs(float(o.get("strike", 0)) - strike_obj))
        return {
            "symbol":      mejor.get("symbol"),
            "strike":      float(mejor.get("strike", 0)),
            "expiration":  vencimiento,
            "tipo":        tipo.upper(),
            "ask":         float(mejor.get("ask", 0)),
            "bid":         float(mejor.get("bid", 0)),
            "subyacente":  simbolo,
            "pct_otm":     pct,
        }
    except Exception as e:
        print(f"Error opcion Tradier {simbolo}: {e}")
        return None

# ═══════════════════════════════════════════════════════════
# TRADIER — EJECUTAR ORDEN
# ═══════════════════════════════════════════════════════════
def ejecutar_orden_tradier(opcion):
    try:
        # COMPRA — market order
        payload_compra = {
            "class":         "option",
            "symbol":        opcion["subyacente"],
            "option_symbol": opcion["symbol"],
            "side":          "buy_to_open",
            "quantity":      "1",
            "type":          "market",
            "duration":      "day",
        }
        r = requests.post(
            f"{TRADIER_BASE}/accounts/{TRADIER_ACCOUNT}/orders",
            headers=TRADIER_HEADERS,
            data=payload_compra,
            timeout=10
        )
        data     = r.json()
        orden_id = data.get("order", {}).get("id")
        status   = data.get("order", {}).get("status", "unknown")

        # VENTA LIMITE GTC al doble del ask (100% ganancia)
        precio_venta = round(opcion["ask"] * 2, 2)
        payload_venta = {
            "class":         "option",
            "symbol":        opcion["subyacente"],
            "option_symbol": opcion["symbol"],
            "side":          "sell_to_close",
            "quantity":      "1",
            "type":          "limit",
            "price":         str(precio_venta),
            "duration":      "gtc",
        }
        r2 = requests.post(
            f"{TRADIER_BASE}/accounts/{TRADIER_ACCOUNT}/orders",
            headers=TRADIER_HEADERS,
            data=payload_venta,
            timeout=10
        )
        data2     = r2.json()
        orden_venta_id = data2.get("order", {}).get("id")

        return {
            "ok":            True,
            "id":            orden_id,
            "status":        status,
            "venta_id":      orden_venta_id,
            "precio_venta":  precio_venta,
        }
    except Exception as e:
        print(f"Error ejecutar orden Tradier: {e}")
        return {"ok": False, "error": str(e)}

# ═══════════════════════════════════════════════════════════
# TELEGRAM — ENVIAR MENSAJE CON BOTONES
# ═══════════════════════════════════════════════════════════
def enviar_telegram_botones(mensaje, orden_id):
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    reto_activo = _portfolio["reto"]["activo"]
    # Buscar carril disponible — rotación secuencial C1→C2→...→C10→C1
    carril_disponible = None
    if reto_activo:
        turno = _portfolio["reto"].get("turno_actual", 1)
        carriles = _portfolio["reto"]["carriles"]
        # Buscar desde turno_actual en adelante, luego volver al inicio
        orden = list(range(turno - 1, 10)) + list(range(0, turno - 1))
        for idx in orden:
            c = carriles[idx]
            if not c.get("eliminado") and c["posicion"] is None:
                carril_disponible = c["id"]
                break
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    botones = [
        {"text": "✅ EJECUTAR", "callback_data": f"exec:{orden_id}"},
        {"text": "❌ IGNORAR",  "callback_data": f"skip:{orden_id}"},
    ]
    if reto_activo and carril_disponible:
        botones.insert(1, {"text": f"🏆 RETO C{carril_disponible}", "callback_data": f"reto:{orden_id}:{carril_disponible}"})
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
def enviar_senal_con_botones(simbolo, estrategia, hora_label, precio_vela, tipo_opcion, extra=""):
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

    if opcion:
        opcion["subyacente"] = simbolo
        msg = (
            f"{emoji} <b>{estrategia}</b>\n"
            f"<b>Activo:</b> {simbolo}\n"
            f"<b>Hora:</b> {hora_label}\n"
            f"<b>Precio:</b> ${precio:.2f}\n"
            f"{extra}"
            f"<b>Opcion:</b> {opcion['tipo']} ${opcion['strike']:.0f} exp {opcion['expiration']}\n"
            f"<b>Ask:</b> ${opcion['ask']:.2f} | <b>Bid:</b> ${opcion['bid']:.2f}\n"
            f"⚠️ <b>{tipo_opcion} — ¿Ejecutar?</b> (expira en {ORDEN_TIMEOUT_MIN} min)"
        )
        message_id, chat_id = enviar_telegram_botones(msg, orden_id)
        ordenes_pendientes[orden_id] = {
            "opcion":          opcion,
            "estrategia":      estrategia,
            "ts":              datetime.now(pytz.utc),
            "message_id":      message_id,
            "chat_id":         chat_id,
            "texto_original":  msg,
        }
        guardar_ordenes()
        print(f"{simbolo}: señal enviada con botones — {estrategia} | opcion {opcion['tipo']} ${opcion['strike']:.0f}")
    else:
        # Tradier no disponible — alerta simple sin botones pero con toda la info
        enviar_telegram(
            f"{emoji} <b>{estrategia}</b>\n"
            f"<b>Activo:</b> {simbolo}\n"
            f"<b>Hora:</b> {hora_label}\n"
            f"<b>Precio:</b> ${precio:.2f}\n"
            f"{extra}"
            f"⚠️ <b>{tipo_opcion} — Tradier sin datos, evaluar manualmente</b>"
        )
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
                print(f"{simbolo}: sin datos")
            time.sleep(2)
        except Exception as e:
            print(f"Error evaluando {simbolo}: {e}")

# ═══════════════════════════════════════════════════════════
# LOOP PRINCIPAL
# ═══════════════════════════════════════════════════════════
def monitor_loop():
    print("AXIS Breakout Sentinel v8.50 iniciado...")
    while True:
        ahora = datetime.now(EST)
        mins  = ahora.hour * 60 + ahora.minute
        # Solo activo entre 9:30 AM y 4:30 PM EST en días de mercado
        en_horario = es_dia_mercado(ahora) and 570 <= mins <= 990
        if not en_horario:
            time.sleep(300)  # fuera de horario — revisar cada 5 min
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
    mercado = es_dia_mercado(ahora)
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
               width: 100%; max-width: 560px; margin-bottom: 40px; }}
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
    <div class="status-pill">v8.46 · {len(ACTIVOS)} activos</div>
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
  </div>
  <div class="canales-grid">
    {canales_html}
  </div>
  <div class="footer">AXIS Breakout Sentinel v8.50 · {activos_str}</div>
</body>
</html>"""
    from flask import Response
    return Response(html, mimetype="text/html")

@app.route("/test", methods=["GET"])
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
        f"✅ <b>AXIS Breakout Sentinel v8.50</b>\n"
        f"<b>Hora:</b> {ahora.strftime('%A %d/%m/%Y %H:%M EST')}\n"
        f"<b>Mercado:</b> {'Abierto' if es_dia_mercado(ahora) else 'Cerrado'}\n"
        f"<b>1VR:</b> {'ON' if VR1_ON else 'OFF'} | "
        f"<b>RPG:</b> {'ON' if RPG_ON else 'OFF'} | "
        f"<b>GNA:</b> {'ON' if GNA_ON else 'OFF'} | "
        f"<b>GBA:</b> {'ON' if GBA_ON else 'OFF'}\n"
        f"<b>Canales:</b>\n" + "\n".join(lineas_canal)
    )
    return jsonify({"status": "ok"}), 200

@app.route("/reporte", methods=["GET"])
def reporte_manual():
    reporte_horario()
    return jsonify({"status": "reporte enviado"}), 200

@app.route("/activar", methods=["GET"])
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

@app.route("/desactivar", methods=["GET"])
def desactivar():
    simbolo = request.args.get("activo", "SPY").upper()
    if simbolo not in ACTIVOS:
        return jsonify({"error": f"Activo {simbolo} no reconocido"}), 400
    canal[simbolo] = canal_vacio()
    guardar_canales()
    enviar_telegram(f"🔕 <b>Canal desactivado manualmente — {simbolo}</b>")
    return jsonify({"status": "canal desactivado", "activo": simbolo}), 200

@app.route("/apagar", methods=["GET"])
def apagar():
    global SISTEMA_ACTIVO
    SISTEMA_ACTIVO = False
    enviar_telegram("🏁 <b>Sistema apagado manualmente.</b>")
    return jsonify({"status": "apagado"}), 200

@app.route("/estrategia", methods=["GET"])
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




# ═══════════════════════════════════════════════════════════
# TRADIER TEST — verifica token y conexion
# ═══════════════════════════════════════════════════════════
@app.route("/tradier_test", methods=["GET"])
def tradier_test():
    resultados = {}
    
    # Test 1 — precio SPY
    try:
        r = requests.get(
            f"{TRADIER_BASE}/markets/quotes",
            headers=TRADIER_HEADERS,
            params={"symbols": "SPY"},
            timeout=10
        )
        resultados["precio_status"] = r.status_code
        resultados["precio_response"] = r.text[:200]
        if r.status_code == 200:
            data = r.json()
            precio = data.get("quotes", {}).get("quote", {}).get("last")
            resultados["SPY_precio"] = precio
    except Exception as e:
        resultados["precio_error"] = str(e)

    # Test 2 — vencimientos SPY
    try:
        r2 = requests.get(
            f"{TRADIER_BASE}/markets/options/expirations",
            headers=TRADIER_HEADERS,
            params={"symbol": "SPY"},
            timeout=10
        )
        resultados["vencimientos_status"] = r2.status_code
        resultados["vencimientos_response"] = r2.text[:200]
    except Exception as e:
        resultados["vencimientos_error"] = str(e)

    # Test 3 — cuenta
    try:
        r3 = requests.get(
            f"{TRADIER_BASE}/accounts/{TRADIER_ACCOUNT}/balances",
            headers=TRADIER_HEADERS,
            timeout=10
        )
        resultados["cuenta_status"] = r3.status_code
        resultados["cuenta_response"] = r3.text[:200]
    except Exception as e:
        resultados["cuenta_error"] = str(e)

    # Enviar resumen a Telegram
    msg = (
        f"🔧 <b>Tradier Test</b>\n"
        f"<b>Token:</b> {'OK' if resultados.get('precio_status') == 200 else 'ERROR'}\n"
        f"<b>Precio SPY:</b> {resultados.get('SPY_precio', 'N/A')}\n"
        f"<b>Status precio:</b> {resultados.get('precio_status', 'N/A')}\n"
        f"<b>Status vencimientos:</b> {resultados.get('vencimientos_status', 'N/A')}\n"
        f"<b>Status cuenta:</b> {resultados.get('cuenta_status', 'N/A')}\n"
        f"<b>Resp precio:</b> {resultados.get('precio_response', resultados.get('precio_error', 'N/A'))[:100]}"
    )
    enviar_telegram(msg)
    
    return jsonify(resultados), 200

# ═══════════════════════════════════════════════════════════
# RETO MILLONARIO — HELPERS
# ═══════════════════════════════════════════════════════════
def buscar_opcion_reto(opcion_original, presupuesto):
    """
    Busca opción alternativa en ±5 strikes del strike original
    que quepa en el presupuesto del carril (80% capital).
    Vencimiento mínimo 7 días.
    """
    try:
        from datetime import date
        simbolo     = opcion_original["subyacente"]
        tipo        = opcion_original["tipo"].lower()
        strike_orig = float(opcion_original["strike"])
        vencimiento = opcion_original["expiration"]
        precio_max  = presupuesto / 100

        # Verificar que el vencimiento sigue siendo válido (≥7 días)
        hoy = date.today()
        if (date.fromisoformat(vencimiento) - hoy).days < 7:
            r0 = requests.get(
                f"{TRADIER_BASE}/markets/options/expirations",
                headers=TRADIER_HEADERS,
                params={"symbol": simbolo, "includeAllRoots": "true"},
                timeout=10
            )
            fechas = r0.json().get("expirations", {}).get("date", [])
            if isinstance(fechas, str): fechas = [fechas]
            vencimiento = None
            for f in sorted(fechas):
                if (date.fromisoformat(f) - hoy).days >= 7:
                    vencimiento = f
                    break
            if not vencimiento:
                return None

        r = requests.get(
            f"{TRADIER_BASE}/markets/options/chains",
            headers=TRADIER_HEADERS,
            params={"symbol": simbolo, "expiration": vencimiento, "greeks": "false"},
            timeout=10
        )
        opciones = r.json().get("options", {}).get("option", [])
        if not opciones:
            return None

        candidatas = []
        for o in opciones:
            if o.get("option_type") != tipo:
                continue
            strike = float(o.get("strike", 0))
            ask    = float(o.get("ask", 0))
            if ask <= 0 or abs(strike - strike_orig) > 5:
                continue
            if ask <= precio_max:
                candidatas.append(o)

        if not candidatas:
            return None

        mejor = min(candidatas, key=lambda o: abs(float(o.get("strike", 0)) - strike_orig))
        return {
            "symbol":      mejor.get("symbol"),
            "strike":      float(mejor.get("strike", 0)),
            "expiration":  vencimiento,
            "tipo":        tipo.upper(),
            "ask":         float(mejor.get("ask", 0)),
            "bid":         float(mejor.get("bid", 0)),
            "subyacente":  simbolo,
        }
    except Exception as e:
        print(f"Error buscar_opcion_reto: {e}")
        return None

def ejecutar_orden_tradier_contratos(opcion, contratos):
    """Ejecuta compra de N contratos + GTC al doble en Tradier sandbox."""
    try:
        payload_compra = {
            "class":         "option",
            "symbol":        opcion["subyacente"],
            "option_symbol": opcion["symbol"],
            "side":          "buy_to_open",
            "quantity":      str(contratos),
            "type":          "market",
            "duration":      "day",
        }
        r = requests.post(
            f"{TRADIER_BASE}/accounts/{TRADIER_ACCOUNT}/orders",
            headers=TRADIER_HEADERS,
            data=payload_compra,
            timeout=10
        )
        data     = r.json()
        orden_id = data.get("order", {}).get("id")
        status   = data.get("order", {}).get("status", "unknown")

        precio_venta = round(opcion["ask"] * 2, 2)
        payload_venta = {
            "class":         "option",
            "symbol":        opcion["subyacente"],
            "option_symbol": opcion["symbol"],
            "side":          "sell_to_close",
            "quantity":      str(contratos),
            "type":          "limit",
            "price":         str(precio_venta),
            "duration":      "gtc",
        }
        r2 = requests.post(
            f"{TRADIER_BASE}/accounts/{TRADIER_ACCOUNT}/orders",
            headers=TRADIER_HEADERS,
            data=payload_venta,
            timeout=10
        )
        data2         = r2.json()
        orden_venta_id = data2.get("order", {}).get("id")
        return {
            "ok":           True,
            "id":           orden_id,
            "status":       status,
            "venta_id":     orden_venta_id,
            "precio_venta": precio_venta,
        }
    except Exception as e:
        print(f"Error ejecutar_orden_tradier_contratos: {e}")
        return {"ok": False, "error": str(e)}

def recomendar_opcion_claude(opcion_original, capital_carril, presupuesto):
    """Llama a Claude cuando no hay opción en ±5 strikes que quepa en el presupuesto."""
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
            f"Da una recomendación concreta en máximo 3 líneas: qué hacer con este carril "
            f"(esperar, buscar vencimiento más corto, ajustar strike más alejado). "
            f"Sin markdown, en español."
        )
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":    "claude-sonnet-4-5",
                "max_tokens": 150,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=15
        )
        data = r.json()
        if r.status_code == 200:
            return data["content"][0]["text"]
        return "No se pudo obtener recomendación de Claude."
    except Exception as e:
        return f"Error Claude: {str(e)}"

# ═══════════════════════════════════════════════════════════
# PORTFOLIO RESET — limpia posiciones para empezar de cero
# GET /portfolio/reset
# ═══════════════════════════════════════════════════════════
@app.route("/portfolio/reset", methods=["GET"])
def portfolio_reset():
    """Resetea portfolio a cero — solo usar en desarrollo/pruebas."""
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
def portfolio_data():
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    return jsonify({
        "posiciones": _portfolio["posiciones"],
        "historial":  _portfolio["historial"][-20:],
        "reto":       _portfolio["reto"],
    }), 200

@app.route("/portfolio/cerrar", methods=["GET", "POST"])
def portfolio_cerrar():
    """Panic Button — vende al bid en Tradier, cancela GTC, cierra en portfolio."""
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

    # 1 — Obtener bid actual de la opción en Tradier
    bid = get_bid_opcion_tradier(pos["option_symbol"])
    precio_cierre = bid if bid else 0.01  # fallback mínimo si no hay bid

    # 2 — Cancelar orden GTC activa en Tradier
    if pos.get("tradier_gtc_id"):
        cancelar_orden_tradier(pos["tradier_gtc_id"])

    # 3 — Colocar venta limit al bid en Tradier
    if bid and bid > 0:
        vender_opcion_tradier(
            pos["option_symbol"],
            pos["simbolo"],
            pos.get("contratos", 1),
            bid
        )

    # 4 — Registrar cierre en portfolio
    pos_cerrada = cerrar_posicion(pos_id, precio_cierre, motivo)
    if not pos_cerrada:
        return jsonify({"error": "Error cerrando posición"}), 500

    return jsonify({
        "ok":          True,
        "bid_usado":   precio_cierre,
        "posicion":    pos_cerrada,
    }), 200

@app.route("/portfolio/claude", methods=["GET"])
def portfolio_claude():
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    analisis = analizar_portfolio_claude(
        _portfolio["posiciones"],
        _portfolio["reto"]
    )
    return jsonify({"analisis": analisis}), 200

@app.route("/portfolio/reto/activar", methods=["GET"])
def reto_activar():
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    _portfolio["reto"]["activo"] = True
    guardar_portfolio()
    enviar_telegram("🏆 <b>Reto Millonario ACTIVADO</b>\n10 carriles × $200 = $2,000\n¡A duplicar!")
    return jsonify({"ok": True, "reto": _portfolio["reto"]}), 200

@app.route("/portfolio/reto/desactivar", methods=["GET"])
def reto_desactivar():
    global _portfolio
    if _portfolio is None:
        cargar_portfolio()
    _portfolio["reto"]["activo"] = False
    guardar_portfolio()
    enviar_telegram("⏸ <b>Reto Millonario PAUSADO</b>")
    return jsonify({"ok": True}), 200

# ═══════════════════════════════════════════════════════════
# APP WEB — servida desde Railway
# ═══════════════════════════════════════════════════════════
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

# ═══════════════════════════════════════════════════════════
# TELEGRAM WEBHOOK — recibe botones EJECUTAR / IGNORAR
# ═══════════════════════════════════════════════════════════
@app.route("/telegram_webhook", methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"ok": True}), 200

        callback = data.get("callback_query")
        if not callback:
            return jsonify({"ok": True}), 200

        callback_id  = callback.get("id")
        callback_data = callback.get("data", "")
        message_id   = callback.get("message", {}).get("message_id")
        chat_id      = callback.get("message", {}).get("chat", {}).get("id")

        partes = callback_data.split(":")
        # Soporta: "exec:id", "skip:id", "reto:id:carril"
        if len(partes) < 2:
            return jsonify({"ok": True}), 200

        accion   = partes[0]
        orden_id = partes[1]
        carril_id_reto = int(partes[2]) if len(partes) >= 3 else None

        # Responder al callback para quitar el "loading" del boton
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery",
            json={"callback_query_id": callback_id},
            timeout=5
        )

        # Editar mensaje original para quitar botones
        def editar_mensaje(texto):
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText",
                json={
                    "chat_id":    chat_id,
                    "message_id": message_id,
                    "text":       texto,
                    "parse_mode": "HTML",
                },
                timeout=5
            )

        # Agregar recibo DEBAJO del mensaje original sin borrarlo
        def agregar_recibo(recibo):
            texto_original = datos.get("texto_original", "")
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText",
                json={
                    "chat_id":    chat_id,
                    "message_id": message_id,
                    "text":       f"{texto_original}\n\n{recibo}",
                    "parse_mode": "HTML",
                },
                timeout=5
            )

        if accion == "exec":
            datos = ordenes_pendientes.pop(orden_id, None)
            guardar_ordenes()
            if not datos:
                editar_mensaje("⚠️ <b>Orden expirada o ya procesada.</b>")
                return jsonify({"ok": True}), 200
            opcion     = datos["opcion"]
            estrategia = datos.get("estrategia", "AXIS")
            # Ejecutar en Tradier sandbox
            resultado_tradier = ejecutar_orden_tradier(opcion)
            tradier_orden_id = resultado_tradier.get("id") if resultado_tradier["ok"] else None
            tradier_gtc_id   = resultado_tradier.get("venta_id") if resultado_tradier["ok"] else None
            registrar_posicion(opcion, estrategia, opcion["subyacente"], opcion["ask"],
                               tradier_orden_id=tradier_orden_id, tradier_gtc_id=tradier_gtc_id)
            estado_tradier = "✅ Orden enviada a sandbox" if resultado_tradier["ok"] else f"⚠️ Error Tradier: {resultado_tradier.get('error','')}"
            agregar_recibo(
                f"━━━━━━━━━━━━━━━━━━\n"
                f"✅ <b>EJECUTADA</b> — registrada en Portfolio\n"
                f"📋 <b>Opción:</b> {opcion['symbol']}\n"
                f"💰 <b>Costo:</b> ${opcion['ask']*100:.2f} | <b>GTC:</b> ${opcion['ask']*2:.2f}\n"
                f"🏦 <b>Tradier:</b> {estado_tradier}"
            )
            print(f"Posición registrada — {opcion['subyacente']} {opcion['tipo']} ${opcion['strike']} | Tradier: {resultado_tradier['ok']}")

        elif accion == "reto":
            carril_id = carril_id_reto or 1
            datos = ordenes_pendientes.pop(orden_id, None)
            guardar_ordenes()
            if not datos:
                editar_mensaje("⚠️ <b>Orden expirada o ya procesada.</b>")
                return jsonify({"ok": True}), 200
            opcion     = datos["opcion"]
            estrategia = datos.get("estrategia", "AXIS")

            carril = next((c for c in _portfolio["reto"]["carriles"] if c["id"] == carril_id), None)
            if not carril or carril.get("eliminado"):
                agregar_recibo(f"━━━━━━━━━━━━━━━━━━\n⚠️ <b>Carril #{carril_id} no disponible</b>")
                return jsonify({"ok": True}), 200

            costo_1cont = round(opcion["ask"] * 100, 2)

            # PRIMERA RONDA: capital=0 → el costo de esta opción ES el capital inicial
            if carril["capital"] == 0:
                # Asignar capital inicial = costo real de esta opción (1 contrato)
                carril["capital"]         = costo_1cont
                carril["capital_inicial"] = costo_1cont
                contratos  = 1
                presupuesto = costo_1cont
            else:
                # RONDAS SIGUIENTES: solo usa lo acumulado, nunca capital externo
                presupuesto = round(carril["capital"] * 0.80, 2)
                if costo_1cont > presupuesto:
                    opcion_reto = buscar_opcion_reto(opcion, presupuesto)
                    if not opcion_reto:
                        rec_claude = recomendar_opcion_claude(opcion, carril["capital"], presupuesto)
                        agregar_recibo(
                            f"━━━━━━━━━━━━━━━━━━\n"
                            f"⚠️ <b>Capital insuficiente — Carril #{carril_id}</b>\n"
                            f"Capital: ${carril['capital']:.2f} | Presupuesto: ${presupuesto:.2f}\n"
                            f"Costo opción: ${costo_1cont:.2f}\n\n"
                            f"🤖 <b>Claude recomienda:</b>\n{rec_claude}"
                        )
                        return jsonify({"ok": True}), 200
                    opcion = opcion_reto
                    costo_1cont = round(opcion["ask"] * 100, 2)
                contratos = max(1, int(presupuesto // costo_1cont))

            # Avanzar turno al siguiente carril disponible
            carriles = _portfolio["reto"]["carriles"]
            turno_actual = carril_id  # acaba de jugar este carril
            siguiente = None
            orden = list(range(turno_actual, 10)) + list(range(0, turno_actual))
            for idx in orden:
                c = carriles[idx]
                if not c.get("eliminado") and c["posicion"] is None and c["id"] != carril_id:
                    siguiente = c["id"]
                    break
            _portfolio["reto"]["turno_actual"] = siguiente if siguiente else carril_id

            # Ejecutar en Tradier sandbox
            resultado_tradier = ejecutar_orden_tradier_contratos(opcion, contratos)
            tradier_orden_id = resultado_tradier.get("id")    if resultado_tradier["ok"] else None
            tradier_gtc_id   = resultado_tradier.get("venta_id") if resultado_tradier["ok"] else None
            costo_total = round(opcion["ask"] * 100 * contratos, 2)

            registrar_posicion(opcion, estrategia, opcion["subyacente"], opcion["ask"],
                               es_reto=True, carril_id=carril_id, contratos=contratos,
                               tradier_orden_id=tradier_orden_id, tradier_gtc_id=tradier_gtc_id)

            estado_tradier = "✅ Orden enviada a sandbox" if resultado_tradier["ok"] else f"⚠️ Error: {resultado_tradier.get('error','')}"
            es_primera = carril["capital_inicial"] == costo_1cont and carril["ronda"] == 1
            agregar_recibo(
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🏆 <b>RETO C{carril_id} — {'PRIMERA ENTRADA' if es_primera else 'EJECUTADO'}</b>\n"
                f"📋 <b>Opción:</b> {opcion['symbol']}\n"
                f"📊 <b>Contratos:</b> {contratos} × ${opcion['ask']:.2f} = ${costo_total:.2f}\n"
                f"💰 <b>Capital carril:</b> ${carril['capital']:.2f}"
                + (f" (inicial asignado)" if es_primera else f" | Usado: ${costo_total:.2f}") + "\n"
                f"🎯 <b>GTC:</b> ${opcion['ask']*2:.2f} (+100%)\n"
                f"🔄 <b>Siguiente turno:</b> C{_portfolio['reto']['turno_actual']}\n"
                f"🏦 <b>Tradier:</b> {estado_tradier}"
            )
            print(f"RETO C{carril_id} — {contratos}ct {opcion['subyacente']} {opcion['tipo']} ${opcion['strike']} | siguiente: C{_portfolio['reto']['turno_actual']}")

        elif accion == "skip":
            ordenes_pendientes.pop(orden_id, None)
            guardar_ordenes()
            agregar_recibo("━━━━━━━━━━━━━━━━━━\n❌ <b>Orden ignorada</b>")
            print(f"Orden ignorada — ID: {orden_id}")

    except Exception as e:
        print(f"Error webhook: {e}")

    return jsonify({"ok": True}), 200

# ═══════════════════════════════════════════════════════════
# TRADIER PRODUCCION — TEST DATOS HISTORICOS v8.9
# ═══════════════════════════════════════════════════════════
@app.route("/tradier_history_test", methods=["GET"])
def tradier_history_test():
    if not TRADIER_TOKEN_REAL:
        return jsonify({"error": "TRADIER_TOKEN_REAL no configurado en Railway"}), 400

    resultados = {}

    # Test 1 — precio actual SPY (confirma que el token real funciona)
    try:
        r = requests.get(
            f"{TRADIER_BASE_REAL}/markets/quotes",
            headers=TRADIER_HEADERS_REAL,
            params={"symbols": "SPY"},
            timeout=10
        )
        resultados["precio_status"] = r.status_code
        if r.status_code == 200:
            precio = r.json().get("quotes", {}).get("quote", {}).get("last")
            resultados["SPY_precio_real"] = precio
        else:
            resultados["precio_response"] = r.text[:300]
    except Exception as e:
        resultados["error_precio"] = str(e)

    # Test 2 — velas 1h SPY ultimos 7 dias
    try:
        from datetime import date, timedelta
        fecha_fin    = date.today().strftime("%Y-%m-%d")
        fecha_inicio = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")

        r2 = requests.get(
            f"{TRADIER_BASE_REAL}/markets/timesales",
            headers=TRADIER_HEADERS_REAL,
            params={
                "symbol":         "SPY",
                "interval":       "60min",
                "start":          f"{fecha_inicio} 09:00",
                "end":            f"{fecha_fin} 16:00",
                "session_filter": "open",
            },
            timeout=15
        )
        resultados["velas_status"] = r2.status_code
        resultados["velas_raw_sample"] = r2.text[:400]

        if r2.status_code == 200:
            data2 = r2.json()
            series = data2.get("series", {})
            if series and series != "null" and series is not None:
                velas = series.get("data", [])
                if isinstance(velas, dict):
                    velas = [velas]
                resultados["total_velas"]   = len(velas)
                resultados["primera_vela"]  = velas[0]  if velas else None
                resultados["ultima_vela"]   = velas[-1] if velas else None
                resultados["campos"]        = list(velas[0].keys()) if velas else []
            else:
                resultados["nota_velas"] = "series es null — endpoint timesales no disponible con este token"
    except Exception as e:
        resultados["error_velas"] = str(e)

    # Test 3 — historial diario SPY (alternativa si timesales falla)
    try:
        from datetime import date, timedelta
        r3 = requests.get(
            f"{TRADIER_BASE_REAL}/markets/history",
            headers=TRADIER_HEADERS_REAL,
            params={
                "symbol":   "SPY",
                "interval": "daily",
                "start":    (date.today() - timedelta(days=10)).strftime("%Y-%m-%d"),
                "end":      date.today().strftime("%Y-%m-%d"),
            },
            timeout=15
        )
        resultados["history_status"] = r3.status_code
        if r3.status_code == 200:
            data3 = r3.json()
            hist = data3.get("history", {})
            if hist and hist != "null":
                dias = hist.get("day", [])
                if isinstance(dias, dict):
                    dias = [dias]
                resultados["history_dias"]    = len(dias)
                resultados["history_sample"]  = dias[-1] if dias else None
                resultados["history_campos"]  = list(dias[0].keys()) if dias else []
            else:
                resultados["nota_history"] = "history null"
        else:
            resultados["history_response"] = r3.text[:300]
    except Exception as e:
        resultados["error_history"] = str(e)

    # Resumen a Telegram
    token_ok  = resultados.get("precio_status") == 200
    velas_ok  = resultados.get("total_velas", 0) > 0
    hist_ok   = resultados.get("history_dias", 0) > 0
    enviar_telegram(
        f"🔬 <b>Tradier History Test v8.9</b>\n"
        f"<b>Token real:</b> {'✅ OK' if token_ok else '❌ ERROR'}\n"
        f"<b>SPY precio:</b> ${resultados.get('SPY_precio_real', 'N/A')}\n"
        f"<b>Velas 1h (timesales):</b> {'✅ ' + str(resultados.get('total_velas')) + ' velas' if velas_ok else '❌ ' + str(resultados.get('nota_velas', resultados.get('error_velas', 'sin datos')))}\n"
        f"<b>Historial diario:</b> {'✅ ' + str(resultados.get('history_dias')) + ' dias' if hist_ok else '❌ ' + str(resultados.get('nota_history', resultados.get('error_history', 'sin datos')))}\n"
        f"<b>Campos vela:</b> {resultados.get('campos', resultados.get('history_campos', 'N/A'))}"
    )

    return jsonify(resultados), 200

# ═══════════════════════════════════════════════════════════
# VERIFICACION DE VELAS — TwelveData vs Tradier v8.10
# Compara las 7 velas AXIS del lunes 2026-05-11 para SPY
# ═══════════════════════════════════════════════════════════
@app.route("/verificar_velas", methods=["GET"])
def verificar_velas():
    FECHA      = "2026-05-11"
    SIMBOLO    = request.args.get("activo", "SPY").upper()
    resultado  = {"fecha": FECHA, "simbolo": SIMBOLO}

    # ── TWELVEDATA — velas 1h del dia ──
    try:
        r = requests.get(
            "https://api.twelvedata.com/time_series",
            params={
                "symbol":     SIMBOLO,
                "interval":   "1h",
                "outputsize": 50,
                "timezone":   "America/New_York",
                "apikey":     TWELVEDATA_KEY,
            },
            timeout=15
        )
        data = r.json()
        todas = data.get("values", [])

        # Filtrar solo las 7 velas AXIS del 2026-05-11 (horas 9-15 EST = cierre 10:00-16:00)
        velas_axis = []
        for v in todas:
            dt_str = v["datetime"]
            if dt_str.startswith(FECHA):
                hora = int(dt_str[11:13])
                if 9 <= hora <= 15:
                    velas_axis.append({
                        "vela":        f"V{hora - 8}",
                        "hora_cierre": f"{hora + 1}:00 EST",
                        "open":        float(v["open"]),
                        "high":        float(v["high"]),
                        "low":         float(v["low"]),
                        "close":       float(v["close"]),
                    })

        velas_axis.reverse()
        resultado["twelvedata"] = {
            "total_velas_dia": len(velas_axis),
            "velas": velas_axis,
        }
    except Exception as e:
        resultado["twelvedata"] = {"error": str(e)}

    # ── TRADIER PRODUCCION — historial diario del mismo dia ──
    try:
        r2 = requests.get(
            f"{TRADIER_BASE_REAL}/markets/history",
            headers=TRADIER_HEADERS_REAL,
            params={
                "symbol":   SIMBOLO,
                "interval": "daily",
                "start":    FECHA,
                "end":      FECHA,
            },
            timeout=15
        )
        data2 = r2.json()
        hist  = data2.get("history", {})
        dia   = hist.get("day", {}) if hist and hist != "null" else {}
        if isinstance(dia, list):
            dia = dia[0] if dia else {}
        resultado["tradier"] = {
            "fecha":  dia.get("date"),
            "open":   float(dia.get("open",  0)) if dia else None,
            "high":   float(dia.get("high",  0)) if dia else None,
            "low":    float(dia.get("low",   0)) if dia else None,
            "close":  float(dia.get("close", 0)) if dia else None,
            "volume": dia.get("volume"),
            "nota":   "Tradier solo da vela diaria — se compara open V1 y close V7 de TwelveData",
        }
    except Exception as e:
        resultado["tradier"] = {"error": str(e)}

    # ── COMPARACION DIRECTA ──
    try:
        td = resultado.get("twelvedata", {})
        tr = resultado.get("tradier", {})
        v1 = next((v for v in td.get("velas", []) if v["vela"] == "V1"), None)
        v7 = next((v for v in td.get("velas", []) if v["vela"] == "V7"), None)

        if v1 and v7 and tr.get("open"):
            diff_open  = round(abs(v1["open"]  - tr["open"]),  2)
            diff_close = round(abs(v7["close"] - tr["close"]), 2)
            resultado["comparacion"] = {
                "open_V1_twelve":        v1["open"],
                "open_diario_tradier":   tr["open"],
                "diferencia_open":       diff_open,
                "close_V7_twelve":       v7["close"],
                "close_diario_tradier":  tr["close"],
                "diferencia_close":      diff_close,
                "veredicto": "✅ DATOS CONSISTENTES" if diff_open < 0.10 and diff_close < 0.10 else "⚠️ REVISAR — diferencia mayor a $0.10",
            }
        else:
            resultado["comparacion"] = {"nota": "Datos insuficientes para comparar"}
    except Exception as e:
        resultado["comparacion"] = {"error": str(e)}

    # ── RESUMEN A TELEGRAM ──
    try:
        comp  = resultado.get("comparacion", {})
        velas = resultado.get("twelvedata", {}).get("velas", [])
        lineas = "\n".join(
            f"  {v['vela']} {v['hora_cierre']} O:{v['open']:.2f} H:{v['high']:.2f} L:{v['low']:.2f} C:{v['close']:.2f}"
            for v in velas
        )
        tr = resultado.get("tradier", {})
        enviar_telegram(
            f"🔍 <b>Verificación Velas {SIMBOLO} — {FECHA}</b>\n\n"
            f"<b>TwelveData — 7 velas AXIS:</b>\n{lineas}\n\n"
            f"<b>Tradier diario:</b> O:{tr.get('open')} H:{tr.get('high')} L:{tr.get('low')} C:{tr.get('close')}\n\n"
            f"<b>Veredicto:</b> {comp.get('veredicto', comp.get('nota', 'sin datos'))}\n"
            f"Δ Open: ${comp.get('diferencia_open', 'N/A')} | Δ Close: ${comp.get('diferencia_close', 'N/A')}"
        )
    except Exception as e:
        print(f"Error Telegram verificar_velas: {e}")

    return jsonify(resultado), 200

# ═══════════════════════════════════════════════════════════
# V7 ANTICIPADA — AAPL, BA, GLD (v8.11)
# -------------------------------------------------------
# DECISION MVP: thread independiente para no tocar monitor_loop.
# Logica:
#   3:58 EST → evalua V7 con precio disponible → dispara alerta si hay señal
#   4:00 EST → lee cierre real → corrige v7_close interno → sin alerta
# SPY no aplica — sigue evaluandose en monitor_loop a las 4:01 EST
# ═══════════════════════════════════════════════════════════
ACTIVOS_V7_ANTICIPADA     = ["AAPL", "BA", "GLD", "NVDA", "AMZN", "GOOG", "META"]
ACTIVOS_V7_ANTICIPADA_SPY = ["SPY"]

def enviar_resumen_diario(ahora):
    """Envía resumen del día a Telegram a las 4:16 PM EST."""
    try:
        if _portfolio is None:
            cargar_portfolio()

        fecha_hoy = ahora.strftime("%Y-%m-%d")

        # Señales del día
        señales_lineas = []
        for activo in ACTIVOS:
            ed = estado_dia.get(activo, {})
            if ed.get("fecha") != fecha_hoy:
                continue
            disparadas = []
            if ed.get("vr1_fired"):  disparadas.append("1VR")
            if ed.get("rpg_fired"):  disparadas.append("RPG")
            if ed.get("gna_fired"):  disparadas.append("GNA")
            if ed.get("gba_fired"):  disparadas.append("GBA")
            if ed.get("pm40_fired"): disparadas.append("PM40")
            if ed.get("4ps_fired"):  disparadas.append("4PS")
            if disparadas:
                señales_lineas.append(f"  • {activo}: {', '.join(disparadas)}")

        # Posiciones cerradas hoy
        cerradas_hoy = [
            p for p in _portfolio["historial"]
            if str(p.get("ts_cierre", "")).startswith(fecha_hoy)
        ]
        pl_dia = sum(p.get("pl_usd", 0) or 0 for p in cerradas_hoy)
        wins   = sum(1 for p in cerradas_hoy if (p.get("pl_usd", 0) or 0) > 0)

        # Estado reto
        reto     = _portfolio["reto"]
        cap_reto = sum(c["capital"] for c in reto["carriles"] if not c.get("eliminado"))
        vivos    = sum(1 for c in reto["carriles"] if not c.get("eliminado"))
        elim     = sum(1 for c in reto["carriles"] if c.get("eliminado"))

        # Historial win rate global
        hist_total = len(_portfolio["historial"])
        hist_wins  = sum(1 for p in _portfolio["historial"] if (p.get("pl_usd", 0) or 0) > 0)
        wr         = f"{round(hist_wins/hist_total*100,1)}%" if hist_total else "—"

        # Posiciones abiertas
        pos_abiertas = len(_portfolio["posiciones"])

        emoji_pl = "✅" if pl_dia >= 0 else "🔴"

        msg = (
            f"📊 <b>AXIS — Resumen {ahora.strftime('%m/%d/%Y')}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>Señales del día:</b>\n"
            + (("\n".join(señales_lineas) + "\n") if señales_lineas else "  Sin señales hoy\n")
            + f"\n<b>Operaciones cerradas hoy:</b> {len(cerradas_hoy)}"
            + (f" ({wins}W / {len(cerradas_hoy)-wins}L)" if cerradas_hoy else "")
            + f"\n{emoji_pl} <b>P&L del día:</b> ${pl_dia:+.2f}\n"
            f"📈 <b>Posiciones abiertas:</b> {pos_abiertas}\n\n"
            f"<b>Win Rate global:</b> {wr} ({hist_wins}/{hist_total})\n\n"
            f"🏆 <b>Reto Millonario:</b> {'Activo' if reto['activo'] else 'Inactivo'}\n"
            f"  Carriles vivos: {vivos}/10 | Eliminados: {elim}\n"
            f"  Capital total: ${cap_reto:,.2f}\n\n"
            f"<i>AXIS v8.50 | {ahora.strftime('%H:%M EST')}</i>"
        )
        enviar_telegram(msg)
        print(f"Resumen diario enviado — {fecha_hoy}")
    except Exception as e:
        print(f"Error enviar_resumen_diario: {e}")

def loop_v7_anticipada():
    """
    Thread independiente que vigila horarios V7 para todos los activos.
    - AAPL/BA/GLD/NVDA/AMZN/GOOG/META: evalúa 3:58 EST, corrige 4:00 EST
    - SPY: evalúa 4:14 EST, corrige 4:16 EST (cierra 4:15 PM)
    """
    print("Thread V7 anticipada iniciado...")
    ejecutado_358  = set()
    ejecutado_400  = set()
    ejecutado_414  = set()
    ejecutado_416  = set()
    fecha_actual   = None

    while True:
        try:
            ahora     = datetime.now(EST)
            fecha_hoy = ahora.strftime("%Y-%m-%d")

            # Reset diario
            if fecha_hoy != fecha_actual:
                fecha_actual  = fecha_hoy
                ejecutado_358 = set()
                ejecutado_400 = set()
                ejecutado_414 = set()
                ejecutado_416 = set()

            if es_dia_mercado(ahora):
                # 3:58 EST — V7 anticipada AAPL/BA/GLD/NVDA/AMZN/GOOG/META + HED
                if ahora.hour == 15 and ahora.minute == 58:
                    for simbolo in ACTIVOS_V7_ANTICIPADA:
                        if simbolo not in ejecutado_358:
                            evaluar_v7_anticipada(simbolo)
                            evaluar_hed(simbolo)
                            ejecutado_358.add(simbolo)

                # 4:00 EST — correccion cierre real AAPL/BA/GLD/NVDA/AMZN/GOOG/META
                if ahora.hour == 16 and ahora.minute == 0:
                    for simbolo in ACTIVOS_V7_ANTICIPADA:
                        if simbolo not in ejecutado_400:
                            corregir_cierre_v7(simbolo)
                            ejecutado_400.add(simbolo)

                # 4:14 EST — V7 anticipada SPY + HED
                if ahora.hour == 16 and ahora.minute == 14:
                    for simbolo in ACTIVOS_V7_ANTICIPADA_SPY:
                        if simbolo not in ejecutado_414:
                            evaluar_v7_anticipada(simbolo)
                            evaluar_hed(simbolo)
                            ejecutado_414.add(simbolo)

                # 4:16 EST — correccion cierre real SPY + resumen diario
                if ahora.hour == 16 and ahora.minute == 16:
                    for simbolo in ACTIVOS_V7_ANTICIPADA_SPY:
                        if simbolo not in ejecutado_416:
                            corregir_cierre_v7(simbolo)
                            ejecutado_416.add(simbolo)
                    # Resumen diario — se ejecuta una sola vez al cierre
                    if "resumen" not in ejecutado_416:
                        ejecutado_416.add("resumen")
                        enviar_resumen_diario(ahora)

            time.sleep(30)
        except Exception as e:
            print(f"Error loop V7 anticipada: {e}")
            time.sleep(30)

def evaluar_v7_anticipada(simbolo):
    """Evalua V7 anticipada para activos no-SPY (3:58) y SPY (4:14)."""
    ahora = datetime.now(EST)
    print(f"V7 anticipada {simbolo} — {ahora.strftime('%H:%M EST')}")
    try:
        velas = get_velas(simbolo, outputsize=50)
        if velas:
            # SPY usa hora 16:15 (4:15 cierre), resto 16:01
            hora_eval = 16
            evaluar_activo(simbolo, velas, ahora.replace(hour=hora_eval, minute=1))
        else:
            print(f"V7 anticipada {simbolo}: sin datos")
    except Exception as e:
        print(f"Error V7 anticipada {simbolo}: {e}")

def corregir_cierre_v7(simbolo):
    """Lee el cierre real de V7 y actualiza v7_ayer_close para mañana. Sin alerta."""
    print(f"Correccion cierre V7 {simbolo} — {datetime.now(EST).strftime('%H:%M EST')}")
    try:
        velas = get_velas(simbolo, outputsize=10)
        if not velas:
            return
        fecha_hoy = datetime.now(EST).strftime("%Y-%m-%d")
        for v in velas:
            dt_str = v["datetime"]
            if dt_str.startswith(fecha_hoy) and int(dt_str[11:13]) == 15:
                cierre_real = float(v["close"])
                estado_dia[simbolo]["v7_ayer_close"] = cierre_real
                print(f"Correccion V7 {simbolo}: cierre real ${cierre_real:.2f} registrado")
                return
        print(f"Correccion V7 {simbolo}: vela 15h no encontrada aun")
    except Exception as e:
        print(f"Error correccion V7 {simbolo}: {e}")

def evaluar_hed(simbolo):
    """
    HED — Hanger en Diario
    Evalúa si la vela del día forma una shooting star a las 3:58:01 EST
    Ejecución automática sin botón si cumple condiciones
    """
    try:
        velas = get_velas(simbolo, outputsize=2)
        if not velas:
            return
        # Tomar la vela del día actual (última)
        v = velas[-1]
        v_open  = float(v["open"])
        v_close = float(v["close"])
        v_high  = float(v["high"])
        v_low   = float(v["low"])

        cuerpo   = abs(v_close - v_open)
        mecha_sup = v_high - max(v_close, v_open)
        mecha_inf = min(v_close, v_open) - v_low
        rango     = v_high - v_low

        # No doji
        if cuerpo <= 0 or rango <= 0:
            print(f"{simbolo} HED: doji — no válida")
            return

        # Shooting star mínima: mecha_sup >= 1.25 × cuerpo AND mecha_inf <= 25% cuerpo
        es_shooting_star = (
            mecha_sup >= 1.25 * cuerpo and
            mecha_inf <= 0.25 * cuerpo
        )

        if not es_shooting_star:
            print(f"{simbolo} HED: no shooting star — mecha_sup={mecha_sup:.2f} cuerpo={cuerpo:.2f}")
            return

        # Calcular SMAs
        velas_hist = get_velas(simbolo, outputsize=60)
        closes = [float(x["close"]) for x in velas_hist]
        sma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
        sma40 = sum(closes[-40:]) / 40 if len(closes) >= 40 else None

        # Condición A: SMA20 > SMA40
        cond_a = sma20 and sma40 and sma20 > sma40

        # Condición B: dentro RCB entre techo y 30% hacia la media
        ahora_dt = datetime.now(EST)
        techo_h  = calcular_techo_canal(simbolo, ahora_dt)
        _, mitad_h = calcular_piso_mitad_canal(simbolo, ahora_dt)
        c_hed    = canal[simbolo]
        zona_30_h = None
        if techo_h and mitad_h:
            zona_30_h = techo_h - (techo_h - mitad_h) * 0.30
        cond_b = (
            c_hed["on"] and not c_hed["apagado"] and c_hed["p3"] is not None
            and techo_h is not None and zona_30_h is not None
            and zona_30_h <= v_close <= techo_h
        )

        if not (cond_a or cond_b):
            print(f"{simbolo} HED: shooting star pero sin condición adicional")
            return

        # Buscar opción PUT automáticamente
        precio_actual = get_precio_tradier(simbolo) or v_close
        opcion = get_opcion_tradier(simbolo, "put", precio_actual)
        if not opcion:
            enviar_telegram(f"⚠️ <b>HED {simbolo}</b> — Shooting star detectada pero sin opción disponible")
            return

        # Ejecutar automáticamente sin botón
        opcion["subyacente"] = simbolo
        resultado = ejecutar_orden_tradier(opcion)

        color_vela = "🟢" if v_close > v_open else "🔴"
        cond_str = "RCB 30%" if cond_b else f"SMA20({sma20:.2f})>SMA40({sma40:.2f})"

        if resultado["ok"]:
            enviar_telegram(
                f"🕯 <b>HED — SHOOTING STAR DIARIA</b>\n"
                f"<b>Activo:</b> {simbolo} {color_vela}\n"
                f"<b>Condición:</b> {cond_str}\n"
                f"<b>Mecha sup:</b> {mecha_sup:.2f} | <b>Cuerpo:</b> {cuerpo:.2f} | ratio: {mecha_sup/cuerpo:.2f}×\n"
                f"<b>Opción PUT:</b> ${opcion['strike']:.0f} exp {opcion['expiration']}\n"
                f"✅ <b>EJECUTADA automáticamente</b> | ID: {resultado['id']}\n"
                f"📈 Venta GTC: ${resultado['precio_venta']:.2f}"
            )
            print(f"{simbolo} HED ejecutada — ID: {resultado['id']}")
        else:
            enviar_telegram(
                f"⚠️ <b>HED {simbolo}</b> — Shooting star detectada\n"
                f"❌ Error al ejecutar: {resultado.get('error','desconocido')}"
            )
    except Exception as e:
        print(f"Error evaluar_hed {simbolo}: {e}")


# ═══════════════════════════════════════════════════════════
# TEST TRADIER 30MIN — v8.13
# Pide velas de 30min a Tradier produccion para SPY
# Las une en pares para construir velas AXIS de 1h
# Compara contra valores reales de TradingView
# ═══════════════════════════════════════════════════════════
@app.route("/test_tradier_30min", methods=["GET"])
def test_tradier_30min():
    FECHA   = "2026-05-11"
    SIMBOLO = request.args.get("activo", "SPY").upper()
    resultado = {"fecha": FECHA, "simbolo": SIMBOLO}

    # Valores de referencia TV (Pine Script 30min) para SPY 05/11/2026
    TV_REF = {
        "V1": {"O":738.49, "H":739.21, "L":734.86, "C":735.10},
        "V2": {"O":735.11, "H":736.36, "L":733.54, "C":733.80},
        "V3": {"O":733.78, "H":734.04, "L":731.84, "C":732.49},
        "V4": {"O":732.51, "H":733.48, "L":731.83, "C":732.10},
        "V5": {"O":732.10, "H":735.20, "L":732.04, "C":735.07},
        "V6": {"O":735.06, "H":736.56, "L":734.66, "C":735.99},
        "V7": {"O":736.00, "H":738.84, "L":735.99, "C":738.14},
    }

    try:
        # Pedir timesales de 15min (el intervalo mas fino disponible en Tradier)
        # Intentamos 15min primero, luego 5min si falla
        velas_raw = []
        for intervalo in ["15min", "5min"]:
            r = requests.get(
                f"{TRADIER_BASE_REAL}/markets/timesales",
                headers=TRADIER_HEADERS_REAL,
                params={
                    "symbol":         SIMBOLO,
                    "interval":       intervalo,
                    "start":          f"{FECHA} 09:00",
                    "end":            f"{FECHA} 16:00",
                    "session_filter": "open",
                },
                timeout=15
            )
            resultado[f"status_{intervalo}"] = r.status_code
            resultado[f"raw_{intervalo}"]    = r.text[:200]

            if r.status_code == 200:
                data = r.json()
                series = data.get("series")
                if series and series != "null" and series is not None:
                    velas_raw = series.get("data", [])
                    if isinstance(velas_raw, dict):
                        velas_raw = [velas_raw]
                    resultado["intervalo_usado"] = intervalo
                    resultado["total_barras"]    = len(velas_raw)
                    resultado["muestra"]         = velas_raw[:3]
                    break
                else:
                    resultado[f"nota_{intervalo}"] = "series null"

        if not velas_raw:
            resultado["error"] = "Tradier no devolvio datos intraday con ningun intervalo"
            enviar_telegram(f"❌ <b>Test Tradier 30min</b>\nNo hay datos intraday para {SIMBOLO}")
            return jsonify(resultado), 200

        # ── Agrupacion correcta de barras 15min en velas AXIS ──
        # AXIS empieza a las 10:00 EST — ignorar barras 9:30 y 9:45 (pre-AXIS)
        # V1 = barras 10:00, 10:15, 10:30, 10:45 (la vela cierra cuando empieza V2)
        # V2 = barras 11:00, 11:15, 11:30, 11:45
        # ...
        # V7 = barras 16:00 (solo el cierre final)
        #
        # Regla: barra de HH:MM pertenece a vela AXIS numero (HH - 9)
        # Solo horas 10, 11, 12, 13, 14, 15 — ignorar hora 9 completa
        from collections import defaultdict
        from datetime import datetime

        grupos = defaultdict(list)

        for b in velas_raw:
            try:
                ts_str = b["time"].replace("T", " ")
                dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                h  = dt.hour

                # Ignorar barras pre-AXIS (hora 9 = 9:30, 9:45)
                if h < 10:
                    continue

                # Ignorar barras post-AXIS (hora > 16)
                if h > 16:
                    continue

                # Asignar vela AXIS — barra de hora H va a vela (H - 9)
                vela_map = {10:"V1", 11:"V2", 12:"V3", 13:"V4", 14:"V5", 15:"V6", 16:"V7"}
                vela = vela_map.get(h)
                if vela:
                    grupos[vela].append(b)
            except Exception as ex:
                resultado.setdefault("parse_errors", []).append(str(ex))
                continue

        # Construir velas AXIS de 1h
        velas_axis = {}
        for vela, barras in sorted(grupos.items()):
            if not barras:
                continue
            o = float(barras[0]["open"])
            h = max(float(b["high"])  for b in barras)
            l = min(float(b["low"])   for b in barras)
            c = float(barras[-1]["close"])
            velas_axis[vela] = {"O":o, "H":h, "L":l, "C":c, "barras":len(barras)}

        resultado["velas_axis"] = velas_axis

        # Comparar contra TV
        comparacion = {}
        for vela, vals in velas_axis.items():
            if vela not in TV_REF:
                continue
            ref = TV_REF[vela]
            diffs = {
                "dO": round(abs(vals["O"]-ref["O"]), 2),
                "dH": round(abs(vals["H"]-ref["H"]), 2),
                "dL": round(abs(vals["L"]-ref["L"]), 2),
                "dC": round(abs(vals["C"]-ref["C"]), 2),
            }
            max_diff = max(diffs.values())
            diffs["max_diff"] = max_diff
            diffs["estado"]   = "✅ OK" if max_diff < 0.15 else ("⚠️ DIFF" if max_diff < 1.0 else "❌ ERROR")
            comparacion[vela] = diffs

        resultado["comparacion_vs_TV"] = comparacion

        # Resumen Telegram
        lineas = []
        for vela in ["V1","V2","V3","V4","V5","V6","V7"]:
            if vela in velas_axis:
                v   = velas_axis[vela]
                cmp = comparacion.get(vela, {})
                lineas.append(
                    f"<b>{vela}</b> O:{v['O']:.2f} H:{v['H']:.2f} L:{v['L']:.2f} C:{v['C']:.2f} "
                    f"| Δmax:{cmp.get('max_diff','?')} {cmp.get('estado','')}"
                )

        enviar_telegram(
            f"🔬 <b>Test Tradier 30min — {SIMBOLO} {FECHA}</b>\n"
            f"<b>Intervalo:</b> {resultado.get('intervalo_usado','ninguno')}\n"
            f"<b>Barras totales:</b> {resultado.get('total_barras',0)}\n\n" +
            "\n".join(lineas)
        )

    except Exception as e:
        resultado["error"] = str(e)
        enviar_telegram(f"❌ <b>Test Tradier 30min error:</b> {str(e)}")

    return jsonify(resultado), 200

# ═══════════════════════════════════════════════════════════
# COMPARAR FUENTES — v8.16
# Compara TwelveData vs Tradier 15min para HOY
# Muestra OHLC lado a lado por vela AXIS
# ═══════════════════════════════════════════════════════════
@app.route("/comparar_fuentes", methods=["GET"])
def comparar_fuentes():
    from datetime import date, datetime
    from collections import defaultdict

    SIMBOLO = request.args.get("activo", "SPY").upper()
    FECHA   = date.today().strftime("%Y-%m-%d")
    resultado = {"fecha": FECHA, "simbolo": SIMBOLO}

    # ── 1. TwelveData — velas 1h de hoy ──
    try:
        r = requests.get(
            "https://api.twelvedata.com/time_series",
            params={
                "symbol":     SIMBOLO,
                "interval":   "1h",
                "outputsize": 20,
                "timezone":   "America/New_York",
                "apikey":     TWELVEDATA_KEY,
            },
            timeout=15
        )
        data = r.json()
        velas_td = {}
        for v in data.get("values", []):
            if not v["datetime"].startswith(FECHA):
                continue
            h = int(v["datetime"][11:13])
            # TwelveData marca hora de apertura — mapeamos a vela AXIS
            # h=9 → V1(9:30-10:00), h=10→V2, h=11→V3, h=12→V4, h=13→V5, h=14→V6, h=15→V7
            vela_map = {9:"V1",10:"V2",11:"V3",12:"V4",13:"V5",14:"V6",15:"V7"}
            vela = vela_map.get(h)
            if vela:
                velas_td[vela] = {
                    "O": round(float(v["open"]),  2),
                    "H": round(float(v["high"]),  2),
                    "L": round(float(v["low"]),   2),
                    "C": round(float(v["close"]), 2),
                }
        resultado["twelvedata"] = velas_td
    except Exception as e:
        resultado["twelvedata_error"] = str(e)

    # ── 2. Tradier 15min — construir velas AXIS ──
    try:
        r2 = requests.get(
            f"{TRADIER_BASE_REAL}/markets/timesales",
            headers=TRADIER_HEADERS_REAL,
            params={
                "symbol":         SIMBOLO,
                "interval":       "15min",
                "start":          f"{FECHA} 09:00",
                "end":            f"{FECHA} 16:30",
                "session_filter": "open",
            },
            timeout=15
        )
        data2  = r2.json()
        series = data2.get("series")
        barras = []
        if series and series != "null":
            barras = series.get("data", [])
            if isinstance(barras, dict):
                barras = [barras]

        # Agrupar barras en velas AXIS
        # V1 = 9:30-10:00 (barras 9:30, 9:45)
        # V2 = 10:00-11:00 (barras 10:00,10:15,10:30,10:45)
        # V3-V7 = igual, cada hora completa
        grupos = defaultdict(list)
        for b in barras:
            ts_str = b["time"].replace("T"," ")
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            h, m = dt.hour, dt.minute
            if h == 9 and m in (30, 45):
                grupos["V1"].append(b)
            elif h == 10: grupos["V2"].append(b)
            elif h == 11: grupos["V3"].append(b)
            elif h == 12: grupos["V4"].append(b)
            elif h == 13: grupos["V5"].append(b)
            elif h == 14: grupos["V6"].append(b)
            elif h == 15: grupos["V7"].append(b)

        velas_tr = {}
        for vela, bs in sorted(grupos.items()):
            if not bs: continue
            velas_tr[vela] = {
                "O": round(float(bs[0]["open"]),              2),
                "H": round(max(float(b["high"]) for b in bs), 2),
                "L": round(min(float(b["low"])  for b in bs), 2),
                "C": round(float(bs[-1]["close"]),            2),
                "barras": len(bs),
            }
        resultado["tradier_15min"] = velas_tr
    except Exception as e:
        resultado["tradier_error"] = str(e)

    # ── 3. Comparacion lado a lado ──
    comparacion = {}
    velas_td = resultado.get("twelvedata", {})
    velas_tr = resultado.get("tradier_15min", {})
    todas = sorted(set(list(velas_td.keys()) + list(velas_tr.keys())))

    for vela in todas:
        td = velas_td.get(vela)
        tr = velas_tr.get(vela)
        if not td or not tr:
            comparacion[vela] = {"nota": "falta en una fuente"}
            continue
        diffs = {campo: round(abs(td[campo] - tr[campo]), 2) for campo in ["O","H","L","C"]}
        max_d = max(diffs.values())
        coinciden = max_d < 0.15
        comparacion[vela] = {
            "TD_O": td["O"], "TR_O": tr["O"], "dO": diffs["O"],
            "TD_H": td["H"], "TR_H": tr["H"], "dH": diffs["H"],
            "TD_L": td["L"], "TR_L": tr["L"], "dL": diffs["L"],
            "TD_C": td["C"], "TR_C": tr["C"], "dC": diffs["C"],
            "max_diff": max_d,
            "estado": "✅ OK" if coinciden else ("⚠️ DIFF" if max_d < 1.0 else "❌ ERROR"),
        }
    resultado["comparacion"] = comparacion

    # ── 4. Veredicto final ──
    errores   = sum(1 for v in comparacion.values() if isinstance(v, dict) and v.get("estado","").startswith("❌"))
    warnings  = sum(1 for v in comparacion.values() if isinstance(v, dict) and v.get("estado","").startswith("⚠️"))
    oks       = sum(1 for v in comparacion.values() if isinstance(v, dict) and v.get("estado","").startswith("✅"))
    resultado["veredicto"] = f"✅ {oks} OK | ⚠️ {warnings} DIFF | ❌ {errores} ERROR"

    # ── 5. Telegram ──
    lineas = []
    for vela in todas:
        c = comparacion.get(vela, {})
        if "nota" in c:
            lineas.append(f"<b>{vela}</b>: sin datos completos")
            continue
        td = velas_td.get(vela, {})
        tr = velas_tr.get(vela, {})
        lineas.append(
            f"<b>{vela}</b> {c.get('estado','')}\n"
            f"  TD: O{td['O']} H{td['H']} L{td['L']} C{td['C']}\n"
            f"  TR: O{tr['O']} H{tr['H']} L{tr['L']} C{tr['C']}\n"
            f"  Δmax: ${c.get('max_diff','?')}"
        )

    enviar_telegram(
        f"🔬 <b>Comparacion Fuentes {SIMBOLO} — {FECHA}</b>\n"
        f"<b>Resultado:</b> {resultado['veredicto']}\n\n" +
        "\n".join(lineas)
    )

    return jsonify(resultado), 200

# ═══════════════════════════════════════════════════════════
# RUTA /velas — Dashboard consume datos Tradier via Railway
# ═══════════════════════════════════════════════════════════
@app.route("/velas", methods=["GET"])
def ruta_velas():
    simbolo = request.args.get("simbolo", "SPY").upper()
    velas   = get_velas(simbolo, outputsize=280)
    if not velas:
        return jsonify({"error": f"Sin datos para {simbolo}"}), 500

    # Señales que Railway ya disparó hoy — dashboard las dibuja directamente
    # sin recalcular condiciones (SMAs, canales) que pueden diferir
    ed = estado_dia.get(simbolo, {})
    senales_hoy = []
    fecha_hoy = datetime.now(EST).strftime("%Y-%m-%d")
    if ed.get("fecha") == fecha_hoy:
        if ed.get("vr1_fired"):
            senales_hoy.append({"tipo": "1VR",  "fecha": fecha_hoy})
        if ed.get("rpg_fired"):
            senales_hoy.append({"tipo": "RPG",  "fecha": fecha_hoy})
        if ed.get("gna_fired"):
            senales_hoy.append({"tipo": "GNA",  "fecha": fecha_hoy})
        if ed.get("gba_fired"):
            senales_hoy.append({"tipo": "GBA",  "fecha": fecha_hoy})
        if ed.get("pm40_fired"):
            senales_hoy.append({"tipo": "PM40", "fecha": fecha_hoy})
        if ed.get("4ps_fired"):
            senales_hoy.append({"tipo": "4PS",  "fecha": fecha_hoy})

    return jsonify({
        "simbolo":     simbolo,
        "fuente":      "Tradier 15min",
        "total":       len(velas),
        "velas":       velas,
        "senales_hoy": senales_hoy,
    }), 200

# ═══════════════════════════════════════════════════════════
# SYSTEM STATUS — diagnóstico completo del sistema
# GET /status
# ═══════════════════════════════════════════════════════════
@app.route("/status", methods=["GET"])
def system_status():
    from datetime import date
    ahora    = datetime.now(EST)
    hoy      = date.today()

    # ── Threads activos
    import threading
    threads_vivos = [t.name for t in threading.enumerate()]

    # ── Estado de mercado
    mercado_abierto = es_dia_mercado(ahora)

    # ── Canales
    canales_resumen = {}
    for a in ACTIVOS:
        c = canal[a]
        canales_resumen[a] = {
            "on":      c["on"],
            "tipo":    "RCB" if (c["on"] and c.get("p3")) else "CNF" if c["on"] else "OFF",
            "p1":      c["p1"]["high"] if c.get("p1") else None,
            "p2":      c.get("p2_actual_high"),
        }

    # ── Estado día (señales de hoy)
    señales_hoy = {}
    for a in ACTIVOS:
        ed = estado_dia.get(a, {})
        señales_hoy[a] = {
            "fecha":       ed.get("fecha"),
            "1VR":         ed.get("vr1_fired", False),
            "RPG":         ed.get("rpg_fired", False),
            "GNA":         ed.get("gna_fired", False),
            "GBA":         ed.get("gba_fired", False),
            "PM40":        ed.get("pm40_fired", False),
            "4PS":         ed.get("4ps_fired", False),
        }

    # ── Portfolio
    if _portfolio is None:
        cargar_portfolio()
    pos_abiertas   = len(_portfolio["posiciones"])
    pos_historial  = len(_portfolio["historial"])
    reto           = _portfolio["reto"]
    carriles_vivos = [c for c in reto["carriles"] if not c.get("eliminado")]
    carriles_elim  = [c for c in reto["carriles"] if c.get("eliminado")]
    carriles_en_pos = [c for c in carriles_vivos if c["posicion"]]

    reto_resumen = {
        "activo":         reto["activo"],
        "turno_actual":   reto.get("turno_actual", 1),
        "carriles_vivos": len(carriles_vivos),
        "carriles_elim":  len(carriles_elim),
        "carriles_en_pos": len(carriles_en_pos),
        "capital_total":  round(sum(c["capital"] for c in carriles_vivos), 2),
        "detalle": [
            {
                "id":              c["id"],
                "capital":         c["capital"],
                "capital_inicial": c.get("capital_inicial", 0),
                "ronda":           c["ronda"],
                "en_posicion":     c["posicion"] is not None,
                "eliminado":       c.get("eliminado", False),
                "multiplicador":   round(c["capital"] / c["capital_inicial"], 2) if c.get("capital_inicial", 0) > 0 else None,
            }
            for c in reto["carriles"]
        ]
    }

    # ── Órdenes pendientes
    ordenes_vivas = []
    for oid, d in ordenes_pendientes.items():
        try:
            ts   = d["ts"]
            mins = round((datetime.now(pytz.utc) - ts).total_seconds() / 60, 1)
            ordenes_vivas.append({
                "id":       oid,
                "activo":   d["opcion"].get("subyacente"),
                "tipo":     d["opcion"].get("tipo"),
                "strike":   d["opcion"].get("strike"),
                "mins_ago": mins,
            })
        except:
            pass

    # ── Archivos /data
    archivos_data = {}
    for fname in ["axis_canales.json", "axis_portfolio.json", "axis_ordenes.json"]:
        path = f"/data/{fname}"
        try:
            size = os.path.getsize(path)
            archivos_data[fname] = f"{size} bytes ✅"
        except:
            archivos_data[fname] = "NO ENCONTRADO ❌"

    return jsonify({
        "sistema":          "AXIS Breakout Sentinel v8.50",
        "hora_est":         ahora.strftime("%Y-%m-%d %H:%M:%S EST"),
        "mercado":          "ABIERTO ✅" if mercado_abierto else "CERRADO ⏸",
        "threads":          threads_vivos,
        "activos":          ACTIVOS,
        "canales":          canales_resumen,
        "señales_hoy":      señales_hoy,
        "portfolio": {
            "posiciones_abiertas": pos_abiertas,
            "historial_total":     pos_historial,
            "posiciones":          _portfolio["posiciones"],
        },
        "reto":             reto_resumen,
        "ordenes_pendientes": ordenes_vivas,
        "archivos_data":    archivos_data,
    }), 200
# GET /cotizar_opciones
# ═══════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════
# ESTADÍSTICAS — win rate por estrategia, activo, vela, hora
# GET /estadisticas
# ═══════════════════════════════════════════════════════════
@app.route("/estadisticas", methods=["GET"])
def estadisticas():
    if _portfolio is None:
        cargar_portfolio()

    historial = _portfolio.get("historial", [])
    if not historial:
        return jsonify({"mensaje": "Sin historial aún — opera primero para generar estadísticas"}), 200

    from collections import defaultdict

    # Acumuladores
    por_estrategia = defaultdict(lambda: {"total": 0, "wins": 0, "pl_usd": 0.0, "pl_pcts": []})
    por_activo     = defaultdict(lambda: {"total": 0, "wins": 0, "pl_usd": 0.0, "pl_pcts": []})
    por_motivo     = defaultdict(lambda: {"total": 0, "pl_usd": 0.0})
    por_vela       = defaultdict(lambda: {"total": 0, "wins": 0, "pl_usd": 0.0})
    rachas         = []
    racha_actual   = 0
    mejor_racha    = 0

    pl_total       = 0.0
    wins_total     = 0
    total          = len(historial)

    for pos in historial:
        pl_pct  = pos.get("pl_pct", 0) or 0
        pl_usd  = pos.get("pl_usd", 0) or 0
        es_win  = pl_usd > 0
        strat   = pos.get("estrategia", "?")
        activo  = pos.get("simbolo", "?")
        motivo  = pos.get("motivo_cierre", "?")
        pl_total += pl_usd

        if es_win:
            wins_total  += 1
            racha_actual += 1
            mejor_racha  = max(mejor_racha, racha_actual)
        else:
            racha_actual = 0

        # Por estrategia
        por_estrategia[strat]["total"]   += 1
        por_estrategia[strat]["pl_usd"]  += pl_usd
        por_estrategia[strat]["pl_pcts"].append(pl_pct)
        if es_win:
            por_estrategia[strat]["wins"] += 1

        # Por activo
        por_activo[activo]["total"]   += 1
        por_activo[activo]["pl_usd"]  += pl_usd
        por_activo[activo]["pl_pcts"].append(pl_pct)
        if es_win:
            por_activo[activo]["wins"] += 1

        # Por motivo de cierre
        por_motivo[motivo]["total"]  += 1
        por_motivo[motivo]["pl_usd"] += pl_usd

        # Por vela de entrada (extraer de ts_entrada)
        try:
            ts_in = datetime.fromisoformat(str(pos["ts_entrada"]).replace("Z", ""))
            hora  = ts_in.hour
            if hora == 10:   vela = "V1(10h)"
            elif hora == 11: vela = "V2(11h)"
            elif hora == 12: vela = "V3(12h)"
            elif hora == 13: vela = "V4(13h)"
            elif hora == 14: vela = "V5(14h)"
            elif hora == 15: vela = "V6(15h)"
            elif hora == 16: vela = "V7(16h)"
            else:            vela = f"V?({hora}h)"
            por_vela[vela]["total"]  += 1
            por_vela[vela]["pl_usd"] += pl_usd
            if es_win:
                por_vela[vela]["wins"] += 1
        except:
            pass

    def resumen(d):
        return {
            "total":      d["total"],
            "wins":       d["wins"],
            "losses":     d["total"] - d["wins"],
            "win_rate":   f"{round(d['wins']/d['total']*100, 1)}%" if d["total"] else "—",
            "pl_usd":     round(d["pl_usd"], 2),
            "pl_pct_avg": f"{round(sum(d['pl_pcts'])/len(d['pl_pcts']), 1)}%" if d.get("pl_pcts") else "—",
        }

    return jsonify({
        "resumen_general": {
            "total_operaciones": total,
            "wins":              wins_total,
            "losses":            total - wins_total,
            "win_rate":          f"{round(wins_total/total*100, 1)}%" if total else "—",
            "pl_total_usd":      round(pl_total, 2),
            "mejor_racha":       mejor_racha,
            "racha_actual":      racha_actual,
        },
        "por_estrategia": {k: resumen(v) for k, v in sorted(por_estrategia.items())},
        "por_activo":     {k: resumen(v) for k, v in sorted(por_activo.items())},
        "por_vela":       {
            k: {
                "total":    v["total"],
                "wins":     v["wins"],
                "win_rate": f"{round(v['wins']/v['total']*100,1)}%" if v["total"] else "—",
                "pl_usd":   round(v["pl_usd"], 2),
            }
            for k, v in sorted(por_vela.items())
        },
        "por_motivo_cierre": {
            k: {"total": v["total"], "pl_usd": round(v["pl_usd"], 2)}
            for k, v in sorted(por_motivo.items())
        },
        "ultimas_10": [
            {
                "simbolo":   p.get("simbolo"),
                "estrategia":p.get("estrategia"),
                "tipo":      p.get("tipo"),
                "pl_pct":    p.get("pl_pct"),
                "pl_usd":    p.get("pl_usd"),
                "motivo":    p.get("motivo_cierre"),
                "ts_cierre": p.get("ts_cierre"),
            }
            for p in historial[-10:]
        ],
    }), 200

@app.route("/cotizar_opciones", methods=["GET"])
def cotizar_opciones():
    from datetime import date, timedelta
    hoy = date.today()

    def get_pct_otm(precio):
        if precio < 150:  return 1.50
        if precio < 300:  return 1.25
        if precio < 500:  return 0.85
        if precio < 700:  return 0.65
        return 0.50

    resultado = {}
    for simbolo in ACTIVOS:
        try:
            # Precio actual del subyacente
            r0 = requests.get(
                f"{TRADIER_BASE_REAL}/markets/quotes",
                headers=TRADIER_HEADERS_REAL,
                params={"symbols": simbolo, "greeks": "false"},
                timeout=10
            )
            precio_actual = float(r0.json().get("quotes", {}).get("quote", {}).get("last", 0))
            if not precio_actual:
                resultado[simbolo] = {"error": "Sin precio"}
                continue

            # Primer vencimiento con mínimo 7 días
            r1 = requests.get(
                f"{TRADIER_BASE_REAL}/markets/options/expirations",
                headers=TRADIER_HEADERS_REAL,
                params={"symbol": simbolo, "includeAllRoots": "true"},
                timeout=10
            )
            fechas = r1.json().get("expirations", {}).get("date", [])
            if isinstance(fechas, str): fechas = [fechas]
            vencimiento = None
            for f in sorted(fechas):
                if (date.fromisoformat(f) - hoy).days >= 7:
                    vencimiento = f
                    break
            if not vencimiento:
                resultado[simbolo] = {"error": "Sin vencimiento"}
                continue

            # Calcular strikes objetivo
            pct = get_pct_otm(precio_actual)
            dist = round(precio_actual * pct / 100, 1)
            strike_call = round(precio_actual + dist)
            strike_put  = round(precio_actual - dist)

            # Cadena de opciones
            r2 = requests.get(
                f"{TRADIER_BASE_REAL}/markets/options/chains",
                headers=TRADIER_HEADERS_REAL,
                params={"symbol": simbolo, "expiration": vencimiento, "greeks": "false"},
                timeout=10
            )
            opciones = r2.json().get("options", {}).get("option", [])
            if not opciones:
                resultado[simbolo] = {"error": "Sin cadena de opciones"}
                continue

            calls = [o for o in opciones if o.get("option_type") == "call"]
            puts  = [o for o in opciones if o.get("option_type") == "put"]

            mejor_call = min(calls, key=lambda o: abs(float(o.get("strike",0)) - strike_call)) if calls else None
            mejor_put  = min(puts,  key=lambda o: abs(float(o.get("strike",0)) - strike_put))  if puts  else None

            resultado[simbolo] = {
                "precio_actual":  round(precio_actual, 2),
                "vencimiento":    vencimiento,
                "dias_venc":      (date.fromisoformat(vencimiento) - hoy).days,
                "pct_otm":        f"{pct}%",
                "distancia_pts":  dist,
                "CALL": {
                    "strike":       float(mejor_call.get("strike", 0)) if mejor_call else None,
                    "ask":          float(mejor_call.get("ask", 0))    if mejor_call else None,
                    "bid":          float(mejor_call.get("bid", 0))    if mejor_call else None,
                    "costo_1cont":  round(float(mejor_call.get("ask", 0)) * 100, 2) if mejor_call else None,
                    "symbol":       mejor_call.get("symbol")           if mejor_call else None,
                } if mejor_call else None,
                "PUT": {
                    "strike":       float(mejor_put.get("strike", 0))  if mejor_put else None,
                    "ask":          float(mejor_put.get("ask", 0))     if mejor_put else None,
                    "bid":          float(mejor_put.get("bid", 0))     if mejor_put else None,
                    "costo_1cont":  round(float(mejor_put.get("ask", 0)) * 100, 2) if mejor_put else None,
                    "symbol":       mejor_put.get("symbol")            if mejor_put else None,
                } if mejor_put else None,
            }
        except Exception as e:
            resultado[simbolo] = {"error": str(e)}

    return jsonify(resultado), 200
# Prueba diferentes rangos de fechas en Tradier timesales
# para encontrar el limite exacto de datos disponibles
# ═══════════════════════════════════════════════════════════
@app.route("/test_rango", methods=["GET"])
def test_rango():
    from datetime import date

    SIMBOLO  = "SPY"
    fecha_fin = date.today()
    resultado = {}

    def restar_habiles(fecha, dias):
        actual = fecha
        contados = 0
        while contados < dias:
            actual -= timedelta(days=1)
            if actual.weekday() < 5:
                contados += 1
        return actual

    # Probar rangos: 20, 30, 40, 45, 50, 60 dias habiles
    for dias in [20, 30, 40, 45, 50, 60]:
        fecha_ini = restar_habiles(fecha_fin, dias)
        try:
            r = requests.get(
                f"{TRADIER_BASE_REAL}/markets/timesales",
                headers=TRADIER_HEADERS_REAL,
                params={
                    "symbol":         SIMBOLO,
                    "interval":       "15min",
                    "start":          f"{fecha_ini.strftime('%Y-%m-%d')} 09:00",
                    "end":            f"{fecha_fin.strftime('%Y-%m-%d')} 16:30",
                    "session_filter": "open",
                },
                timeout=30
            )
            data   = r.json()
            series = data.get("series")
            if series and series != "null":
                barras = series.get("data", [])
                if isinstance(barras, dict): barras = [barras]
                resultado[f"{dias}_dias_habiles"] = {
                    "estado":    "✅ OK",
                    "barras":    len(barras),
                    "desde":     fecha_ini.strftime("%Y-%m-%d"),
                    "primera":   barras[-1]["time"] if barras else None,
                }
            else:
                resultado[f"{dias}_dias_habiles"] = {
                    "estado": "❌ series null",
                    "desde":  fecha_ini.strftime("%Y-%m-%d"),
                }
        except Exception as e:
            resultado[f"{dias}_dias_habiles"] = {"estado": f"❌ error: {str(e)}"}

    return jsonify(resultado), 200

# ═══════════════════════════════════════════════════════════
# DIAGNOSTICO — Auditoria de estrategias por activo y fecha
# Uso: /diagnostico?simbolo=AAPL&fecha=2026-03-27
# Muestra OHLC real + razon exacta de cada señal por vela
# Permanente — para verificacion de datos y logica
# ═══════════════════════════════════════════════════════════
@app.route("/diagnostico", methods=["GET"])
def diagnostico():
    from datetime import date as date_cls, datetime as dt2, timedelta
    from collections import defaultdict

    simbolo = request.args.get("simbolo", "SPY").upper()
    fecha   = request.args.get("fecha", date_cls.today().strftime("%Y-%m-%d"))

    reporte = { "simbolo": simbolo, "fecha": fecha, "velas": [], "señales": [], "log": [] }
    log = reporte["log"]

    # ── Obtener velas del dia y dia anterior via Tradier ──
    try:
        fecha_dt   = dt2.strptime(fecha, "%Y-%m-%d")
        fecha_ini  = (fecha_dt - timedelta(days=10)).strftime("%Y-%m-%d")
        fecha_fin  = fecha_dt.strftime("%Y-%m-%d")

        r = requests.get(
            f"{TRADIER_BASE_REAL}/markets/timesales",
            headers=TRADIER_HEADERS_REAL,
            params={
                "symbol":         simbolo,
                "interval":       "15min",
                "start":          f"{fecha_ini} 09:00",
                "end":            f"{fecha_fin} 16:30",
                "session_filter": "open",
            },
            timeout=30
        )
        data   = r.json()
        series = data.get("series")
        barras = []
        if series and series != "null":
            barras = series.get("data", [])
            if isinstance(barras, dict): barras = [barras]
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # ── Agrupar en velas AXIS ──
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
        return {
            "vela":  vnum,
            "open":  round(float(bs[0]["open"]), 2),
            "high":  round(max(float(b["high"]) for b in bs), 2),
            "low":   round(min(float(b["low"])  for b in bs), 2),
            "close": round(float(bs[-1]["close"]), 2),
            "bars":  len(bs),
        }

    # ── Velas del dia anterior (para V7 close y SMAs simples) ──
    fechas_ordenadas = sorted(dias.keys())
    v7_prev_close = None
    for f in fechas_ordenadas:
        if f < fecha:
            bs = dias[f].get("V7", [])
            if bs: v7_prev_close = round(float(bs[-1]["close"]), 2)

    # ── Construir velas del dia solicitado ──
    velas_dia = {}
    for vnum in ["V1","V2","V3","V4","V5","V6","V7"]:
        v = construir_vela(vnum, dias.get(fecha, {}).get(vnum, []))
        if v: velas_dia[vnum] = v

    reporte["velas"] = list(velas_dia.values())
    reporte["v7_dia_anterior"] = v7_prev_close

    if not velas_dia:
        log.append("⚠️ Sin velas para esta fecha — puede ser feriado o fin de semana")
        return jsonify(reporte), 200

    # ── Helpers ──
    def es_verde(v): return v["close"] > v["open"]
    def es_roja(v):  return v["close"] < v["open"]
    def es_alcista(v):
        o,h,l,c = v["open"],v["high"],v["low"],v["close"]
        cuerpo   = c - o
        rango    = h - l
        mechaSup = h - c
        if c <= o: return False, "close <= open"
        if rango == 0: return False, "rango=0"
        r1 = round(cuerpo/rango, 3)
        if r1 < 0.15: return False, f"body/range={r1} < 0.15"
        r2 = round(mechaSup/cuerpo, 3) if cuerpo > 0 else 999
        if r2 > 0.75: return False, f"mechaSup/body={r2} > 0.75"
        return True, f"body/range={r1} mechaSup/body={r2}"

    v1 = velas_dia.get("V1")

    # ── ANALISIS 1VR ──
    log.append("─── 1VR ───────────────────────────────")
    if v1:
        if es_roja(v1):
            log.append(f"✅ 1VR DISPARADA — V1 roja: O{v1['open']} C{v1['close']}")
            reporte["señales"].append("1VR en V1")
        else:
            log.append(f"❌ 1VR no — V1 verde: O{v1['open']} C{v1['close']}")

    # ── ANALISIS RPG ──
    log.append("─── RPG ───────────────────────────────")
    if v1 and v7_prev_close:
        gap_up   = round((v1["open"] - v7_prev_close) / v7_prev_close * 100, 3)
        gap_down = round((v7_prev_close - v1["open"]) / v7_prev_close * 100, 3)
        hay_gap  = abs(gap_up) >= 0.2 or abs(gap_down) >= 0.2
        log.append(f"V7 anterior close: {v7_prev_close}")
        log.append(f"V1 open: {v1['open']} | gap_up={gap_up}% gap_down={gap_down}%")
        log.append(f"Gap >= 0.2%: {'SI' if hay_gap else 'NO'}")
        log.append(f"V1 verde: {'SI' if es_verde(v1) else 'NO'}")

        if hay_gap and es_verde(v1):
            piso = v1["low"]
            log.append(f"✅ RPG activado — piso = V1.low = {piso}")
            rpg_fired = False
            for vnum in ["V2","V3","V4","V5","V6","V7"]:
                v = velas_dia.get(vnum)
                if not v or rpg_fired: continue
                roja = es_roja(v)
                bajo_piso = v["close"] < piso
                log.append(f"  {vnum}: O{v['open']} H{v['high']} L{v['low']} C{v['close']} | roja={roja} close({v['close']})<piso({piso})={bajo_piso}")
                if roja and bajo_piso:
                    log.append(f"  ✅ RPG DISPARADA en {vnum}")
                    reporte["señales"].append(f"RPG en {vnum}")
                    rpg_fired = True
                elif bajo_piso and not roja:
                    log.append(f"  ⚠️ {vnum} cerro bajo piso pero es VERDE — RPG requiere roja")
                elif roja and not bajo_piso:
                    log.append(f"  ⚠️ {vnum} es roja pero NO cerro bajo piso")
        else:
            log.append("❌ RPG no activado — condiciones V1 no cumplidas")
    else:
        log.append(f"❌ RPG no — {'sin V1' if not v1 else 'sin V7 anterior'}")

    # ── ANALISIS GNA ──
    log.append("─── GNA ───────────────────────────────")
    if v1 and v7_prev_close:
        gap_up = round((v1["open"] - v7_prev_close) / v7_prev_close * 100, 3)
        log.append(f"gap_up={gap_up}% (min 0.1%): {'SI' if gap_up >= 0.1 else 'NO'}")
        log.append(f"V1 verde: {'SI' if es_verde(v1) else 'NO'}")
        log.append("SMA20>SMA40: requiere historial largo — verificar en dashboard")

        if gap_up >= 0.1 and es_verde(v1):
            techo = v1["close"]
            log.append(f"GNA activado — techo = V1.close = {techo}")
            gna_fired = False
            for vnum in ["V2","V3","V4","V5","V6","V7"]:
                v = velas_dia.get(vnum)
                if not v or gna_fired: continue
                ok_alc, razon_alc = es_alcista(v)
                rompe = v["close"] > techo
                log.append(f"  {vnum}: O{v['open']} H{v['high']} L{v['low']} C{v['close']} | alcista={ok_alc}({razon_alc}) rompe={rompe}(c{v['close']}>t{techo})")
                if ok_alc and rompe:
                    tipo = "GNA" if vnum == "V2" else "GNA+2"
                    log.append(f"  ✅ {tipo} DISPARADA en {vnum}")
                    reporte["señales"].append(f"{tipo} en {vnum}")
                    gna_fired = True
        else:
            log.append("❌ GNA no activado")

    # ── ANALISIS GBA ──
    log.append("─── GBA ───────────────────────────────")
    if v1 and v7_prev_close:
        gap_down = round((v7_prev_close - v1["open"]) / v7_prev_close * 100, 3)
        log.append(f"gap_down={gap_down}% (min 0.1%): {'SI' if gap_down >= 0.1 else 'NO'}")
        log.append(f"V1 verde: {'SI' if es_verde(v1) else 'NO'}")

        if gap_down >= 0.1 and es_verde(v1):
            techo = v1["close"]
            log.append(f"GBA activado — techo = V1.close = {techo}")
            gba_fired = False
            for vnum in ["V2","V3","V4","V5","V6","V7"]:
                v = velas_dia.get(vnum)
                if not v or gba_fired: continue
                ok_alc, razon_alc = es_alcista(v)
                rompe = v["close"] > techo
                log.append(f"  {vnum}: alcista={ok_alc}({razon_alc}) rompe={rompe}")
                if ok_alc and rompe:
                    tipo = "GBA" if vnum == "V2" else "GBA+2"
                    log.append(f"  ✅ {tipo} DISPARADA en {vnum}")
                    reporte["señales"].append(f"{tipo} en {vnum}")
                    gba_fired = True
        else:
            log.append("❌ GBA no activado")

    return jsonify(reporte), 200

# ═══════════════════════════════════════════════════════════
# PRECIO EN TIEMPO REAL
# GET /precio?simbolo=SPY
# ═══════════════════════════════════════════════════════════
@app.route("/precio", methods=["GET"])
def precio_rt():
    simbolo = request.args.get("simbolo", "SPY").upper()
    precio  = get_precio_tradier(simbolo)
    if precio:
        return jsonify({"simbolo": simbolo, "precio": precio}), 200
    return jsonify({"error": "No disponible"}), 500

# ═══════════════════════════════════════════════════════════
# CANAL ESTADO — devuelve P's actuales por activo
# Usado por el dashboard para sincronizar el panel de P's
# GET /canal_estado?activo=SPY (opcional — sin param devuelve todos)
# ═══════════════════════════════════════════════════════════
@app.route("/canal_estado", methods=["GET"])
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
            "on":      c["on"],
            "tipo":    "RCB" if (c["on"] and c["p3"]) else ("CNF" if c["on"] else "---"),
            "p1":      c["p1"],
            "p2":      c["p2"],
            "p3":      c["p3"],
            "techo":   round(techo, 2) if techo else None,
            "mitad":   round(piso_mitad[1], 2) if piso_mitad[1] else None,
            "piso":    round(piso_mitad[0], 2) if piso_mitad[0] else None,
        }

    return jsonify(resultado), 200

# ═══════════════════════════════════════════════════════════
# CANAL LINEAS — calcula techo/mitad/piso por cada vela
# El dashboard dibuja exactamente lo que Railway calcula
# GET /canal_lineas?activo=SPY
# Devuelve lista de { datetime, techo, mitad, piso } por vela AXIS
# ═══════════════════════════════════════════════════════════
@app.route("/canal_lineas", methods=["GET"])
def canal_lineas():
    simbolo = request.args.get("activo", "SPY").upper()
    if simbolo not in ACTIVOS:
        return jsonify({"error": f"Activo no reconocido"}), 400

    c = canal[simbolo]
    if not c["on"] or not c["p1"] or not c["p2"]:
        return jsonify({"activo": simbolo, "on": False, "lineas": []}), 200

    # Obtener velas del activo
    velas = get_velas(simbolo, outputsize=280)
    if not velas:
        return jsonify({"error": "Sin velas"}), 500

    lineas = []
    fecha_p1 = c["p1"]["fecha"]
    hora_p1  = c["p1"]["hora_est"]

    for v in velas:
        try:
            # Solo incluir velas desde P1 en adelante
            v_fecha = v["datetime"][:10]
            v_hora  = int(v["datetime"][11:13])
            if v_fecha < fecha_p1:
                continue
            if v_fecha == fecha_p1 and v_hora < hora_p1:
                continue

            ahora_dt = datetime.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S")
            ahora_dt = EST.localize(ahora_dt)
            techo = calcular_techo_canal(simbolo, ahora_dt)
            piso, mitad = calcular_piso_mitad_canal(simbolo, ahora_dt)
            lineas.append({
                "datetime": v["datetime"],
                "vela":     v["vela"],
                "techo":    round(techo, 4) if techo else None,
                "mitad":    round(mitad, 4) if mitad else None,
                "piso":     round(piso,  4) if piso  else None,
            })
        except Exception as e:
            continue

    tipo = "RCB" if c["p3"] else "CNF"
    return jsonify({
        "activo":  simbolo,
        "on":      True,
        "tipo":    tipo,
        "lineas":  lineas,
    }), 200

# ═══════════════════════════════════════════════════════════
# POLLING GTC Y VENCIMIENTO
# Cada 5 min revisa posiciones abiertas:
# - Si la orden GTC se ejecutó en Tradier → cierra posición como "gtc"
# - Si la opción venció → cierra posición como "vencimiento"
# ═══════════════════════════════════════════════════════════
def get_estado_orden_tradier(orden_id):
    """Consulta estado de una orden en Tradier sandbox."""
    try:
        r = requests.get(
            f"{TRADIER_BASE}/accounts/{TRADIER_ACCOUNT}/orders/{orden_id}",
            headers=TRADIER_HEADERS,
            timeout=10
        )
        if r.status_code != 200:
            return None
        data = r.json()
        orden = data.get("order", {})
        return {
            "status":       orden.get("status"),
            "avg_fill_price": float(orden.get("avg_fill_price", 0) or 0),
        }
    except Exception as e:
        print(f"Error estado orden {orden_id}: {e}")
        return None

def loop_polling_posiciones():
    """
    Thread que cada 5 min revisa posiciones abiertas.
    Detecta GTC ejecutado y vencimientos.
    Solo activo en horario de mercado.
    """
    print("Thread polling posiciones iniciado...")
    while True:
        try:
            time.sleep(300)  # cada 5 minutos
            ahora = datetime.now(EST)
            if not es_dia_mercado(ahora):
                continue
            mins = ahora.hour * 60 + ahora.minute
            if not (570 <= mins <= 1020):  # 9:30 — 5:00 PM
                continue
            if _portfolio is None:
                continue

            from datetime import date as date_cls
            hoy = date_cls.today()
            posiciones = list(_portfolio["posiciones"])

            for pos in posiciones:
                pos_id = pos["id"]

                # 1 — Vencimiento: si expiration <= hoy → cerrar como vencimiento
                try:
                    exp = date_cls.fromisoformat(pos["expiration"])
                    if exp < hoy:
                        print(f"Posición {pos_id} vencida — {pos['option_symbol']}")
                        cerrar_posicion(pos_id, 0.0, "vencimiento")
                        continue
                except Exception as e:
                    print(f"Error check vencimiento {pos_id}: {e}")

                # 2 — GTC: si hay orden GTC y su estado es "filled" → cerrar
                gtc_id = pos.get("tradier_gtc_id")
                if not gtc_id:
                    continue
                try:
                    estado = get_estado_orden_tradier(gtc_id)
                    if not estado:
                        continue
                    if estado["status"] == "filled" and estado["avg_fill_price"] > 0:
                        precio_gtc = estado["avg_fill_price"]
                        print(f"GTC ejecutado {pos_id} — ${precio_gtc:.2f}")
                        cerrar_posicion(pos_id, precio_gtc, "gtc")
                except Exception as e:
                    print(f"Error check GTC {pos_id}: {e}")

        except Exception as e:
            print(f"Error loop_polling_posiciones: {e}")


def arrancar_monitor():
    time.sleep(5)
    cargar_canales()
    cargar_portfolio()
    cargar_ordenes()
    threading.Thread(target=monitor_loop,              daemon=True).start()
    threading.Thread(target=loop_v7_anticipada,        daemon=True).start()
    threading.Thread(target=loop_limpiar_ordenes,      daemon=True).start()
    threading.Thread(target=loop_polling_posiciones,   daemon=True).start()

threading.Thread(target=arrancar_monitor, daemon=True).start()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
