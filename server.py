#!/usr/bin/env python3
"""
Breakout Sentinel v6.6
- Fuente de datos: Twelve Data (principal) + Finnhub (backup)
- Reportes a las :01 de cada hora: 10,11,12,13,14,15,16 EST
- Solo Lunes a Viernes (mercado abierto)
- Vela 7 (4:00 PM) es de 30 minutos — se confirma igual a las 4:01 PM
- Techo, piso y mitad calculados dinamicamente hora a hora
- Distancia canal = P1 high - PISO (constante, paralelo)
- P2 se actualiza automaticamente si el high de la vela supera el techo
- Ruptura alcista: cierre > techo + vela verde + mecha <= 35%
- Ruptura sin confirmacion: cierre > techo pero vela roja o mecha > 35%
- Canal invalidado: P2 nuevo > P1 — sistema se apaga automaticamente
- Primera Vela Roja — alerta especial a las 10:01 reemplaza reporte normal
- endpoint /apagar para desactivar manualmente
- endpoint /piso para actualizar solo el piso sin tocar P1/P2
"""

import requests
import threading
import time
from datetime import datetime, timedelta
import pytz
from flask import Flask, jsonify, request

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
HORAS_REPORTE = [10, 11, 12, 13, 14, 15, 16]

# Mecha maxima para ruptura alcista confirmada
MECHA_MAX = 35

# ═══════════════════════════════════════════════════════════
# ESTADO DEL CANAL — mutable en runtime
# ═══════════════════════════════════════════════════════════
# P1 — FIJO, nunca se mueve
P1 = { "fecha": "2026-02-26", "hora_est": 10, "high": 693.29 }

# P2 — DINAMICO, se actualiza automaticamente
P2 = { "fecha": "2026-03-10", "hora_est": 14, "high": 683.36 }

# PISO — igual que P1 y P2: fecha, vela y low de la vela mas baja del canal
# La distancia se calcula en ese punto exacto (techo en esa vela - low)
# De ahi en adelante piso y mitad son dinamicos y paralelos al techo
PISO = { "fecha": "2026-03-30", "hora_est": 15, "low": 629.48 }

# Estado del sistema
SISTEMA_ACTIVO = True  # False = canal invalidado o apagado manualmente

# ═══════════════════════════════════════════════════════════
# HELPERS — DIA DE MERCADO
# ═══════════════════════════════════════════════════════════
def es_dia_mercado(dt=None):
    if dt is None:
        dt = datetime.now(EST)
    return dt.weekday() < 5

def es_hora_reporte(hora):
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
def get_vela_twelvedata():
    try:
        params = {
            "symbol":     "SPY",
            "interval":   "1h",
            "outputsize": 10,
            "timezone":   "America/New_York",
            "apikey":     TWELVEDATA_KEY,
        }
        url = "https://api.twelvedata.com/time_series"
        r = requests.get(url, params=params, timeout=15)
        data = r.json()

        if data.get("status") == "error" or "values" not in data:
            print(f"TwelveData error: {data.get('message', data)}")
            return None

        valores = data["values"]
        if len(valores) < 2:
            return None

        # valores[1] es la ultima vela cerrada
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
def get_vela_finnhub():
    try:
        ahora_est = datetime.now(EST)
        dt_fin    = ahora_est
        dt_inicio = ahora_est - timedelta(hours=12)
        ts_inicio = int(dt_inicio.timestamp())
        ts_fin    = int(dt_fin.timestamp())

        params = {
            "symbol":     "SPY",
            "resolution": "60",
            "from":       ts_inicio,
            "to":         ts_fin,
            "token":      FINNHUB_KEY,
        }
        r = requests.get("https://finnhub.io/api/v1/stock/candle", params=params, timeout=15)
        data = r.json()

        if data.get("s") != "ok" or not data.get("c"):
            print(f"Finnhub error: {data}")
            return None

        if len(data["c"]) < 2:
            return None

        # penultima = ultima cerrada
        i = -2
        dt = datetime.fromtimestamp(data["t"][i], tz=EST)
        return {
            "open":  data["o"][i],
            "high":  data["h"][i],
            "low":   data["l"][i],
            "close": data["c"][i],
            "time":  dt.strftime("%H:%M EST"),
        }
    except Exception as e:
        print(f"Error Finnhub: {e}")
        return None

# ═══════════════════════════════════════════════════════════
# OBTENER VELA — TwelveData primero, Finnhub como backup
# ═══════════════════════════════════════════════════════════
def get_ultima_vela():
    vela = get_vela_twelvedata()
    if vela:
        print("Datos: TwelveData ✅")
        return vela, "TwelveData"
    print("TwelveData fallo — intentando Finnhub...")
    vela = get_vela_finnhub()
    if vela:
        print("Datos: Finnhub ✅")
        return vela, "Finnhub"
    print("Ambas fuentes fallaron ❌")
    return None, None

# ═══════════════════════════════════════════════════════════
# CALCULAR TECHO DIAGONAL
# ═══════════════════════════════════════════════════════════
def calcular_techo(dt_referencia=None):
    """
    Calcula el techo al momento exacto indicado.
    Para reportes horarios pasar el cierre exacto de la vela.
    """
    fmt   = "%Y-%m-%d %H:%M"
    p1_dt = EST.localize(datetime.strptime(f"{P1['fecha']} {P1['hora_est']}:00", fmt))
    p2_dt = EST.localize(datetime.strptime(f"{P2['fecha']} {P2['hora_est']}:00", fmt))
    if dt_referencia is None:
        dt_referencia = datetime.now(EST)
    pendiente = (P2["high"] - P1["high"]) / (p2_dt.timestamp() - p1_dt.timestamp())
    techo = P1["high"] + pendiente * (dt_referencia.timestamp() - p1_dt.timestamp())
    return round(techo, 2)

# ═══════════════════════════════════════════════════════════
# CALCULAR PISO Y MITAD DEL CANAL
# ═══════════════════════════════════════════════════════════
def calcular_piso_y_mitad(dt_referencia=None):
    """
    Calcula el piso y la mitad del canal en un momento dado.
    La distancia se calcula en la barra del piso:
      distancia = techo en ese punto - low de esa vela
    De ahi en adelante piso y mitad son dinamicos y paralelos al techo.
    """
    fmt    = "%Y-%m-%d %H:%M"
    piso_dt = EST.localize(datetime.strptime(f"{PISO['fecha']} {PISO['hora_est']}:00", fmt))
    techo_en_piso = calcular_techo(piso_dt)
    distancia = round(techo_en_piso - PISO["low"], 2)
    techo     = calcular_techo(dt_referencia)
    piso      = round(techo - distancia, 2)
    mitad     = round(piso + distancia / 2, 2)
    return piso, mitad, distancia

# ═══════════════════════════════════════════════════════════
# ALERTA PRIMERA VELA ROJA — solo a las 10:01 AM
# ═══════════════════════════════════════════════════════════
def alerta_primera_vela_roja(vela, techo, fuente):
    """
    Evalua si la vela 1 cumple las condiciones de Primera Vela Roja.
    Condiciones:
      1. Vela roja (cierre < apertura)
      2. Open por debajo del techo (dentro del canal)
      3. Open en la mitad superior del canal (open >= mitad)
    Retorna True si envia alerta, False si no aplica.
    """
    cierre_vela = datetime.now(EST).replace(minute=0, second=0, microsecond=0)
    piso, mitad, distancia = calcular_piso_y_mitad(cierre_vela)

    vela_roja       = vela["close"] < vela["open"]
    open_bajo_techo = vela["open"] < techo
    open_mitad_sup  = vela["open"] >= mitad

    if vela_roja and open_bajo_techo and open_mitad_sup:
        enviar_telegram(
            f"🔻 <b>PRIMERA VELA ROJA — 10:00 EST</b>\n\n"
            f"<b>Techo:</b> ${techo:.2f}\n"
            f"<b>Mitad canal:</b> ${mitad:.2f}\n"
            f"<b>Piso:</b> ${piso:.2f}\n\n"
            f"<b>Open vela:</b> ${vela['open']:.2f} ✅ mitad superior\n"
            f"<b>Cierre vela:</b> ${vela['close']:.2f}\n"
            f"<b>Fuente:</b> {fuente}\n\n"
            f"⚠️ <b>Vela roja dentro del canal — vigilar continuacion bajista</b>"
        )
        return True

    # Si no cumple condiciones — reportar por que no aplico
    razones = []
    if not vela_roja:       razones.append("vela no es roja")
    if not open_bajo_techo: razones.append(f"open ${vela['open']:.2f} supera techo ${techo:.2f}")
    if not open_mitad_sup:  razones.append(f"open ${vela['open']:.2f} bajo mitad ${mitad:.2f}")
    print(f"Primera Vela Roja no aplica: {', '.join(razones)}")
    return False
def actualizar_p2(nuevo_high, ahora_est):
    """Actualiza P2 al high de la vela actual."""
    global P2
    P2_anterior = P2["high"]
    P2 = {
        "fecha":    ahora_est.strftime("%Y-%m-%d"),
        "hora_est": ahora_est.hour,
        "high":     round(nuevo_high, 2)
    }
    print(f"P2 actualizado: ${P2_anterior:.2f} → ${nuevo_high:.2f}")
    return P2_anterior

# ═══════════════════════════════════════════════════════════
# APAGAR SISTEMA
# ═══════════════════════════════════════════════════════════
def apagar_sistema(motivo):
    global SISTEMA_ACTIVO
    SISTEMA_ACTIVO = False
    enviar_telegram(
        f"🏁 <b>CANAL INVALIDADO — SISTEMA APAGADO</b>\n\n"
        f"{motivo}\n\n"
        f"El sistema queda dormido.\n"
        f"Reactivar cuando identifiques nuevo canal bajista."
    )
    print(f"Sistema apagado: {motivo}")

# ═══════════════════════════════════════════════════════════
# REPORTE HORARIO
# ═══════════════════════════════════════════════════════════
def reporte_horario():
    global SISTEMA_ACTIVO

    if not SISTEMA_ACTIVO:
        print("Sistema apagado — sin reporte.")
        return

    ahora_est = datetime.now(EST)

    # Filtro 1: Solo Lunes a Viernes
    if not es_dia_mercado(ahora_est):
        print(f"Fin de semana — sin reporte: {ahora_est.strftime('%A %H:%M EST')}")
        return

    hora = ahora_est.hour

    # Filtro 2: Solo en horas de reporte
    if not es_hora_reporte(hora):
        print(f"Fuera de horario: {ahora_est.strftime('%H:%M EST')}")
        return

    vela_num      = hora - 9
    hora_label    = f"{hora}:00 EST"
    es_ultima     = (hora == 16)
    nota_vela     = " <i>(vela 30 min)</i>" if es_ultima else ""
    proxima       = f"{hora + 1}:00 EST" if hora < 16 else ("apertura del lunes" if ahora_est.weekday() == 4 else "apertura manana")

    # Techo al cierre exacto de la vela
    cierre_vela = ahora_est.replace(minute=0, second=0, microsecond=0)
    techo = calcular_techo(cierre_vela)

    vela, fuente = get_ultima_vela()

    if not vela:
        enviar_telegram(
            f"⚠️ <b>Breakout Sentinel — {hora_label} — Vela {vela_num}</b>\n"
            f"No se pudo obtener datos de SPY.\n"
            f"Sistema activo — proxima: {proxima}"
        )
        return

    # ── A las 10:01 — evaluar Primera Vela Roja primero ─
    if hora == 10:
        aplico = alerta_primera_vela_roja(vela, techo, fuente)
        if aplico:
            return  # reemplaza el reporte normal de las 10:01

    # ── Analisis de la vela ──────────────────────────────
    vela_verde  = vela["close"] > vela["open"]
    rango       = vela["high"] - vela["low"]
    mecha_sup   = vela["high"] - max(vela["close"], vela["open"])
    mecha_pct   = (mecha_sup / rango * 100) if rango > 0 else 0
    mecha_ok    = mecha_pct <= MECHA_MAX
    high_rompe  = vela["high"] > techo    # high supero el techo
    cierre_rompe = vela["close"] > techo  # cierre supero el techo

    # ── Actualizar P2 si el high supero el techo ────────
    p2_actualizado = False
    p2_anterior    = None
    if high_rompe:
        p2_anterior    = actualizar_p2(vela["high"], ahora_est)
        p2_actualizado = True

        # Verificar si el nuevo P2 invalida el canal
        if P2["high"] >= P1["high"]:
            apagar_sistema(
                f"P2 nuevo ${P2['high']:.2f} supera a P1 ${P1['high']:.2f}\n"
                f"El canal bajista ya no es valido."
            )
            return

    # ── Clasificar el evento ────────────────────────────
    nota_p2 = ""
    if p2_actualizado:
        nota_p2 = f"\n📌 <b>P2 actualizado:</b> ${p2_anterior:.2f} → ${P2['high']:.2f}"

    if cierre_rompe and vela_verde and mecha_ok:
        # RUPTURA ALCISTA COMPLETA
        enviar_telegram(
            f"🟢 <b>BREAKOUT SENTINEL — RUPTURA ALCISTA</b>\n"
            f"<b>Hora:</b> {hora_label} — Vela {vela_num}{nota_vela}\n\n"
            f"<b>Techo:</b> ${techo:.2f}\n"
            f"<b>Cierre:</b> ${vela['close']:.2f}\n"
            f"<b>High:</b> ${vela['high']:.2f}\n"
            f"<b>Mecha sup:</b> {mecha_pct:.0f}%\n"
            f"<b>Fuente:</b> {fuente}"
            f"{nota_p2}\n\n"
            f"⚡ <b>EVALUAR ENTRADA CALL</b>"
        )

    elif cierre_rompe:
        # RUPTURA SIN CONFIRMACION ALCISTA
        razon = []
        if not vela_verde: razon.append("vela roja")
        if not mecha_ok:   razon.append(f"mecha {mecha_pct:.0f}% > {MECHA_MAX}%")
        enviar_telegram(
            f"⚠️ <b>BREAKOUT SENTINEL — RUPTURA SIN CONFIRMACION</b>\n"
            f"<b>Hora:</b> {hora_label} — Vela {vela_num}{nota_vela}\n\n"
            f"<b>Techo:</b> ${techo:.2f}\n"
            f"<b>Cierre:</b> ${vela['close']:.2f}\n"
            f"<b>High:</b> ${vela['high']:.2f}\n"
            f"<b>Razon:</b> {', '.join(razon)}\n"
            f"<b>Fuente:</b> {fuente}"
            f"{nota_p2}\n\n"
            f"❌ <b>NO ENTRAR — vigilar proxima vela</b>"
        )

    else:
        # SIN RUPTURA
        razon = []
        if not vela_verde:   razon.append("vela roja")
        if not cierre_rompe: razon.append(f"cierre ${vela['close']:.2f} bajo techo ${techo:.2f}")

        enviar_telegram(
            f"🔴 <b>Breakout Sentinel — Sin ruptura</b>\n"
            f"<b>Hora:</b> {hora_label} — Vela {vela_num}{nota_vela}\n\n"
            f"<b>Techo:</b> ${techo:.2f}\n"
            f"<b>Cierre:</b> ${vela['close']:.2f}\n"
            f"<b>Vela:</b> {'Verde' if vela_verde else 'Roja'} | Mecha: {mecha_pct:.0f}%\n"
            f"<b>Razon:</b> {', '.join(razon)}\n"
            f"<b>Fuente:</b> {fuente}"
            f"{nota_p2}\n\n"
            f"Sistema activo — proxima: {proxima}"
        )

# ═══════════════════════════════════════════════════════════
# LOOP
# ═══════════════════════════════════════════════════════════
def monitor_loop():
    print("Breakout Sentinel v6.6 iniciado...")
    while True:
        ahora = datetime.now(EST)
        minutos_hasta_01 = (1 - ahora.minute) % 60
        if minutos_hasta_01 == 0:
            minutos_hasta_01 = 60
        segundos_espera = minutos_hasta_01 * 60 - ahora.second
        print(f"Proximo chequeo en {minutos_hasta_01} min | {ahora.strftime('%A %H:%M EST')}")
        time.sleep(segundos_espera)
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
    cierre_vela = ahora.replace(minute=0, second=0, microsecond=0)
    techo = calcular_techo(cierre_vela)
    piso, mitad, distancia = calcular_piso_y_mitad(cierre_vela)
    return jsonify({
        "sistema":  "Breakout Sentinel v6.6",
        "estado":   "activo" if SISTEMA_ACTIVO else "apagado",
        "hora_est": ahora.strftime("%A %H:%M EST"),
        "mercado":  "abierto" if es_dia_mercado(ahora) else "cerrado (fin de semana)",
        "P1":       P1,
        "P2":       P2,
        "techo_actual": techo,
        "piso_actual":  piso,
        "mitad_canal":  mitad,
    }), 200

@app.route("/test", methods=["GET"])
def test():
    ahora = datetime.now(EST)
    cierre_vela = ahora.replace(minute=0, second=0, microsecond=0)
    techo = calcular_techo(cierre_vela)
    piso, mitad, distancia = calcular_piso_y_mitad(cierre_vela)
    enviar_telegram(
        f"✅ <b>Breakout Sentinel v6.6</b>\n"
        f"Estado: {'Activo' if SISTEMA_ACTIVO else 'Apagado'}\n"
        f"Hora: {ahora.strftime('%A %d/%m/%Y %H:%M EST')}\n"
        f"Mercado: {'Abierto' if es_dia_mercado(ahora) else 'Cerrado (fin de semana)'}\n\n"
        f"<b>P1:</b> ${P1['high']:.2f} ({P1['fecha']})\n"
        f"<b>P2:</b> ${P2['high']:.2f} ({P2['fecha']})\n"
        f"<b>Techo ahora:</b> ${techo:.2f}\n"
        f"<b>Mitad canal:</b> ${mitad:.2f}\n"
        f"<b>Piso:</b> ${piso:.2f}"
    )
    return jsonify({"status": "ok"}), 200

@app.route("/reporte", methods=["GET"])
def reporte_manual():
    reporte_horario()
    return jsonify({"status": "reporte enviado"}), 200

@app.route("/apagar", methods=["GET"])
def apagar_manual():
    """Apaga el sistema manualmente."""
    apagar_sistema("Apagado manualmente por el operador.")
    return jsonify({"status": "sistema apagado"}), 200

@app.route("/piso", methods=["GET"])
def actualizar_piso():
    """Actualiza el piso del canal sin tocar P1/P2.
    Uso: /piso?fecha=2026-03-30&vela=6&low=629.48
    vela = numero de vela 1-7 (hora final)
    """
    global PISO
    try:
        vela_num = int(request.args["vela"])
        hora_map = {1:10, 2:11, 3:12, 4:13, 5:14, 6:15, 7:16}
        PISO = {
            "fecha":    request.args["fecha"],
            "hora_est": hora_map[vela_num],
            "low":      float(request.args["low"]),
        }
        techo = calcular_techo()
        piso, mitad, distancia = calcular_piso_y_mitad()
        enviar_telegram(
            f"📐 <b>Piso del canal actualizado</b>\n\n"
            f"<b>Fecha piso:</b> {PISO['fecha']} Vela {vela_num}\n"
            f"<b>Low piso:</b> ${PISO['low']:.2f}\n"
            f"<b>Distancia canal:</b> ${distancia:.2f}\n\n"
            f"<b>Techo ahora:</b> ${techo:.2f}\n"
            f"<b>Mitad canal:</b> ${mitad:.2f}\n"
            f"<b>Piso ahora:</b> ${piso:.2f}"
        )
        return jsonify({"status": "piso actualizado", "piso": PISO, "mitad": mitad, "distancia": distancia}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/activar", methods=["GET"])
def activar():
    """Reactiva el sistema con nuevos P1, P2 y piso.
    Uso: /activar?p1_fecha=2026-02-26&p1_hora=10&p1_high=693.29
                 &p2_fecha=2026-03-10&p2_hora=14&p2_high=683.36
                 &piso_fecha=2026-03-30&piso_vela=6&piso_low=629.48
    """
    global P1, P2, PISO, SISTEMA_ACTIVO
    try:
        P1 = {
            "fecha":    request.args["p1_fecha"],
            "hora_est": int(request.args["p1_hora"]),
            "high":     float(request.args["p1_high"]),
        }
        P2 = {
            "fecha":    request.args["p2_fecha"],
            "hora_est": int(request.args["p2_hora"]),
            "high":     float(request.args["p2_high"]),
        }
        vela_map = {1:10, 2:11, 3:12, 4:13, 5:14, 6:15, 7:16}
        piso_vela = int(request.args.get("piso_vela", 6))
        PISO = {
            "fecha":    request.args.get("piso_fecha", PISO["fecha"]),
            "hora_est": vela_map[piso_vela],
            "low":      float(request.args.get("piso_low", PISO["low"])),
        }
        SISTEMA_ACTIVO = True

        techo = calcular_techo()
        piso, mitad, distancia = calcular_piso_y_mitad()

        enviar_telegram(
            f"✅ <b>Breakout Sentinel — REACTIVADO</b>\n\n"
            f"<b>P1:</b> ${P1['high']:.2f} — {P1['fecha']} Vela {request.args['p1_hora']}\n"
            f"<b>P2:</b> ${P2['high']:.2f} — {P2['fecha']} Vela {request.args['p2_hora']}\n"
            f"<b>Piso:</b> ${PISO['low']:.2f} — {PISO['fecha']} Vela {piso_vela}\n"
            f"<b>Distancia canal:</b> ${distancia:.2f}\n\n"
            f"<b>Techo ahora:</b> ${techo:.2f}\n"
            f"<b>Mitad canal:</b> ${mitad:.2f}\n"
            f"<b>Piso ahora:</b> ${piso:.2f}\n\n"
            f"Sistema activo — monitoreando canal bajista."
        )
        return jsonify({"status": "sistema reactivado", "P1": P1, "P2": P2, "PISO": PISO}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ═══════════════════════════════════════════════════════════
# ARRANQUE DEL MONITOR — funciona con gunicorn Y python directo
# Delay de 5 segundos para que Flask responda primero al health check
# ═══════════════════════════════════════════════════════════
def arrancar_monitor():
    time.sleep(5)
    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()

threading.Thread(target=arrancar_monitor, daemon=True).start()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
