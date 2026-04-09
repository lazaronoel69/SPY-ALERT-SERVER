#!/usr/bin/env python3
"""
Breakout Sentinel v6.8
- Fuente de datos: Twelve Data (principal) + Finnhub (backup)
- Reportes a las :01 de cada hora: 10,11,12,13,14,15,16 EST
- Solo Lunes a Viernes y dias habiles del mercado americano
- Festivos calculados automaticamente para cualquier año
- P1, P2 y Piso sin valores hardcodeados — solo el operador los activa
- Sin actualizacion automatica de P2 — solo el operador lo actualiza
- 1VR simplificado: unica condicion es Vela 1 roja (cierre < open)
- Canal inactivo por defecto — se activa via /activar
- Techo, piso y mitad calculados dinamicamente hora a hora
- Ruptura alcista: cierre > techo + vela verde + mecha <= 35%
- Canal invalidado: P2 nuevo >= P1 — sistema se apaga
- endpoint /apagar para desactivar manualmente
- endpoint /piso para actualizar piso con fecha+vela+low
- endpoint /activar para activar canal con P1, P2 y Piso
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
# ESTADO DEL CANAL — solo el operador activa via /activar
# Sin valores hardcodeados — canal inactivo hasta que el operador lo active
# ═══════════════════════════════════════════════════════════
P1   = None  # Se activa via /activar
P2   = None  # Se activa via /activar
PISO = None  # Se activa via /activar

# Estado del sistema
CANAL_ACTIVO   = False  # True solo cuando el operador activa via /activar
SISTEMA_ACTIVO = True   # False = apagado manualmente

# ═══════════════════════════════════════════════════════════
# HELPERS — DIA DE MERCADO
# Festivos calculados automaticamente para cualquier año
# ═══════════════════════════════════════════════════════════
def calcular_pascua(year):
    """Algoritmo de Gauss para calcular el Domingo de Pascua."""
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
    """
    Calcula los dias festivos del mercado americano para un año dado.
    Se recalcula automaticamente — no hay que tocar el codigo nunca.
    """
    from datetime import date, timedelta

    festivos = set()

    def observado(d):
        """Si cae Sabado → Viernes anterior. Si cae Domingo → Lunes siguiente."""
        if d.weekday() == 5:  # Sabado
            return d - timedelta(days=1)
        if d.weekday() == 6:  # Domingo
            return d + timedelta(days=1)
        return d

    def nth_weekday(year, month, weekday, n):
        """N-esimo dia de la semana en un mes. weekday: 0=Lunes, 4=Viernes."""
        d = date(year, month, 1)
        days_ahead = weekday - d.weekday()
        if days_ahead < 0:
            days_ahead += 7
        d = d + timedelta(days=days_ahead)
        return d + timedelta(weeks=n - 1)

    def last_weekday(year, month, weekday):
        """Ultimo dia de la semana en un mes."""
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        d = date(year, month, last_day)
        days_back = (d.weekday() - weekday) % 7
        return d - timedelta(days=days_back)

    # New Year's Day — 1 Enero
    festivos.add(observado(date(year, 1, 1)))

    # MLK Day — 3er Lunes de Enero
    festivos.add(nth_weekday(year, 1, 0, 3))

    # Presidents Day — 3er Lunes de Febrero
    festivos.add(nth_weekday(year, 2, 0, 3))

    # Good Friday — Viernes antes del Domingo de Pascua
    pascua = calcular_pascua(year)
    good_friday = pascua - timedelta(days=2)
    festivos.add(good_friday)

    # Memorial Day — ultimo Lunes de Mayo
    festivos.add(last_weekday(year, 5, 0))

    # Juneteenth — 19 Junio
    festivos.add(observado(date(year, 6, 19)))

    # Independence Day — 4 Julio
    festivos.add(observado(date(year, 7, 4)))

    # Labor Day — 1er Lunes de Septiembre
    festivos.add(nth_weekday(year, 9, 0, 1))

    # Thanksgiving — 4to Jueves de Noviembre
    festivos.add(nth_weekday(year, 11, 3, 4))

    # Christmas — 25 Diciembre
    festivos.add(observado(date(year, 12, 25)))

    return festivos

# Cache de festivos por año para no recalcular en cada llamada
_festivos_cache = {}

def es_dia_mercado(dt=None):
    """Retorna True si el mercado esta abierto — no es fin de semana ni festivo."""
    from datetime import date
    if dt is None:
        dt = datetime.now(EST)
    if dt.weekday() >= 5:  # Sabado o Domingo
        return False
    año = dt.year
    if año not in _festivos_cache:
        _festivos_cache[año] = calcular_festivos(año)
    return date(dt.year, dt.month, dt.day) not in _festivos_cache[año]

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
    """Calcula el techo al momento exacto. Retorna None si canal no activo."""
    if not CANAL_ACTIVO or P1 is None or P2 is None:
        return None
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
    """Calcula piso y mitad. Retorna None, None, None si canal no activo."""
    if not CANAL_ACTIVO or PISO is None:
        return None, None, None
    fmt     = "%Y-%m-%d %H:%M"
    piso_dt = EST.localize(datetime.strptime(f"{PISO['fecha']} {PISO['hora_est']}:00", fmt))
    techo_en_piso = calcular_techo(piso_dt)
    if techo_en_piso is None:
        return None, None, None
    distancia = round(techo_en_piso - PISO["low"], 2)
    techo     = calcular_techo(dt_referencia)
    if techo is None:
        return None, None, None
    piso      = round(techo - distancia, 2)
    mitad     = round(piso + distancia / 2, 2)
    return piso, mitad, distancia

# ═══════════════════════════════════════════════════════════
# ALERTA PRIMERA VELA ROJA — solo a las 10:01 AM
# ═══════════════════════════════════════════════════════════
def alerta_primera_vela_roja(vela, fuente):
    """
    1VR — Primera Vela Roja.
    Unica condicion: Vela 1 es roja (cierre < apertura).
    Retorna True si envia alerta.
    """
    if vela["close"] < vela["open"]:
        cierre_vela = datetime.now(EST).replace(minute=0, second=0, microsecond=0)
        techo = calcular_techo(cierre_vela)
        piso, mitad, distancia = calcular_piso_y_mitad(cierre_vela)
        enviar_telegram(
            f"🔻 <b>PRIMERA VELA ROJA — 10:00 EST</b>\n\n"
            f"<b>Open:</b> ${vela['open']:.2f}\n"
            f"<b>Cierre:</b> ${vela['close']:.2f}\n"
            f"<b>Fuente:</b> {fuente}\n"
            + (f"\n<b>Techo:</b> ${techo:.2f}\n<b>Mitad:</b> ${mitad:.2f}\n<b>Piso:</b> ${piso:.2f}" if techo else "") +
            f"\n\n⚠️ <b>Vela 1 roja — vigilar continuacion bajista</b>"
        )
        return True
    return False

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

    vela, fuente = get_ultima_vela()

    if not vela:
        enviar_telegram(
            f"⚠️ <b>Breakout Sentinel — {hora_label} — Vela {vela_num}</b>\n"
            f"No se pudo obtener datos de SPY.\n"
            f"Sistema activo — proxima: {proxima}"
        )
        return

    # ── A las 10:01 — evaluar Primera Vela Roja ─────────
    # Condicion unica: Vela 1 roja
    if hora == 10:
        aplico = alerta_primera_vela_roja(vela, fuente)
        if aplico:
            return  # 1VR reemplaza el reporte normal de las 10:01

    # ── Si canal no esta activo — no hay reporte BS ──────
    if not CANAL_ACTIVO:
        print(f"Canal no activo — sin reporte BS: {hora_label}")
        return

    # ── Techo al cierre exacto de la vela ───────────────
    cierre_vela  = ahora_est.replace(minute=0, second=0, microsecond=0)
    techo        = calcular_techo(cierre_vela)
    piso, mitad, distancia = calcular_piso_y_mitad(cierre_vela)

    if techo is None:
        return

    # ── Analisis de la vela ──────────────────────────────
    vela_verde   = vela["close"] > vela["open"]
    rango        = vela["high"] - vela["low"]
    mecha_sup    = vela["high"] - max(vela["close"], vela["open"])
    mecha_pct    = (mecha_sup / rango * 100) if rango > 0 else 0
    mecha_ok     = mecha_pct <= MECHA_MAX
    cierre_rompe = vela["close"] > techo

    if cierre_rompe and vela_verde and mecha_ok:
        enviar_telegram(
            f"🟢 <b>BREAKOUT SENTINEL — RUPTURA ALCISTA</b>\n"
            f"<b>Hora:</b> {hora_label} — Vela {vela_num}{nota_vela}\n\n"
            f"<b>Techo:</b> ${techo:.2f}\n"
            f"<b>Mitad:</b> ${mitad:.2f}\n"
            f"<b>Piso:</b> ${piso:.2f}\n"
            f"<b>Cierre:</b> ${vela['close']:.2f}\n"
            f"<b>High:</b> ${vela['high']:.2f}\n"
            f"<b>Mecha sup:</b> {mecha_pct:.0f}%\n"
            f"<b>Fuente:</b> {fuente}\n\n"
            f"⚡ <b>EVALUAR ENTRADA CALL</b>"
        )

    elif cierre_rompe:
        razon = []
        if not vela_verde: razon.append("vela roja")
        if not mecha_ok:   razon.append(f"mecha {mecha_pct:.0f}% > {MECHA_MAX}%")
        enviar_telegram(
            f"⚠️ <b>BREAKOUT SENTINEL — RUPTURA SIN CONFIRMACION</b>\n"
            f"<b>Hora:</b> {hora_label} — Vela {vela_num}{nota_vela}\n\n"
            f"<b>Techo:</b> ${techo:.2f}\n"
            f"<b>Mitad:</b> ${mitad:.2f}\n"
            f"<b>Piso:</b> ${piso:.2f}\n"
            f"<b>Cierre:</b> ${vela['close']:.2f}\n"
            f"<b>High:</b> ${vela['high']:.2f}\n"
            f"<b>Razon:</b> {', '.join(razon)}\n"
            f"<b>Fuente:</b> {fuente}\n\n"
            f"❌ <b>NO ENTRAR — vigilar proxima vela</b>"
        )

    else:
        razon = []
        if not vela_verde:   razon.append("vela roja")
        if not cierre_rompe: razon.append(f"cierre ${vela['close']:.2f} bajo techo ${techo:.2f}")
        enviar_telegram(
            f"🔴 <b>Breakout Sentinel — Sin ruptura</b>\n"
            f"<b>Hora:</b> {hora_label} — Vela {vela_num}{nota_vela}\n\n"
            f"<b>Techo:</b> ${techo:.2f}\n"
            f"<b>Mitad:</b> ${mitad:.2f}\n"
            f"<b>Piso:</b> ${piso:.2f}\n"
            f"<b>Cierre:</b> ${vela['close']:.2f}\n"
            f"<b>Vela:</b> {'Verde' if vela_verde else 'Roja'} | Mecha: {mecha_pct:.0f}%\n"
            f"<b>Razon:</b> {', '.join(razon)}\n"
            f"<b>Fuente:</b> {fuente}\n\n"
            f"Sistema activo — proxima: {proxima}"
        )

# ═══════════════════════════════════════════════════════════
# LOOP
# ═══════════════════════════════════════════════════════════
def monitor_loop():
    print("Breakout Sentinel v6.8 iniciado...")
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
        "sistema":      "Breakout Sentinel v6.8",
        "estado":       "activo" if SISTEMA_ACTIVO else "apagado",
        "canal_activo": CANAL_ACTIVO,
        "hora_est":     ahora.strftime("%A %H:%M EST"),
        "mercado":      "abierto" if es_dia_mercado(ahora) else "cerrado",
        "P1":           P1,
        "P2":           P2,
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
    canal_info = ""
    if CANAL_ACTIVO and techo:
        canal_info = (
            f"\n<b>P1:</b> ${P1['high']:.2f} ({P1['fecha']})\n"
            f"<b>P2:</b> ${P2['high']:.2f} ({P2['fecha']})\n"
            f"<b>Techo ahora:</b> ${techo:.2f}\n"
            f"<b>Mitad canal:</b> ${mitad:.2f}\n"
            f"<b>Piso:</b> ${piso:.2f}"
        )
    else:
        canal_info = "\n<b>Canal:</b> Sin activar — usar /activar para definir P1, P2 y Piso"
    enviar_telegram(
        f"✅ <b>Breakout Sentinel v6.8</b>\n"
        f"Estado: {'Activo' if SISTEMA_ACTIVO else 'Apagado'}\n"
        f"Canal: {'Activo' if CANAL_ACTIVO else 'Sin activar'}\n"
        f"Hora: {ahora.strftime('%A %d/%m/%Y %H:%M EST')}\n"
        f"Mercado: {'Abierto' if es_dia_mercado(ahora) else 'Cerrado'}"
        f"{canal_info}"
    )
    return jsonify({"status": "ok"}), 200

@app.route("/reporte", methods=["GET"])
def reporte_manual():
    reporte_horario()
    return jsonify({"status": "reporte enviado"}), 200

@app.route("/apagar", methods=["GET"])
def apagar_manual():
    apagar_sistema("Apagado manualmente por el operador.")
    return jsonify({"status": "sistema apagado"}), 200

@app.route("/piso", methods=["GET"])
def actualizar_piso():
    """Actualiza el piso del canal sin tocar P1/P2.
    Uso: /piso?fecha=2026-03-30&vela=6&low=629.48
    """
    global PISO
    if not CANAL_ACTIVO:
        return jsonify({"error": "Canal no activo. Usar /activar primero."}), 400
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
    """Activa el canal con P1, P2 y Piso definidos por el operador.
    Uso: /activar?p1_fecha=2026-02-26&p1_hora=10&p1_high=693.29
                 &p2_fecha=2026-04-08&p2_hora=10&p2_high=XXX.XX
                 &piso_fecha=2026-03-30&piso_vela=6&piso_low=629.48
    p1_hora y p2_hora = hora final AXIS (10=Vela1, 11=Vela2, etc.)
    piso_vela = numero de vela 1-7
    """
    global P1, P2, PISO, CANAL_ACTIVO, SISTEMA_ACTIVO
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
        vela_map  = {1:10, 2:11, 3:12, 4:13, 5:14, 6:15, 7:16}
        piso_vela = int(request.args["piso_vela"])
        PISO = {
            "fecha":    request.args["piso_fecha"],
            "hora_est": vela_map[piso_vela],
            "low":      float(request.args["piso_low"]),
        }
        CANAL_ACTIVO   = True
        SISTEMA_ACTIVO = True

        techo = calcular_techo()
        piso, mitad, distancia = calcular_piso_y_mitad()

        enviar_telegram(
            f"✅ <b>AXIS — Canal Activado</b>\n\n"
            f"<b>P1:</b> ${P1['high']:.2f} — {P1['fecha']} {P1['hora_est']}:00 EST\n"
            f"<b>P2:</b> ${P2['high']:.2f} — {P2['fecha']} {P2['hora_est']}:00 EST\n"
            f"<b>Piso:</b> ${PISO['low']:.2f} — {PISO['fecha']} Vela {piso_vela}\n"
            f"<b>Distancia canal:</b> ${distancia:.2f}\n\n"
            f"<b>Techo ahora:</b> ${techo:.2f}\n"
            f"<b>Mitad canal:</b> ${mitad:.2f}\n"
            f"<b>Piso ahora:</b> ${piso:.2f}\n\n"
            f"Sistema activo — monitoreando canal bajista."
        )
        return jsonify({"status": "canal activado", "P1": P1, "P2": P2, "PISO": PISO}), 200
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
