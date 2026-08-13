#!/usr/bin/env python3
"""
AXIS Tradier Access — AX-004 Tradier Access Baseline
Funciones puras de acceso a Tradier (sandbox), extraidas de server.py sin
cambiar ningun comportamiento, payload, URL, header, ni nombre publico.

Estas funciones no dependen de Telegram, Portfolio, Derby, ni estado_dia/canal
de server.py -- solo de configuracion (axis_config) y del token via os.environ,
igual que antes.
"""

import os
import requests
from datetime import date, timedelta

from axis_config import TRADIER_BASE

# ── TRADIER SANDBOX (ordenes paper trading) ──
TRADIER_TOKEN   = os.environ.get("TRADIER_TOKEN", "")
TRADIER_ACCOUNT = os.environ.get("TRADIER_ACCOUNT", "")
TRADIER_HEADERS = {
    "Authorization": f"Bearer {TRADIER_TOKEN}",
    "Accept":        "application/json",
}


def get_pct_otm(precio):
    if precio < 150:  return 1.50
    if precio < 300:  return 1.25
    if precio < 500:  return 0.85
    if precio < 700:  return 0.65
    return 0.50


def cancelar_orden_tradier(orden_id):
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


def tiene_posicion_opcion_tradier(option_symbol):
    """Consulta de solo lectura para revisar una compra con respuesta ambigua."""
    try:
        r = requests.get(
            f"{TRADIER_BASE}/accounts/{TRADIER_ACCOUNT}/positions",
            headers=TRADIER_HEADERS,
            timeout=10,
        )
        if r.status_code != 200:
            return None
        posiciones = r.json().get("positions", {}).get("position", [])
        if isinstance(posiciones, dict):
            posiciones = [posiciones]
        return any(p.get("symbol") == option_symbol for p in posiciones)
    except Exception as e:
        print(f"Error revisando posición Tradier {option_symbol}: {e}")
        return None


def _detalle_error_tradier(response, etapa):
    """Mensaje seguro y accionable cuando Tradier no confirma una orden."""
    try:
        cuerpo = response.json()
        detalle = cuerpo.get("error") or cuerpo.get("errors") or cuerpo.get("fault")
    except Exception:
        detalle = None
    sufijo = f": {detalle}" if detalle else ""
    return f"{etapa}: HTTP {response.status_code}{sufijo}"


def _orden_confirmada(response, etapa):
    """Devuelve (id, status, error); exige HTTP 2xx e ID de orden de Tradier."""
    if not (200 <= response.status_code < 300):
        return None, None, _detalle_error_tradier(response, etapa)
    try:
        orden = response.json().get("order") or {}
    except Exception as e:
        return None, None, f"{etapa}: respuesta JSON inválida ({e})"
    orden_id = orden.get("id")
    status = str(orden.get("status") or "unknown")
    if not orden_id:
        return None, status, f"{etapa}: Tradier no devolvió ID de orden"
    if status.lower() in {"rejected", "cancelled", "canceled", "expired", "error", "failed"}:
        return None, status, f"{etapa}: Tradier reportó estado {status}"
    return orden_id, status, None


def vender_opcion_tradier(option_symbol, simbolo, contratos, precio_limit):
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
        orden_id, status, error = _orden_confirmada(r, "venta")
        if error:
            return {"ok": False, "error": error}
        return {"ok": True, "id": orden_id, "status": status}
    except Exception as e:
        print(f"Error vender opcion Tradier: {e}")
        return {"ok": False, "error": str(e)}


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


def get_opcion_tradier(simbolo, tipo, precio_actual):
    try:
        hoy = date.today()

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

        vencimiento = None
        for f in sorted(fechas):
            fd = date.fromisoformat(f)
            if (fd - hoy).days >= 7:
                vencimiento = f
                break

        if not vencimiento:
            print(f"Sin vencimiento ≥7 días para {simbolo}")
            return None

        pct  = get_pct_otm(precio_actual)
        dist = precio_actual * pct / 100
        if tipo == 'call':
            strike_obj = round(precio_actual + dist)
        else:
            strike_obj = round(precio_actual - dist)

        print(f"  {simbolo} {tipo.upper()} — precio ${precio_actual:.2f} | {pct}% OTM | strike obj ${strike_obj} | venc {vencimiento}")

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


def _ejecutar_orden_tradier(opcion, contratos):
    """Envía compra y GTC, sin confundir una respuesta incompleta con éxito.

    ``ok`` representa una compra aceptada por Tradier (HTTP 2xx + order ID).
    El GTC se informa por separado: una falla de salida no borra evidencia de
    una compra real ni permite crear una posición fantasma cuando falló la compra.
    """
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
        orden_id, status, error = _orden_confirmada(r, "compra")
        if error:
            return {"ok": False, "error": error, "ambiguous": r.status_code >= 500}

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
        resultado = {
            "ok":            True,
            "id":            orden_id,
            "status":        status,
            "precio_venta":  precio_venta,
            "venta_ok":      False,
        }
        try:
            r2 = requests.post(
                f"{TRADIER_BASE}/accounts/{TRADIER_ACCOUNT}/orders",
                headers=TRADIER_HEADERS,
                data=payload_venta,
                timeout=10
            )
            orden_venta_id, venta_status, venta_error = _orden_confirmada(r2, "GTC de salida")
            if venta_error:
                resultado["venta_error"] = venta_error
            else:
                resultado["venta_id"] = orden_venta_id
                resultado["venta_status"] = venta_status
                resultado["venta_ok"] = True
        except Exception as e:
            resultado["venta_error"] = f"GTC de salida: {e}"
        return resultado
    except Exception as e:
        print(f"Error ejecutar orden Tradier: {e}")
        return {"ok": False, "error": str(e), "ambiguous": True}


def ejecutar_orden_tradier(opcion):
    return _ejecutar_orden_tradier(opcion, 1)


def ejecutar_orden_tradier_contratos(opcion, contratos):
    return _ejecutar_orden_tradier(opcion, contratos)
