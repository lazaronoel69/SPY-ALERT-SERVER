#!/usr/bin/env python3
"""
AXIS Breakout Sentinel v8.3
Estrategias: 1VR | 1VR+ | RPG | GNA | GBA | RCB/CNF
Multi-activo: SPY, AAPL, BA, GLD
Auto-P2 | Apagado automatico si nuevo P2 >= P1
Fix v8.2: 1VR envia alerta durante reconstruccion antes de marcar vr1_fired
v8.3: 1VR+ — si V1 roja cae dentro de canal RCB entre techo y media, alerta dice 1VR+
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

ACTIVOS          = ["SPY", "AAPL", "BA", "GLD"]
HORAS_REPORTE    = [10, 11, 12, 13, 14, 15, 16]
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
        "gna_activo":    False,
        "gna_fired":     False,
        "gba_activo":    False,
        "gba_fired":     False,
        "vr1_fired":     False,
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
# TWELVE DATA
# ═══════════════════════════════════════════════════════════
def get_velas(simbolo, outputsize=50):
    try:
        params = {
            "symbol":     simbolo,
            "interval":   "1h",
            "outputsize": outputsize,
            "timezone":   "America/New_York",
            "apikey":     TWELVEDATA_KEY,
        }
        r = requests.get("https://api.twelvedata.com/time_series", params=params, timeout=15)
        data = r.json()
        if data.get("status") == "error" or "values" not in data:
            print(f"TwelveData error {simbolo}: {data.get('message', data)}")
            return None
        return data["values"]
    except Exception as e:
        print(f"Error TwelveData {simbolo}: {e}")
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
    if not c["on"] or c["apagado"] or not c["p1"] or not c["p2_actual_high"] or not c["p2_actual_ts"]:
        return None
    try:
        dt_p1 = ts_a_datetime(c["p1"]["fecha"], c["p1"]["hora_est"])
        dt_p2 = c["p2_actual_ts"]
        horas_p1_p2 = (dt_p2 - dt_p1).total_seconds() / 3600
        if horas_p1_p2 <= 0:
            return None
        slope = (c["p2_actual_high"] - c["p1"]["high"]) / horas_p1_p2
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
    estado_dia[simbolo] = {
        "fecha":         fecha_hoy,
        "v1_close":      None,
        "v1_open":       None,
        "v1_low":        None,
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

                # ── v8.3: 1VR / 1VR+ — enviar ANTES de marcar fired, sin retroactivos ──
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
                        enviar_telegram(
                            f"🔴 <b>{label} — PRIMERA VELA ROJA</b>\n"
                            f"<b>Activo:</b> {simbolo}\n"
                            f"<b>Hora:</b> 10:00 EST\n"
                            f"<b>Open:</b> ${v1_open_r:.2f} | <b>Close:</b> ${v1_close_r:.2f}\n"
                            f"{extra}"
                            f"⚠️ <b>PUT — Evaluar entrada</b>"
                        )
                    ed["vr1_fired"] = True

                # Reconstruir RPG
                if RPG_ON and v7_c and v1_close_r > v1_open_r:
                    gap = abs(v1_open_r - v7_c) / v7_c * 100
                    if gap >= 0.5:
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
        (mecha_sup / cuerpo <= 0.30 if cuerpo > 0 else False)
    )
    v_roja    = v_close < v_open
    v7_ayer   = ed["v7_ayer_close"]
    hora_vela = hora - 1

    # ── VELA 1 ──
    if hora_vela == 9:
        ed["v1_close"] = v_close
        ed["v1_open"]  = v_open
        ed["v1_low"]   = v_low

        # ── v8.3: 1VR / 1VR+ — tiempo real ──
        if VR1_ON and v_roja and not ed["vr1_fired"]:
            ahora_dt_vr = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))
            techo_vr = calcular_techo_canal(simbolo, ahora_dt_vr)
            _, mitad_vr = calcular_piso_mitad_canal(simbolo, ahora_dt_vr)
            c_vr = canal[simbolo]
            en_canal_rcb_vr = (
                c_vr["on"] and not c_vr["apagado"] and c_vr["p3"] is not None
                and techo_vr is not None and mitad_vr is not None
                and mitad_vr <= v_close <= techo_vr
            )
            label_vr = "1VR+" if en_canal_rcb_vr else "1VR"
            extra_vr = f"<b>Canal RCB:</b> Techo ${techo_vr:.2f} | Mitad ${mitad_vr:.2f}\n" if en_canal_rcb_vr else ""
            ed["vr1_fired"] = True
            enviar_telegram(
                f"🔴 <b>{label_vr} — PRIMERA VELA ROJA</b>\n"
                f"<b>Activo:</b> {simbolo}\n"
                f"<b>Hora:</b> 10:00 EST\n"
                f"<b>Open:</b> ${v_open:.2f} | <b>Close:</b> ${v_close:.2f}\n"
                f"{extra_vr}"
                f"⚠️ <b>PUT — Evaluar entrada</b>"
            )

        # RPG
        if RPG_ON and v7_ayer and v_close > v_open and not ed["rpg_fired"]:
            gap = abs(v_open - v7_ayer) / v7_ayer * 100
            if gap >= 0.5:
                ed["rpg_activo"] = True
                ed["rpg_piso"]   = v_low
                print(f"{simbolo} RPG activado — piso: ${v_low:.2f}")

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

        return

    # ── VELAS 2-7 ──
    v1_close = ed["v1_close"]

    # RPG
    if RPG_ON and ed["rpg_activo"] and not ed["rpg_fired"] and ed["rpg_piso"]:
        if v_roja and v_close < ed["rpg_piso"]:
            ed["rpg_fired"]  = True
            ed["rpg_activo"] = False
            enviar_telegram(
                f"🟣 <b>RPG — RUPTURA PISO GAP</b>\n"
                f"<b>Activo:</b> {simbolo}\n"
                f"<b>Hora:</b> {hora_vela+1}:00 EST\n"
                f"<b>Piso V1:</b> ${ed['rpg_piso']:.2f}\n"
                f"<b>Cierre:</b> ${v_close:.2f}\n"
                f"⚠️ <b>PUT — Evaluar entrada</b>"
            )

    # GNA
    if GNA_ON and ed["gna_activo"] and not ed["gna_fired"] and v1_close:
        if v_alcista and v_close > v1_close:
            ed["gna_fired"]  = True
            ed["gna_activo"] = False
            tipo = "GNA" if hora_vela == 10 else "GNA+2"
            enviar_telegram(
                f"🟢 <b>{tipo} — GAP NORMAL ALZA</b>\n"
                f"<b>Activo:</b> {simbolo}\n"
                f"<b>Hora:</b> {hora_vela+1}:00 EST\n"
                f"<b>Techo V1:</b> ${v1_close:.2f}\n"
                f"<b>Cierre:</b> ${v_close:.2f}\n"
                f"📈 <b>CALL — Evaluar entrada</b>"
            )

    # GBA
    if GBA_ON and ed["gba_activo"] and not ed["gba_fired"] and v1_close:
        if v_alcista and v_close > v1_close:
            ed["gba_fired"]  = True
            ed["gba_activo"] = False
            tipo = "GBA" if hora_vela == 10 else "GBA+2"
            enviar_telegram(
                f"🔵 <b>{tipo} — GAP BAJISTA ALZA</b>\n"
                f"<b>Activo:</b> {simbolo}\n"
                f"<b>Hora:</b> {hora_vela+1}:00 EST\n"
                f"<b>Techo V1:</b> ${v1_close:.2f}\n"
                f"<b>Cierre:</b> ${v_close:.2f}\n"
                f"📈 <b>CALL — Evaluar entrada</b>"
            )

    # RCB/CNF
    if c["on"] and not c["apagado"]:
        ahora_dt = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))
        techo = calcular_techo_canal(simbolo, ahora_dt)

        if techo:
            sobre_techo = v_close > techo

            if hora_vela == 10:
                if c["v1_candidato"]:
                    nuevo_p2_high = max(c["v1_candidato"], v_high) if (v_alcista and sobre_techo) else c["v1_candidato"]
                    if nuevo_p2_high < c["p1"]["high"]:
                        c["p2_actual_high"] = nuevo_p2_high
                        c["p2_actual_ts"]   = ahora_dt
                        tipo_canal = "RCB" if c["p3"] else "CNF"
                        enviar_telegram(
                            f"🟠 <b>{tipo_canal} — RUPTURA CANAL</b>\n"
                            f"<b>Activo:</b> {simbolo}\n"
                            f"<b>Hora:</b> {hora_vela+1}:00 EST\n"
                            f"<b>Techo:</b> ${techo:.2f}\n"
                            f"<b>Cierre:</b> ${v_close:.2f}\n"
                            f"<b>Nuevo P2:</b> ${nuevo_p2_high:.2f}\n"
                            f"📈 <b>CALL — Evaluar entrada</b>"
                        )
                    else:
                        c["apagado"] = True
                        enviar_telegram(
                            f"🔕 <b>Canal APAGADO — {simbolo}</b>\n"
                            f"Nuevo P2 ${nuevo_p2_high:.2f} >= P1 ${c['p1']['high']:.2f}"
                        )
                    c["v1_candidato"] = None

                elif v_alcista and sobre_techo:
                    if v_high < c["p1"]["high"]:
                        c["p2_actual_high"] = v_high
                        c["p2_actual_ts"]   = ahora_dt
                        tipo_canal = "RCB" if c["p3"] else "CNF"
                        enviar_telegram(
                            f"🟠 <b>{tipo_canal} — RUPTURA CANAL</b>\n"
                            f"<b>Activo:</b> {simbolo}\n"
                            f"<b>Hora:</b> {hora_vela+1}:00 EST\n"
                            f"<b>Techo:</b> ${techo:.2f}\n"
                            f"<b>Cierre:</b> ${v_close:.2f}\n"
                            f"<b>Nuevo P2:</b> ${v_high:.2f}\n"
                            f"📈 <b>CALL — Evaluar entrada</b>"
                        )
                    else:
                        c["apagado"] = True
                        enviar_telegram(
                            f"🔕 <b>Canal APAGADO — {simbolo}</b>\n"
                            f"Nuevo P2 ${v_high:.2f} >= P1 ${c['p1']['high']:.2f}"
                        )

            elif hora_vela > 10:
                if v_alcista and sobre_techo:
                    c["v1_candidato"] = v_high
                    print(f"{simbolo} Canal V{hora_vela-8} candidato: ${v_high:.2f}")

    print(f"{simbolo} V{hora_vela-8} {hora_vela+1}:00 — O:{v_open:.2f} C:{v_close:.2f} | RPG:{ed['rpg_activo']} GNA:{ed['gna_activo']} GBA:{ed['gba_activo']}")

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
                print(f"Datos: TwelveData ✅")
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
    print("AXIS Breakout Sentinel v8.3 iniciado...")
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
    canales = {}
    for a in ACTIVOS:
        c = canal[a]
        canales[a] = {
            "on":      c["on"],
            "apagado": c["apagado"],
            "p1":      c["p1"]["high"] if c["p1"] else None,
            "p2":      c["p2_actual_high"],
            "tipo":    "RCB" if c["p3"] else "CNF" if c["on"] else "OFF",
        }
    return jsonify({
        "sistema":     "AXIS Breakout Sentinel v8.3",
        "estado":      "activo" if SISTEMA_ACTIVO else "apagado",
        "hora_est":    ahora.strftime("%A %H:%M EST"),
        "mercado":     "abierto" if es_dia_mercado(ahora) else "cerrado",
        "estrategias": {"1VR": VR1_ON, "RPG": RPG_ON, "GNA": GNA_ON, "GBA": GBA_ON},
        "canales":     canales,
        "estado_dia":  {a: estado_dia[a] for a in ACTIVOS},
    }), 200

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
        f"✅ <b>AXIS Breakout Sentinel v8.3</b>\n"
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
