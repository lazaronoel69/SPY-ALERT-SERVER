#!/usr/bin/env python3
"""
SPY Alert System v6.0
- Fuente de datos: Twelve Data (principal) + Finnhub (backup)
- Reportes a las :01 de cada hora: 10,11,12,13,14,15,16 EST
- Solo Lunes a Viernes (mercado abierto)
- Vela 7 (4:00 PM) es de 30 minutos — se confirma igual a las 4:01 PM
- Verificacion P1/P2 al inicio
"""

import requests
import threading
import time
from datetime import datetime, timedelta
import pytz
from flask import Flask, jsonify

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════
# CONFIGURACION
# ═══════════════════════════════════════════════════════════
TELEGRAM_TOKEN    = "8668514895:AAG5HKGmDLr6_SM1rz3gwC6uk1Ue9iepN70"
TELEGRAM_CHAT_ID  = "-5010153427"
TWELVEDATA_KEY    = "66dd71373a884f7bb7da8e6e5e469571"
FINNHUB_KEY       = "d71aocpr01qot5jcnohgd71aocpr01qot5jcnoi0"
EST               = pytz.timezone("America/New_York")

# Horas de confirmacion (hora final de cada vela)
# Vela 1=10, Vela 2=11, ..., Vela 7=16
HORAS_REPORTE = [10, 11, 12, 13, 14, 15, 16]

# P1 y P2 — con ADJ desactivado en TradingView
# Formato: fecha YYYY-MM-DD, vela = numero 1-7, high = precio sin ADJ
P1 = { "fecha": "2026-02-26", "vela": 1, "hora_est": 10, "high": 693.29 }
P2 = { "fecha": "2026-03-10", "vela": 5, "hora_est": 14, "high": 683.36 }

# Mapa vela -> hora de cierre en TradingView (para consulta de datos)
# La vela cierra 30 min despues de nuestra hora de confirmacion
# Ejemplo: confirmamos a las 10:00, la vela en TV cerro a las 10:30
VELA_A_HORA_TV = {
    1: 10,   # vela cierra 10:30 TV — nosotros consultamos datos de hora 10
    2: 11,
    3: 12,
    4: 13,
    5: 14,
    6: 15,
    7: 16,   # vela de 30 min — cierra 4:00 PM, confirmamos 4:01 PM
}

# ═══════════════════════════════════════════════════════════
# HELPERS — DIA DE MERCADO
# ═══════════════════════════════════════════════════════════
def es_dia_mercado(dt=None):
    """Retorna True si es Lunes a Viernes"""
    if dt is None:
        dt = datetime.now(EST)
    return dt.weekday() < 5  # 0=Lunes ... 4=Viernes, 5=Sabado, 6=Domingo

def es_hora_reporte(hora):
    """Retorna True si la hora esta en nuestro schedule"""
    return hora in HORAS_REPORTE

# ═══════════════════════════════════════════════════════════
# TELEGRAM
# ═══════════════════════════════════════════════════════════
def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = { "chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML" }
    try:
        r = requests.post(url, json=payload, timeout=10)
        print(f"Telegram: {r.status_code}")
    except Exception as e:
        print(f"Error Telegram: {e}")

# ═══════════════════════════════════════════════════════════
# TWELVE DATA — fuente principal
# ═══════════════════════════════════════════════════════════
def get_vela_twelvedata(fecha_str=None):
    """
    Obtiene la ultima vela cerrada de 1H de SPY via Twelve Data.
    Si se pasa fecha_str (YYYY-MM-DD), obtiene velas de ese dia.
    """
    try:
        # Twelve Data: endpoint para series de tiempo
        params = {
            "symbol": "SPY",
            "interval": "1h",
            "outputsize": 10,
            "timezone": "America/New_York",
            "apikey": TWELVEDATA_KEY,
        }
        if fecha_str:
            params["start_date"] = f"{fecha_str} 09:00:00"
            params["end_date"]   = f"{fecha_str} 23:59:59"

        url = "https://api.twelvedata.com/time_series"
        r = requests.get(url, params=params, timeout=15)
        data = r.json()

        if data.get("status") == "error" or "values" not in data:
            print(f"TwelveData error: {data.get('message', data)}")
            return None

        valores = data["values"]
        # valores[0] es la mas reciente (puede estar abierta)
        # valores[1] es la ultima cerrada
        if len(valores) < 2:
            return None

        # Si pedimos fecha especifica retornamos todas las velas del dia
        if fecha_str:
            velas = []
            for v in valores:
                dt = datetime.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S")
                velas.append({
                    "hora": dt.hour,
                    "open":  float(v["open"]),
                    "high":  float(v["high"]),
                    "low":   float(v["low"]),
                    "close": float(v["close"]),
                    "time":  v["datetime"],
                })
            return velas

        # Retornar ultima vela cerrada
        v = valores[1]
        dt = datetime.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S")
        return {
            "open":  float(v["open"]),
            "high":  float(v["high"]),
            "low":   float(v["low"]),
            "close": float(v["close"]),
            "time":  dt.strftime("%H:%M EST")
        }

    except Exception as e:
        print(f"Error TwelveData: {e}")
        return None

# ═══════════════════════════════════════════════════════════
# FINNHUB — fuente backup
# ═══════════════════════════════════════════════════════════
def get_vela_finnhub(fecha_str=None):
    """
    Obtiene velas de 1H de SPY via Finnhub como backup.
    """
    try:
        ahora_est = datetime.now(EST)

        if fecha_str:
            dt_inicio = EST.localize(datetime.strptime(f"{fecha_str} 09:30:00", "%Y-%m-%d %H:%M:%S"))
            dt_fin    = EST.localize(datetime.strptime(f"{fecha_str} 23:59:59", "%Y-%m-%d %H:%M:%S"))
        else:
            dt_fin    = ahora_est
            dt_inicio = ahora_est - timedelta(hours=12)

        ts_inicio = int(dt_inicio.timestamp())
        ts_fin    = int(dt_fin.timestamp())

        url = f"https://finnhub.io/api/v1/stock/candle"
        params = {
            "symbol":     "SPY",
            "resolution": "60",
            "from":       ts_inicio,
            "to":         ts_fin,
            "token":      FINNHUB_KEY,
        }
        r = requests.get(url, params=params, timeout=15)
        data = r.json()

        if data.get("s") != "ok" or not data.get("c"):
            print(f"Finnhub error: {data}")
            return None

        # Construir lista de velas
        velas = []
        for i in range(len(data["c"])):
            dt = datetime.fromtimestamp(data["t"][i], tz=EST)
            velas.append({
                "hora":  dt.hour,
                "open":  data["o"][i],
                "high":  data["h"][i],
                "low":   data["l"][i],
                "close": data["c"][i],
                "time":  dt.strftime("%H:%M EST"),
            })

        if fecha_str:
            return velas

        # Retornar ultima vela cerrada (penultima en lista)
        if len(velas) < 2:
            return None
        v = velas[-2]
        return {
            "open":  v["open"],
            "high":  v["high"],
            "low":   v["low"],
            "close": v["close"],
            "time":  v["time"],
        }

    except Exception as e:
        print(f"Error Finnhub: {e}")
        return None

# ═══════════════════════════════════════════════════════════
# OBTENER VELA — intenta TwelveData, luego Finnhub
# ═══════════════════════════════════════════════════════════
def get_ultima_vela():
    """Retorna la ultima vela cerrada. TwelveData primero, Finnhub como backup."""
    vela = get_vela_twelvedata()
    if vela:
        print("Datos obtenidos: TwelveData ✅")
        return vela, "TwelveData"

    print("TwelveData fallo — intentando Finnhub...")
    vela = get_vela_finnhub()
    if vela:
        print("Datos obtenidos: Finnhub ✅")
        return vela, "Finnhub"

    print("Ambas fuentes fallaron ❌")
    return None, None

def get_high_vela_por_hora(fecha_str, hora_est):
    """Obtiene el high de una vela especifica por fecha y hora EST."""
    # Intentar TwelveData
    velas = get_vela_twelvedata(fecha_str=fecha_str)
    if velas:
        for v in velas:
            if v["hora"] == hora_est:
                return v["high"], "TwelveData"

    # Backup Finnhub
    velas = get_vela_finnhub(fecha_str=fecha_str)
    if velas:
        for v in velas:
            if v["hora"] == hora_est:
                return v["high"], "Finnhub"

    return None, None

# ═══════════════════════════════════════════════════════════
# CALCULAR TECHO DIAGONAL
# ═══════════════════════════════════════════════════════════
def calcular_techo_ahora():
    """Calcula el valor del techo del canal bajista en el momento actual."""
    fmt = "%Y-%m-%d %H:%M"
    p1_dt = EST.localize(datetime.strptime(f"{P1['fecha']} {P1['hora_est']}:00", fmt))
    p2_dt = EST.localize(datetime.strptime(f"{P2['fecha']} {P2['hora_est']}:00", fmt))
    ahora = datetime.now(EST)
    pendiente = (P2["high"] - P1["high"]) / (p2_dt.timestamp() - p1_dt.timestamp())
    techo = P1["high"] + pendiente * (ahora.timestamp() - p1_dt.timestamp())
    return round(techo, 2)

# ═══════════════════════════════════════════════════════════
# VERIFICACION P1 Y P2
# ═══════════════════════════════════════════════════════════
def verificar_puntos():
    mensaje = "🔍 <b>Verificacion P1 y P2</b>\n"
    mensaje += "<i>(Sin ADJ — fuente externa vs operador)</i>\n\n"

    # Verificar P1
    high_p1, fuente_p1 = get_high_vela_por_hora(P1["fecha"], P1["hora_est"])
    if high_p1:
        diff = abs(high_p1 - P1["high"])
        estado = "⚠️ <b>P1 REVISAR</b>" if diff > 0.50 else "✅ <b>P1 OK</b>"
        mensaje += f"{estado}\n   Operador: ${P1['high']:.2f} | {fuente_p1}: ${high_p1:.2f} | Diff: ${diff:.2f}\n\n"
    else:
        mensaje += f"⚠️ P1 no verificado — usando ${P1['high']:.2f}\n\n"

    # Verificar P2
    high_p2, fuente_p2 = get_high_vela_por_hora(P2["fecha"], P2["hora_est"])
    if high_p2:
        diff = abs(high_p2 - P2["high"])
        estado = "⚠️ <b>P2 REVISAR</b>" if diff > 0.50 else "✅ <b>P2 OK</b>"
        mensaje += f"{estado}\n   Operador: ${P2['high']:.2f} | {fuente_p2}: ${high_p2:.2f} | Diff: ${diff:.2f}\n\n"
    else:
        mensaje += f"⚠️ P2 no verificado — usando ${P2['high']:.2f}\n\n"

    techo = calcular_techo_ahora()
    mensaje += f"📐 Techo canal ahora: <b>${techo:.2f}</b>\n"
    mensaje += f"⚠️ Regla: ADJ siempre desactivado en TradingView"
    enviar_telegram(mensaje)

# ═══════════════════════════════════════════════════════════
# REPORTE HORARIO
# ═══════════════════════════════════════════════════════════
def reporte_horario():
    ahora_est = datetime.now(EST)

    # Filtro 1: Solo Lunes a Viernes
    if not es_dia_mercado(ahora_est):
        print(f"Fin de semana — sin reporte: {ahora_est.strftime('%A %H:%M EST')}")
        return

    hora = ahora_est.hour

    # Filtro 2: Solo en horas de reporte (10-16)
    if not es_hora_reporte(hora):
        print(f"Fuera de horario de reporte: {ahora_est.strftime('%H:%M EST')}")
        return

    # Nombre de vela para el mensaje
    vela_num = hora - 9  # hora 10 = vela 1, hora 16 = vela 7
    hora_label = f"{hora}:00 EST"
    es_ultima_vela = (hora == 16)

    techo = calcular_techo_ahora()
    vela, fuente = get_ultima_vela()

    if not vela:
        enviar_telegram(
            f"⚠️ <b>Reporte {hora_label} — Vela {vela_num}</b>\n"
            f"No se pudo obtener datos de SPY.\n"
            f"Sistema activo — proxima: {hora + 1}:00 EST"
        )
        return

    # Analisis de la vela
    vela_verde  = vela["close"] > vela["open"]
    rango       = vela["high"] - vela["low"]
    mecha_sup   = vela["high"] - max(vela["close"], vela["open"])
    mecha_pct   = (mecha_sup / rango * 100) if rango > 0 else 0
    mecha_ok    = mecha_pct <= 25
    sobre_techo = vela["close"] > techo
    ruptura     = vela_verde and mecha_ok and sobre_techo

    proxima = f"{hora + 1}:00 EST" if hora < 16 else "apertura del lunes" if ahora_est.weekday() == 4 else "apertura manana"
    nota_vela = " <i>(vela 30 min)</i>" if es_ultima_vela else ""

    if ruptura:
        mensaje = (
            f"🟢 <b>RUPTURA DEL CANAL</b>\n"
            f"<b>Hora:</b> {hora_label} — Vela {vela_num}{nota_vela}\n\n"
            f"<b>Techo:</b> ${techo:.2f}\n"
            f"<b>Cierre:</b> ${vela['close']:.2f}\n"
            f"<b>Mecha sup:</b> {mecha_pct:.0f}%\n"
            f"<b>Fuente:</b> {fuente}\n\n"
            f"⚡ <b>EVALUAR ENTRADA</b>"
        )
    else:
        razon = []
        if not vela_verde:  razon.append("vela roja")
        if not mecha_ok:    razon.append(f"mecha {mecha_pct:.0f}%")
        if not sobre_techo: razon.append(f"cierre ${vela['close']:.2f} bajo techo ${techo:.2f}")

        mensaje = (
            f"🔴 <b>Sin ruptura — {hora_label} — Vela {vela_num}</b>{nota_vela}\n\n"
            f"<b>Techo:</b> ${techo:.2f}\n"
            f"<b>Cierre:</b> ${vela['close']:.2f}\n"
            f"<b>Vela:</b> {'Verde' if vela_verde else 'Roja'} | Mecha: {mecha_pct:.0f}%\n"
            f"<b>Razon:</b> {', '.join(razon)}\n"
            f"<b>Fuente:</b> {fuente}\n\n"
            f"Sistema activo — proxima: {proxima}"
        )

    enviar_telegram(mensaje)

# ═══════════════════════════════════════════════════════════
# LOOP — reporta a las :01 de cada hora de reporte
# ═══════════════════════════════════════════════════════════
def monitor_loop():
    print("SPY Alert System v6.0 iniciado...")
    time.sleep(5)
    verificar_puntos()

    while True:
        ahora = datetime.now(EST)
        # Calcular minutos hasta el proximo :01
        minutos_hasta_01 = (1 - ahora.minute) % 60
        if minutos_hasta_01 == 0:
            minutos_hasta_01 = 60
        segundos_espera = minutos_hasta_01 * 60 - ahora.second

        print(f"Proximo chequeo en {minutos_hasta_01} min | {ahora.strftime('%A %H:%M EST')}")
        time.sleep(segundos_espera)

        # Al despertar verificar si toca reporte
        ahora = datetime.now(EST)
        if es_dia_mercado(ahora) and es_hora_reporte(ahora.hour):
            reporte_horario()
        else:
            print(f"No toca reporte: {ahora.strftime('%A %H:%M EST')}")

# ═══════════════════════════════════════════════════════════
# RUTAS FLASK
# ═══════════════════════════════════════════════════════════
@app.route("/", methods=["GET"])
def home():
    ahora = datetime.now(EST)
    return jsonify({
        "status": "SPY Alert System v6.0 activo",
        "hora_est": ahora.strftime("%A %H:%M EST"),
        "mercado": "abierto" if es_dia_mercado(ahora) else "cerrado (fin de semana)",
    }), 200

@app.route("/test", methods=["GET"])
def test():
    ahora = datetime.now(EST)
    enviar_telegram(
        f"✅ <b>SPY Alert System v6.0</b> activo\n"
        f"Hora: {ahora.strftime('%A %d/%m/%Y %H:%M EST')}\n"
        f"Mercado: {'Abierto' if es_dia_mercado(ahora) else 'Cerrado (fin de semana)'}"
    )
    return jsonify({"status": "ok"}), 200

@app.route("/reporte", methods=["GET"])
def reporte_manual():
    reporte_horario()
    return jsonify({"status": "reporte enviado"}), 200

@app.route("/verificar", methods=["GET"])
def verificar_manual():
    verificar_puntos()
    return jsonify({"status": "verificacion enviada"}), 200

if __name__ == "__main__":
    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()
    app.run(host="0.0.0.0", port=5000, debug=False)
