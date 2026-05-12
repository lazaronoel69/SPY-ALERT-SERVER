#!/usr/bin/env python3
"""
AXIS Breakout Sentinel v8.18
Estrategias: 1VR | 1VR+ | RPG | GNA | GBA | RCB/CNF
Multi-activo: SPY, AAPL, BA, GLD
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

# Ordenes pendientes de confirmacion — clave: callback_query_id
ordenes_pendientes = {}

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
# ═══════════════════════════════════════════════════════════
# GET_VELAS — Tradier produccion 15min → velas AXIS
# Reemplaza TwelveData completamente desde v8.17
# V1 = 9:30+9:45 | V2-V7 = 4 barras de 15min cada una
# Retorna lista de dicts con keys: datetime, open, high, low, close
# en el mismo formato que usaba TwelveData para compatibilidad
# ═══════════════════════════════════════════════════════════
def get_velas(simbolo, outputsize=50):
    try:
        from datetime import date, datetime as dt2
        from collections import defaultdict

        # Calcular fecha inicio con dias habiles reales (sin numpy)
        def restar_dias_habiles(fecha, dias):
            actual = fecha
            contados = 0
            while contados < dias:
                actual -= timedelta(days=1)
                if actual.weekday() < 5:  # lunes=0 a viernes=4
                    contados += 1
            return actual

        fecha_fin = date.today()
        fecha_ini = restar_dias_habiles(fecha_fin, 90)
        fecha_mid = restar_dias_habiles(fecha_fin, 45)

        todas_barras = []

        for (f_ini, f_fin) in [
            (fecha_ini.strftime("%Y-%m-%d"), fecha_mid.strftime("%Y-%m-%d")),
            (fecha_mid.strftime("%Y-%m-%d"), fecha_fin.strftime("%Y-%m-%d")),
        ]:
            r = requests.get(
                f"{TRADIER_BASE_REAL}/markets/timesales",
                headers=TRADIER_HEADERS_REAL,
                params={
                    "symbol":         simbolo,
                    "interval":       "15min",
                    "start":          f"{f_ini} 09:00",
                    "end":            f"{f_fin} 16:30",
                    "session_filter": "open",
                },
                timeout=30
            )
            if r.status_code != 200:
                print(f"Tradier error {simbolo} {f_ini}-{f_fin}: HTTP {r.status_code}")
                continue
            data   = r.json()
            series = data.get("series")
            if not series or series == "null":
                continue
            barras = series.get("data", [])
            if isinstance(barras, dict):
                barras = [barras]
            todas_barras.extend(barras)

        if not todas_barras:
            print(f"Tradier sin datos {simbolo}")
            return None

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
            enviar_senal_con_botones(
                simbolo, f"{label_vr} — PRIMERA VELA ROJA",
                "10:00 EST", v_close, "PUT",
                f"<b>Open:</b> ${v_open:.2f} | <b>Close:</b> ${v_close:.2f}\n{extra_vr}"
            )

        # RPG
        if RPG_ON and v7_ayer and v_close > v_open and not ed["rpg_fired"]:
            gap = abs(v_open - v7_ayer) / v7_ayer * 100
            if gap >= 0.2:
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
            enviar_senal_con_botones(
                simbolo, "RPG — RUPTURA PISO GAP",
                f"{hora_vela+1}:00 EST", v_close, "PUT",
                f"<b>Piso V1:</b> ${ed['rpg_piso']:.2f} | <b>Cierre:</b> ${v_close:.2f}\n"
            )

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
def get_opcion_tradier(simbolo, tipo, precio_actual):
    """
    tipo: 'call' o 'put'
    Busca el contrato con strike precio+-3, vencimiento minimo 4 dias
    """
    try:
        from datetime import date, timedelta
        hoy = date.today()
        # Buscar vencimientos disponibles
        r = requests.get(
            f"{TRADIER_BASE}/markets/options/expirations",
            headers=TRADIER_HEADERS,
            params={"symbol": simbolo, "includeAllRoots": "true"},
            timeout=10
        )
        data = r.json()
        fechas = data.get("expirations", {}).get("date", [])
        if isinstance(fechas, str):
            fechas = [fechas]

        # Primer vencimiento con al menos 4 dias calendario
        vencimiento = None
        for f in sorted(fechas):
            fd = date.fromisoformat(f)
            if (fd - hoy).days >= 4:
                vencimiento = f
                break

        if not vencimiento:
            print(f"Sin vencimiento disponible para {simbolo}")
            return None

        # Strike objetivo
        strike_obj = precio_actual + 3 if tipo == 'call' else precio_actual - 3
        strike_obj = round(strike_obj)

        # Buscar cadena de opciones
        r2 = requests.get(
            f"{TRADIER_BASE}/markets/options/chains",
            headers=TRADIER_HEADERS,
            params={"symbol": simbolo, "expiration": vencimiento, "greeks": "false"},
            timeout=10
        )
        data2 = r2.json()
        opciones = data2.get("options", {}).get("option", [])
        if not opciones:
            return None

        # Filtrar por tipo y buscar strike mas cercano
        filtradas = [o for o in opciones if o.get("option_type") == tipo]
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
        }
    except Exception as e:
        print(f"Error opcion Tradier {simbolo}: {e}")
        return None

# ═══════════════════════════════════════════════════════════
# TRADIER — EJECUTAR ORDEN
# ═══════════════════════════════════════════════════════════
def ejecutar_orden_tradier(opcion):
    try:
        payload = {
            "class":        "option",
            "symbol":       opcion["subyacente"],
            "option_symbol": opcion["symbol"],
            "side":         "buy_to_open",
            "quantity":     "1",
            "type":         "market",
            "duration":     "day",
        }
        r = requests.post(
            f"{TRADIER_BASE}/accounts/{TRADIER_ACCOUNT}/orders",
            headers=TRADIER_HEADERS,
            data=payload,
            timeout=10
        )
        data = r.json()
        orden_id = data.get("order", {}).get("id")
        status   = data.get("order", {}).get("status", "unknown")
        return {"ok": True, "id": orden_id, "status": status}
    except Exception as e:
        print(f"Error ejecutar orden Tradier: {e}")
        return {"ok": False, "error": str(e)}

# ═══════════════════════════════════════════════════════════
# TELEGRAM — ENVIAR MENSAJE CON BOTONES
# ═══════════════════════════════════════════════════════════
def enviar_telegram_botones(mensaje, orden_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       mensaje,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "✅ EJECUTAR", "callback_data": f"exec:{orden_id}"},
                {"text": "❌ IGNORAR",  "callback_data": f"skip:{orden_id}"},
            ]]
        }
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        print(f"Telegram botones: {r.status_code}")
    except Exception as e:
        print(f"Error Telegram botones: {e}")

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
        ordenes_pendientes[orden_id] = opcion
        msg = (
            f"{emoji} <b>{estrategia}</b>\n"
            f"<b>Activo:</b> {simbolo}\n"
            f"<b>Hora:</b> {hora_label}\n"
            f"<b>Precio:</b> ${precio:.2f}\n"
            f"{extra}"
            f"<b>Opcion:</b> {opcion['tipo']} ${opcion['strike']:.0f} exp {opcion['expiration']}\n"
            f"<b>Ask:</b> ${opcion['ask']:.2f} | <b>Bid:</b> ${opcion['bid']:.2f}\n"
            f"⚠️ <b>{tipo_opcion} — ¿Ejecutar?</b>"
        )
        enviar_telegram_botones(msg, orden_id)
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
    print("AXIS Breakout Sentinel v8.18 iniciado...")
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
        "sistema":     "AXIS Breakout Sentinel v8.18",
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
        f"✅ <b>AXIS Breakout Sentinel v8.18</b>\n"
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
        if len(partes) != 2:
            return jsonify({"ok": True}), 200

        accion, orden_id = partes[0], partes[1]

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

        if accion == "exec":
            opcion = ordenes_pendientes.pop(orden_id, None)
            if not opcion:
                editar_mensaje("⚠️ <b>Orden expirada o ya procesada.</b>")
                return jsonify({"ok": True}), 200

            resultado = ejecutar_orden_tradier(opcion)
            if resultado["ok"]:
                editar_mensaje(
                    f"✅ <b>ORDEN EJECUTADA</b>\n"
                    f"<b>Opcion:</b> {opcion['tipo']} ${opcion['strike']:.0f} exp {opcion['expiration']}\n"
                    f"<b>Cantidad:</b> 1 contrato\n"
                    f"<b>ID Orden:</b> {resultado['id']}\n"
                    f"<b>Status:</b> {resultado['status']}"
                )
                print(f"Orden ejecutada — ID: {resultado['id']} | {opcion}")
            else:
                editar_mensaje(
                    f"❌ <b>ERROR AL EJECUTAR</b>\n"
                    f"{resultado.get('error', 'Error desconocido')}"
                )
                print(f"Error ejecutando orden: {resultado}")

        elif accion == "skip":
            ordenes_pendientes.pop(orden_id, None)
            editar_mensaje("❌ <b>Orden ignorada.</b>")
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
ACTIVOS_V7_ANTICIPADA = ["AAPL", "BA", "GLD"]

def evaluar_v7_anticipada(simbolo):
    """Evalua V7 a las 3:58 EST para activos que cierran a las 4:00 EST."""
    ahora = datetime.now(EST)
    print(f"V7 anticipada {simbolo} — {ahora.strftime('%H:%M EST')}")
    try:
        velas = get_velas(simbolo, outputsize=50)
        if velas:
            evaluar_activo(simbolo, velas, ahora.replace(hour=16, minute=1))
        else:
            print(f"V7 anticipada {simbolo}: sin datos TwelveData")
    except Exception as e:
        print(f"Error V7 anticipada {simbolo}: {e}")

def corregir_cierre_v7(simbolo):
    """
    A las 4:00 EST lee el cierre real y corrige v7_close interno.
    Sin alerta — solo actualiza el estado para que el sistema
    tenga el dato correcto si lo necesita en sesiones futuras.
    """
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
                # Actualizar v7_ayer_close para que mañana lo use correctamente
                estado_dia[simbolo]["v7_ayer_close"] = cierre_real
                print(f"Correccion V7 {simbolo}: cierre real ${cierre_real:.2f} registrado")
                return
        print(f"Correccion V7 {simbolo}: vela 15h no encontrada aun")
    except Exception as e:
        print(f"Error correccion V7 {simbolo}: {e}")

def loop_v7_anticipada():
    """
    Thread independiente que vigila 3:58 y 4:00 EST
    solo en dias de mercado para AAPL, BA, GLD.
    """
    print("Thread V7 anticipada iniciado...")
    ejecutado_358 = set()   # activos evaluados a las 3:58 hoy
    ejecutado_400 = set()   # activos corregidos a las 4:00 hoy
    fecha_actual  = None

    while True:
        try:
            ahora      = datetime.now(EST)
            fecha_hoy  = ahora.strftime("%Y-%m-%d")

            # Reset diario
            if fecha_hoy != fecha_actual:
                fecha_actual  = fecha_hoy
                ejecutado_358 = set()
                ejecutado_400 = set()

            if es_dia_mercado(ahora):
                # 3:58 EST — evaluacion anticipada V7
                if ahora.hour == 15 and ahora.minute == 58:
                    for simbolo in ACTIVOS_V7_ANTICIPADA:
                        if simbolo not in ejecutado_358:
                            evaluar_v7_anticipada(simbolo)
                            ejecutado_358.add(simbolo)

                # 4:00 EST — correccion cierre real sin alerta
                if ahora.hour == 16 and ahora.minute == 0:
                    for simbolo in ACTIVOS_V7_ANTICIPADA:
                        if simbolo not in ejecutado_400:
                            corregir_cierre_v7(simbolo)
                            ejecutado_400.add(simbolo)

            time.sleep(30)   # chequea cada 30 segundos — liviano y preciso
        except Exception as e:
            print(f"Error loop V7 anticipada: {e}")
            time.sleep(30)

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
    dias    = int(request.args.get("dias", 90))
    outputsize = dias * 7  # ~7 velas AXIS por dia

    velas = get_velas(simbolo, outputsize=outputsize)
    if not velas:
        return jsonify({"error": f"Sin datos para {simbolo}"}), 500

    return jsonify({
        "simbolo": simbolo,
        "fuente":  "Tradier 15min",
        "total":   len(velas),
        "velas":   velas,
    }), 200

# ═══════════════════════════════════════════════════════════
# ARRANQUE
# ═══════════════════════════════════════════════════════════
def arrancar_monitor():
    time.sleep(5)
    threading.Thread(target=monitor_loop,        daemon=True).start()
    threading.Thread(target=loop_v7_anticipada,  daemon=True).start()

threading.Thread(target=arrancar_monitor, daemon=True).start()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
