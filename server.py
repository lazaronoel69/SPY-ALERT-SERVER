#!/usr/bin/env python3
"""
Breakout Sentinel v7.0
Estrategias: 1VR | RPG | GNA | GBA | RCB/CNF
SPY — reportes hora a hora — alertas a Telegram
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
TELEGRAM_TOKEN   = "8668514895:AAGWRxFmA9c8tZKIe-5i9tJ31RQtzi1-NYs"
TELEGRAM_CHAT_ID = "-5010153427"
TWELVEDATA_KEY   = "66dd71373a884f7bb7da8e6e5e469571"
FINNHUB_KEY      = "d71aocpr01qot5jcnohgd71aocpr01qot5jcnoi0"
EST              = pytz.timezone("America/New_York")

HORAS_REPORTE = [10, 11, 12, 13, 14, 15, 16]
SISTEMA_ACTIVO = True

# Switches estrategias
VR1_ON = True
RPG_ON = True
GNA_ON = True
GBA_ON = True
CANAL_ON = False  # Se activa via /activar

# Canal RCB/CNF
P1   = None
P2   = None
PISO = None
CANAL_ACTIVO = False

# Estado diario — se resetea cada dia
estado_dia = {
    "fecha":          None,
    "v1_close":       None,  # cierre de V1
    "v1_open":        None,  # apertura de V1
    "v7_ayer_close":  None,  # cierre V7 del dia anterior
    "rpg_piso":       None,  # low de V1 si RPG activo
    "rpg_activo":     False,
    "rpg_fired":      False,
    "gna_activo":     False,
    "gna_fired":      False,
    "gba_activo":     False,
    "gba_fired":      False,
    "vr1_fired":      False,
}

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
        print(f"Telegram: {r.status_code}")
    except Exception as e:
        print(f"Error Telegram: {e}")

# ═══════════════════════════════════════════════════════════
# TWELVE DATA — obtener velas historicas
# ═══════════════════════════════════════════════════════════
def get_velas_twelvedata(outputsize=30):
    try:
        params = {
            "symbol":     "SPY",
            "interval":   "1h",
            "outputsize": outputsize,
            "timezone":   "America/New_York",
            "apikey":     TWELVEDATA_KEY,
        }
        r = requests.get("https://api.twelvedata.com/time_series", params=params, timeout=15)
        data = r.json()
        if data.get("status") == "error" or "values" not in data:
            print(f"TwelveData error: {data.get('message', data)}")
            return None
        return data["values"]  # lista de velas, la mas reciente primero
    except Exception as e:
        print(f"Error TwelveData: {e}")
        return None

def get_vela_finnhub():
    try:
        ahora_est = datetime.now(EST)
        ts_inicio = int((ahora_est - timedelta(hours=12)).timestamp())
        ts_fin    = int(ahora_est.timestamp())
        params = {"symbol": "SPY", "resolution": "60", "from": ts_inicio, "to": ts_fin, "token": FINNHUB_KEY}
        r = requests.get("https://finnhub.io/api/v1/stock/candle", params=params, timeout=15)
        data = r.json()
        if data.get("s") != "ok" or not data.get("c") or len(data["c"]) < 2:
            return None
        i = -2
        dt = datetime.fromtimestamp(data["t"][i], tz=EST)
        return {"open": data["o"][i], "high": data["h"][i], "low": data["l"][i], "close": data["c"][i], "datetime": dt.strftime("%Y-%m-%d %H:%M:%S")}
    except Exception as e:
        print(f"Error Finnhub: {e}")
        return None

# ═══════════════════════════════════════════════════════════
# CALCULAR SMA
# ═══════════════════════════════════════════════════════════
def calcular_sma(velas, periodo):
    """Calcula SMA del cierre de las ultimas N velas."""
    if len(velas) < periodo:
        return None
    cierres = [float(v["close"]) for v in velas[:periodo]]
    return sum(cierres) / periodo

# ═══════════════════════════════════════════════════════════
# RESET DIARIO
# ═══════════════════════════════════════════════════════════
def reset_diario(fecha_hoy, v7_ayer_close):
    global estado_dia
    estado_dia = {
        "fecha":         fecha_hoy,
        "v1_close":      None,
        "v1_open":       None,
        "v7_ayer_close": v7_ayer_close,
        "rpg_piso":      None,
        "rpg_activo":    False,
        "rpg_fired":     False,
        "gna_activo":    False,
        "gna_fired":     False,
        "gba_activo":    False,
        "gba_fired":     False,
        "vr1_fired":     False,
    }
    print(f"Reset diario — V7 ayer: ${v7_ayer_close:.2f}" if v7_ayer_close else "Reset diario — sin V7 ayer")

# ═══════════════════════════════════════════════════════════
# CANAL RCB/CNF
# ═══════════════════════════════════════════════════════════
def calcular_techo(dt_ref=None):
    if not CANAL_ACTIVO or P1 is None or P2 is None:
        return None
    fmt   = "%Y-%m-%d %H:%M"
    p1_dt = EST.localize(datetime.strptime(f"{P1['fecha']} {P1['hora_est']}:00", fmt))
    p2_dt = EST.localize(datetime.strptime(f"{P2['fecha']} {P2['hora_est']}:00", fmt))
    if dt_ref is None:
        dt_ref = datetime.now(EST)
    pendiente = (P2["high"] - P1["high"]) / (p2_dt.timestamp() - p1_dt.timestamp())
    return round(P1["high"] + pendiente * (dt_ref.timestamp() - p1_dt.timestamp()), 2)

def calcular_piso_mitad(dt_ref=None):
    if not CANAL_ACTIVO or PISO is None:
        return None, None
    fmt     = "%Y-%m-%d %H:%M"
    piso_dt = EST.localize(datetime.strptime(f"{PISO['fecha']} {PISO['hora_est']}:00", fmt))
    techo_en_piso = calcular_techo(piso_dt)
    if techo_en_piso is None:
        return None, None
    distancia = techo_en_piso - PISO["low"]
    techo = calcular_techo(dt_ref)
    if techo is None:
        return None, None
    return round(techo - distancia, 2), round(techo - distancia / 2, 2)

# ═══════════════════════════════════════════════════════════
# REPORTE HORARIO PRINCIPAL
# ═══════════════════════════════════════════════════════════
def reporte_horario():
    global estado_dia, CANAL_ACTIVO

    if not SISTEMA_ACTIVO:
        return

    ahora = datetime.now(EST)
    if not es_dia_mercado(ahora):
        print(f"No es dia de mercado: {ahora.strftime('%A %H:%M EST')}")
        return

    hora = ahora.hour
    if hora not in HORAS_REPORTE:
        print(f"Fuera de horario: {ahora.strftime('%H:%M EST')}")
        return

    fecha_hoy = ahora.strftime("%Y-%m-%d")

    # Obtener velas historicas
    velas = get_velas_twelvedata(outputsize=30)
    if not velas:
        vela_backup = get_vela_finnhub()
        if not vela_backup:
            enviar_telegram("⚠️ No se pudo obtener datos de SPY.")
            return
        velas = [vela_backup]

    print("Datos: TwelveData ✅")

    # Vela actual cerrada = velas[1] (velas[0] es la que esta formandose)
    vela_actual = {
        "open":     float(velas[1]["open"]),
        "high":     float(velas[1]["high"]),
        "low":      float(velas[1]["low"]),
        "close":    float(velas[1]["close"]),
        "datetime": velas[1]["datetime"],
    }

    # Calcular SMAs usando velas[1] en adelante (cerradas)
    sma20 = calcular_sma(velas[1:], 20)
    sma40 = calcular_sma(velas[1:], 40)
    tendencia_alza = sma20 is not None and sma40 is not None and sma20 > sma40

    # Reset diario si es nuevo dia
    if estado_dia["fecha"] != fecha_hoy:
        # Buscar cierre V7 del dia anterior en el historico
        v7_ayer = None
        for v in velas[1:]:
            dt_v = datetime.strptime(v["datetime"], "%Y-%m-%d %H:%M:%S")
            if dt_v.strftime("%Y-%m-%d") != fecha_hoy and dt_v.hour == 15 and dt_v.minute == 30:
                v7_ayer = float(v["close"])
                break
        reset_diario(fecha_hoy, v7_ayer)

    v7_ayer = estado_dia["v7_ayer_close"]

    # ── VELA 1 — 10:00 AM EST (timestamp TV 9:30) ────────
    if hora == 10:
        estado_dia["v1_open"]  = vela_actual["open"]
        estado_dia["v1_close"] = vela_actual["close"]
        v1_verde = vela_actual["close"] > vela_actual["open"]
        v1_roja  = vela_actual["close"] < vela_actual["open"]

        # 1VR
        if VR1_ON and v1_roja and not estado_dia["vr1_fired"]:
            estado_dia["vr1_fired"] = True
            techo = calcular_techo()
            piso, mitad = calcular_piso_mitad()
            msg = (
                f"🔴 <b>1VR — PRIMERA VELA ROJA</b>\n"
                f"<b>Open:</b> ${vela_actual['open']:.2f}\n"
                f"<b>Cierre:</b> ${vela_actual['close']:.2f}\n"
                f"⚠️ <b>PUT — Evaluar entrada</b>"
            )
            if techo:
                msg += f"\n<b>Techo canal:</b> ${techo:.2f}"
            enviar_telegram(msg)

        # RPG — gap + V1 verde
        if RPG_ON and v7_ayer and v1_verde and not estado_dia["rpg_fired"]:
            gap_alza = (vela_actual["open"] - v7_ayer) / v7_ayer * 100
            gap_baja = (v7_ayer - vela_actual["open"]) / v7_ayer * 100
            if gap_alza >= 0.5 or gap_baja >= 0.5:
                estado_dia["rpg_piso"]   = vela_actual["low"]
                estado_dia["rpg_activo"] = True
                print(f"RPG activado — piso: ${vela_actual['low']:.2f}")

        # GNA — gap alcista + tendencia alza + V1 verde
        if GNA_ON and v7_ayer and v1_verde and tendencia_alza and not estado_dia["gna_fired"]:
            gap_alza = (vela_actual["open"] - v7_ayer) / v7_ayer * 100
            if gap_alza >= 0.1:
                estado_dia["gna_activo"] = True
                print(f"GNA activado — techo V1: ${vela_actual['close']:.2f}")

        # GBA — gap bajista + V1 verde
        if GBA_ON and v7_ayer and v1_verde and not estado_dia["gba_fired"]:
            gap_baja = (v7_ayer - vela_actual["open"]) / v7_ayer * 100
            if gap_baja >= 0.1:
                estado_dia["gba_activo"] = True
                print(f"GBA activado — techo V1: ${vela_actual['close']:.2f}")

        return

    # ── VELAS 2-7 — evaluar estrategias ──────────────────
    v1_close = estado_dia["v1_close"]
    v1_open  = estado_dia["v1_open"]

    # Vela alcista estricta AXIS
    cuerpo    = vela_actual["close"] - vela_actual["open"]
    mecha_sup = vela_actual["high"] - max(vela_actual["close"], vela_actual["open"])
    rango     = vela_actual["high"] - vela_actual["low"]
    v_alcista = (
        vela_actual["close"] > vela_actual["open"] and
        (cuerpo / rango >= 0.15 if rango > 0 else False) and
        (mecha_sup / cuerpo <= 0.30 if cuerpo > 0 else False)
    )
    v_roja = vela_actual["close"] < vela_actual["open"]

    # RPG — vela roja cierra bajo piso
    if RPG_ON and estado_dia["rpg_activo"] and not estado_dia["rpg_fired"]:
        piso_rpg = estado_dia["rpg_piso"]
        if v_roja and piso_rpg and vela_actual["close"] < piso_rpg:
            estado_dia["rpg_fired"]  = True
            estado_dia["rpg_activo"] = False
            enviar_telegram(
                f"🟣 <b>RPG — RUPTURA PISO GAP</b>\n"
                f"<b>Hora:</b> {hora}:00 EST\n"
                f"<b>Piso V1:</b> ${piso_rpg:.2f}\n"
                f"<b>Cierre:</b> ${vela_actual['close']:.2f}\n"
                f"⚠️ <b>PUT — Evaluar entrada</b>"
            )

    # GNA — vela alcista cierra sobre cierre V1
    if GNA_ON and estado_dia["gna_activo"] and not estado_dia["gna_fired"] and v1_close:
        if v_alcista and vela_actual["close"] > v1_close:
            estado_dia["gna_fired"]  = True
            estado_dia["gna_activo"] = False
            tipo = "GNA" if hora == 11 else "GNA+2"
            enviar_telegram(
                f"🟢 <b>{tipo} — GAP NORMAL ALZA</b>\n"
                f"<b>Hora:</b> {hora}:00 EST\n"
                f"<b>Techo V1:</b> ${v1_close:.2f}\n"
                f"<b>Cierre:</b> ${vela_actual['close']:.2f}\n"
                f"📈 <b>CALL — Evaluar entrada</b>"
            )

    # GBA — vela alcista cierra sobre cierre V1
    if GBA_ON and estado_dia["gba_activo"] and not estado_dia["gba_fired"] and v1_close:
        if v_alcista and vela_actual["close"] > v1_close:
            estado_dia["gba_fired"]  = True
            estado_dia["gba_activo"] = False
            tipo = "GBA" if hora == 11 else "GBA+2"
            enviar_telegram(
                f"🔵 <b>{tipo} — GAP BAJISTA ALZA</b>\n"
                f"<b>Hora:</b> {hora}:00 EST\n"
                f"<b>Techo V1:</b> ${v1_close:.2f}\n"
                f"<b>Cierre:</b> ${vela_actual['close']:.2f}\n"
                f"📈 <b>CALL — Evaluar entrada</b>"
            )

    # RCB/CNF — canal activo
    if CANAL_ON and CANAL_ACTIVO:
        techo = calcular_techo()
        piso, mitad = calcular_piso_mitad()
        if techo and vela_actual["close"] > techo and v_alcista:
            tipo_canal = "RCB" if PISO else "CNF"
            enviar_telegram(
                f"🟠 <b>{tipo_canal} — RUPTURA CANAL</b>\n"
                f"<b>Hora:</b> {hora}:00 EST\n"
                f"<b>Techo:</b> ${techo:.2f}\n"
                f"<b>Cierre:</b> ${vela_actual['close']:.2f}\n"
                f"📈 <b>CALL — Evaluar entrada</b>"
            )

    print(f"Vela {hora}:00 — Close: ${vela_actual['close']:.2f} | RPG: {estado_dia['rpg_activo']} | GNA: {estado_dia['gna_activo']} | GBA: {estado_dia['gba_activo']}")

# ═══════════════════════════════════════════════════════════
# LOOP
# ═══════════════════════════════════════════════════════════
def monitor_loop():
    print("Breakout Sentinel v7.0 iniciado...")
    while True:
        ahora = datetime.now(EST)
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
def home():
    ahora = datetime.now(EST)
    return jsonify({
        "sistema":    "Breakout Sentinel v7.0",
        "estado":     "activo" if SISTEMA_ACTIVO else "apagado",
        "hora_est":   ahora.strftime("%A %H:%M EST"),
        "mercado":    "abierto" if es_dia_mercado(ahora) else "cerrado",
        "estrategias": {"1VR": VR1_ON, "RPG": RPG_ON, "GNA": GNA_ON, "GBA": GBA_ON, "CANAL": CANAL_ON},
        "estado_dia": estado_dia,
    }), 200

@app.route("/test", methods=["GET"])
def test():
    ahora = datetime.now(EST)
    enviar_telegram(
        f"✅ <b>Breakout Sentinel v7.0</b>\n"
        f"<b>Hora:</b> {ahora.strftime('%A %d/%m/%Y %H:%M EST')}\n"
        f"<b>Mercado:</b> {'Abierto' if es_dia_mercado(ahora) else 'Cerrado'}\n"
        f"<b>1VR:</b> {'ON' if VR1_ON else 'OFF'} | "
        f"<b>RPG:</b> {'ON' if RPG_ON else 'OFF'} | "
        f"<b>GNA:</b> {'ON' if GNA_ON else 'OFF'} | "
        f"<b>GBA:</b> {'ON' if GBA_ON else 'OFF'}\n"
        f"<b>Canal:</b> {'Activo' if CANAL_ACTIVO else 'Sin activar'}"
    )
    return jsonify({"status": "ok"}), 200

@app.route("/reporte", methods=["GET"])
def reporte_manual():
    reporte_horario()
    return jsonify({"status": "reporte enviado"}), 200

@app.route("/activar", methods=["GET"])
def activar():
    global P1, P2, PISO, CANAL_ACTIVO, CANAL_ON
    try:
        P1 = {"fecha": request.args["p1_fecha"], "hora_est": int(request.args["p1_hora"]), "high": float(request.args["p1_high"])}
        P2 = {"fecha": request.args["p2_fecha"], "hora_est": int(request.args["p2_hora"]), "high": float(request.args["p2_high"])}
        vela_map = {1:10, 2:11, 3:12, 4:13, 5:14, 6:15, 7:16}
        piso_vela = int(request.args.get("piso_vela", 0))
        if piso_vela > 0 and "piso_low" in request.args:
            PISO = {"fecha": request.args["piso_fecha"], "hora_est": vela_map[piso_vela], "low": float(request.args["piso_low"])}
        CANAL_ACTIVO = True
        CANAL_ON     = True
        techo = calcular_techo()
        piso, mitad = calcular_piso_mitad()
        enviar_telegram(
            f"✅ <b>Canal Activado</b>\n"
            f"<b>P1:</b> ${P1['high']:.2f} — {P1['fecha']}\n"
            f"<b>P2:</b> ${P2['high']:.2f} — {P2['fecha']}\n"
            + (f"<b>Piso:</b> ${PISO['low']:.2f} — {PISO['fecha']}\n" if PISO else "<b>Tipo:</b> CNF — sin piso\n") +
            (f"<b>Techo ahora:</b> ${techo:.2f}\n<b>Mitad:</b> ${mitad:.2f}\n<b>Piso ahora:</b> ${piso:.2f}" if techo and piso else "")
        )
        return jsonify({"status": "canal activado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/apagar", methods=["GET"])
def apagar():
    global SISTEMA_ACTIVO
    SISTEMA_ACTIVO = False
    enviar_telegram("🏁 <b>Sistema apagado manualmente.</b>")
    return jsonify({"status": "apagado"}), 200

@app.route("/estrategia", methods=["GET"])
def estrategia():
    global VR1_ON, RPG_ON, GNA_ON, GBA_ON, CANAL_ON
    if "vr1" in request.args: VR1_ON  = request.args["vr1"].lower()  == "true"
    if "rpg" in request.args: RPG_ON  = request.args["rpg"].lower()  == "true"
    if "gna" in request.args: GNA_ON  = request.args["gna"].lower()  == "true"
    if "gba" in request.args: GBA_ON  = request.args["gba"].lower()  == "true"
    if "canal" in request.args: CANAL_ON = request.args["canal"].lower() == "true"
    enviar_telegram(
        f"⚙️ <b>Estrategias</b>\n"
        f"1VR: {'ON' if VR1_ON else 'OFF'} | RPG: {'ON' if RPG_ON else 'OFF'}\n"
        f"GNA: {'ON' if GNA_ON else 'OFF'} | GBA: {'ON' if GBA_ON else 'OFF'}\n"
        f"Canal: {'ON' if CANAL_ON else 'OFF'}"
    )
    return jsonify({"VR1": VR1_ON, "RPG": RPG_ON, "GNA": GNA_ON, "GBA": GBA_ON, "CANAL": CANAL_ON}), 200

# ═══════════════════════════════════════════════════════════
# ARRANQUE
# ═══════════════════════════════════════════════════════════
def arrancar_monitor():
    time.sleep(5)
    threading.Thread(target=monitor_loop, daemon=True).start()

threading.Thread(target=arrancar_monitor, daemon=True).start()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
