#!/usr/bin/env python3
"""
Breakout Sentinel v6.7
- Fuente de datos: Twelve Data (principal) + Finnhub (backup)
- BS reportes a las :01 de cada hora: 10,11,12,13,14,15,16 EST
- RPG reportes a las :02 de cada hora: 10,11,12,13,14,15,16 EST
- Solo Lunes a Viernes (mercado abierto)
- Techo, piso y mitad BS calculados dinamicamente hora a hora
- P2 se actualiza automaticamente si el high supera el techo
- Ruptura alcista BS: cierre > techo + vela verde + mecha <= 35%
- Canal invalidado: P2 >= P1 - sistema se apaga
- 1VR: alerta especial a las 10:01 si vela 1 roja en mitad superior
- RPG: gap cualquier direccion + vela 1 verde -> piso = low vela 1
        alerta puts si vela 2-7 cierra bajo el piso - una vez por dia
- Todos los reportes BS incluyen techo, mitad y piso
- Switches: BS, 1VR y RPG activables via /estrategia
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
# SWITCHES — activar/desactivar estrategias
# ═══════════════════════════════════════════════════════════
BS_ACTIVO  = True
VR1_ACTIVO = True
RPG_ACTIVO = True

# ═══════════════════════════════════════════════════════════
# ESTADO RPG — se resetea cada dia de mercado
# ═══════════════════════════════════════════════════════════
RPG_PISO_GAP   = None   # low de la vela 1 cuando hay gap + verde
RPG_VIGILANDO  = False  # True desde vela 1 hasta ruptura o fin del dia
RPG_DISPARADO  = False  # True cuando ya disparo la alerta hoy
RPG_DIA_ACTUAL = None   # fecha del dia actual para reset

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
# RPG — RESET DIARIO Y REPORTE
# ═══════════════════════════════════════════════════════════
def reset_rpg_si_nuevo_dia(ahora_est):
    """Resetea el estado RPG si es un nuevo dia de mercado."""
    global RPG_PISO_GAP, RPG_VIGILANDO, RPG_DISPARADO, RPG_DIA_ACTUAL
    dia_hoy = ahora_est.date()
    if RPG_DIA_ACTUAL != dia_hoy:
        RPG_PISO_GAP   = None
        RPG_VIGILANDO  = False
        RPG_DISPARADO  = False
        RPG_DIA_ACTUAL = dia_hoy
        print(f"RPG reseteado para nuevo dia: {dia_hoy}")

def reporte_rpg(hora, vela, fuente, ahora_est):
    """
    Reporte RPG a las :02 de cada hora.
    Hora 10:02 — evalua gap + vela 1 verde → fija piso del gap
    Horas 11:02 a 16:02 — verifica si cierre < piso del gap
    """
    global RPG_PISO_GAP, RPG_VIGILANDO, RPG_DISPARADO

    if not RPG_ACTIVO:
        return

    hora_label = f"{hora}:00 EST"
    vela_num   = hora - 9

    # ── Vela 1 — 10:02 AM ───────────────────────────────
    if hora == 10:
        # Necesitamos el close de ayer — lo obtenemos de la API
        # Usamos el open de la vela como referencia del gap
        # close_ayer = open de la vela 1 ajustado — usamos datos de la vela anterior
        vela_ayer, _ = get_ultima_vela()  # esto da la vela anterior a la actual
        if not vela_ayer:
            enviar_telegram(
                f"📊 <b>RPG — {hora_label} — Vela {vela_num}</b>\n"
                f"No se pudo obtener datos para calcular gap.\n"
                f"RPG en espera."
            )
            return

        # Gap = diferencia entre open de hoy y close de ayer
        close_ayer = vela_ayer["close"]
        open_hoy   = vela["open"]
        gap_pct    = abs(open_hoy - close_ayer) / close_ayer * 100
        hay_gap    = gap_pct > 0
        vela_verde = vela["close"] > vela["open"]
        direccion  = "arriba ↑" if open_hoy > close_ayer else "abajo ↓"

        if hay_gap and vela_verde:
            RPG_PISO_GAP  = round(vela["low"], 2)
            RPG_VIGILANDO = True
            RPG_DISPARADO = False
            enviar_telegram(
                f"📊 <b>RPG — Gap detectado — {hora_label}</b>\n\n"
                f"<b>Gap:</b> {gap_pct:.2f}% {direccion}\n"
                f"<b>Close ayer:</b> ${close_ayer:.2f}\n"
                f"<b>Open hoy:</b> ${open_hoy:.2f}\n"
                f"<b>Vela 1:</b> Verde ✅\n"
                f"<b>Piso del gap:</b> ${RPG_PISO_GAP:.2f}\n\n"
                f"👁 <b>RPG en vigilancia — Velas 2 a 7</b>"
            )
        else:
            razones = []
            if not hay_gap:    razones.append("sin gap")
            if not vela_verde: razones.append("vela 1 no es verde")
            enviar_telegram(
                f"📊 <b>RPG — {hora_label} — Sin activacion</b>\n\n"
                f"<b>Gap:</b> {gap_pct:.2f}% {direccion}\n"
                f"<b>Vela 1:</b> {'Verde' if vela_verde else 'Roja'}\n"
                f"<b>Razon:</b> {', '.join(razones)}\n\n"
                f"RPG en espera hasta manana."
            )
        return

    # ── Velas 2-7 — 11:02 a 16:02 ───────────────────────
    if not RPG_VIGILANDO or RPG_DISPARADO or RPG_PISO_GAP is None:
        return  # RPG no activo hoy — silencio

    cierre_bajo_piso = vela["close"] < RPG_PISO_GAP
    proxima = f"{hora + 1}:00 EST" if hora < 16 else "apertura manana"

    if cierre_bajo_piso:
        RPG_DISPARADO = True
        RPG_VIGILANDO = False
        enviar_telegram(
            f"🔴 <b>RPG — RUPTURA PISO GAP</b>\n"
            f"<b>Hora:</b> {hora_label} — Vela {vela_num}\n\n"
            f"<b>Piso del gap:</b> ${RPG_PISO_GAP:.2f}\n"
            f"<b>Cierre vela:</b> ${vela['close']:.2f}\n"
            f"<b>Fuente:</b> {fuente}\n\n"
            f"🎯 <b>EVALUAR ENTRADA PUTS</b>"
        )
    else:
        enviar_telegram(
            f"📊 <b>RPG — Piso intacto — {hora_label}</b>\n\n"
            f"<b>Piso del gap:</b> ${RPG_PISO_GAP:.2f}\n"
            f"<b>Cierre vela:</b> ${vela['close']:.2f}\n"
            f"<b>Diferencia:</b> +${vela['close'] - RPG_PISO_GAP:.2f}\n\n"
            f"RPG vigilando — proxima: {proxima}"
        )

# ═══════════════════════════════════════════════════════════
# REPORTE HORARIO BS
# ═══════════════════════════════════════════════════════════
def reporte_bs():
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

    # Reset RPG si es nuevo dia
    reset_rpg_si_nuevo_dia(ahora_est)

    # Techo, piso y mitad al cierre exacto de la vela
    cierre_vela = ahora_est.replace(minute=0, second=0, microsecond=0)
    techo = calcular_techo(cierre_vela)
    piso_bs, mitad_bs, _ = calcular_piso_y_mitad(cierre_vela)

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
        enviar_telegram(
            f"🟢 <b>BREAKOUT SENTINEL — RUPTURA ALCISTA</b>\n"
            f"<b>Hora:</b> {hora_label} — Vela {vela_num}{nota_vela}\n\n"
            f"<b>Techo:</b> ${techo:.2f}\n"
            f"<b>Mitad:</b> ${mitad_bs:.2f}\n"
            f"<b>Piso BS:</b> ${piso_bs:.2f}\n"
            f"<b>Cierre:</b> ${vela['close']:.2f}\n"
            f"<b>High:</b> ${vela['high']:.2f}\n"
            f"<b>Mecha sup:</b> {mecha_pct:.0f}%\n"
            f"<b>Fuente:</b> {fuente}"
            f"{nota_p2}\n\n"
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
            f"<b>Mitad:</b> ${mitad_bs:.2f}\n"
            f"<b>Piso BS:</b> ${piso_bs:.2f}\n"
            f"<b>Cierre:</b> ${vela['close']:.2f}\n"
            f"<b>High:</b> ${vela['high']:.2f}\n"
            f"<b>Razon:</b> {', '.join(razon)}\n"
            f"<b>Fuente:</b> {fuente}"
            f"{nota_p2}\n\n"
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
            f"<b>Mitad:</b> ${mitad_bs:.2f}\n"
            f"<b>Piso BS:</b> ${piso_bs:.2f}\n"
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
    print("Breakout Sentinel v6.7 iniciado...")
    while True:
        ahora = datetime.now(EST)
        minuto_actual = ahora.minute

        # Calcular segundos hasta el proximo :01
        if minuto_actual < 1:
            segundos_espera = (1 - minuto_actual) * 60 - ahora.second
        else:
            segundos_espera = (61 - minuto_actual) * 60 - ahora.second

        print(f"Proximo chequeo en {segundos_espera//60}m {segundos_espera%60}s | {ahora.strftime('%A %H:%M EST')}")
        time.sleep(segundos_espera)

        ahora = datetime.now(EST)
        if es_dia_mercado(ahora) and es_hora_reporte(ahora.hour):
            # :01 — BS y 1VR
            if ahora.minute == 1:
                reporte_bs()
                # Esperar 60 segundos para el :02 RPG
                time.sleep(60)
                ahora2 = datetime.now(EST)
                if es_dia_mercado(ahora2) and es_hora_reporte(ahora2.hour):
                    vela, fuente = get_ultima_vela()
                    if vela:
                        reporte_rpg(ahora2.hour, vela, fuente, ahora2)
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
        "sistema":    "Breakout Sentinel v6.7",
        "estado":     "activo" if SISTEMA_ACTIVO else "apagado",
        "hora_est":   ahora.strftime("%A %H:%M EST"),
        "mercado":    "abierto" if es_dia_mercado(ahora) else "cerrado (fin de semana)",
        "estrategias": {"BS": BS_ACTIVO, "1VR": VR1_ACTIVO, "RPG": RPG_ACTIVO},
        "P1":         P1,
        "P2":         P2,
        "techo_actual": techo,
        "mitad_canal":  mitad,
        "piso_actual":  piso,
        "rpg_vigilando": RPG_VIGILANDO,
        "rpg_piso_gap":  RPG_PISO_GAP,
    }), 200

@app.route("/test", methods=["GET"])
def test():
    ahora = datetime.now(EST)
    cierre_vela = ahora.replace(minute=0, second=0, microsecond=0)
    techo = calcular_techo(cierre_vela)
    piso, mitad, distancia = calcular_piso_y_mitad(cierre_vela)
    enviar_telegram(
        f"✅ <b>Breakout Sentinel v6.7</b>\n"
        f"Estado: {'Activo' if SISTEMA_ACTIVO else 'Apagado'}\n"
        f"Hora: {ahora.strftime('%A %d/%m/%Y %H:%M EST')}\n"
        f"Mercado: {'Abierto' if es_dia_mercado(ahora) else 'Cerrado (fin de semana)'}\n\n"
        f"<b>Estrategias:</b> BS={'ON' if BS_ACTIVO else 'OFF'} | 1VR={'ON' if VR1_ACTIVO else 'OFF'} | RPG={'ON' if RPG_ACTIVO else 'OFF'}\n\n"
        f"<b>P1:</b> ${P1['high']:.2f} ({P1['fecha']})\n"
        f"<b>P2:</b> ${P2['high']:.2f} ({P2['fecha']})\n"
        f"<b>Techo ahora:</b> ${techo:.2f}\n"
        f"<b>Mitad canal:</b> ${mitad:.2f}\n"
        f"<b>Piso BS:</b> ${piso:.2f}\n\n"
        f"<b>RPG vigilando:</b> {'Si — piso gap $' + str(RPG_PISO_GAP) if RPG_VIGILANDO else 'No'}"
    )
    return jsonify({"status": "ok"}), 200

@app.route("/reporte", methods=["GET"])
def reporte_manual():
    reporte_bs()
    return jsonify({"status": "reporte BS enviado"}), 200

@app.route("/estrategia", methods=["GET"])
def cambiar_estrategia():
    """Activa o desactiva estrategias individualmente.
    Uso: /estrategia?bs=true&1vr=false&rpg=true
    """
    global BS_ACTIVO, VR1_ACTIVO, RPG_ACTIVO
    try:
        if "bs" in request.args:
            BS_ACTIVO = request.args["bs"].lower() == "true"
        if "1vr" in request.args:
            VR1_ACTIVO = request.args["1vr"].lower() == "true"
        if "rpg" in request.args:
            RPG_ACTIVO = request.args["rpg"].lower() == "true"
        enviar_telegram(
            f"⚙️ <b>Estrategias actualizadas</b>\n\n"
            f"<b>BS:</b> {'ON ✅' if BS_ACTIVO else 'OFF ❌'}\n"
            f"<b>1VR:</b> {'ON ✅' if VR1_ACTIVO else 'OFF ❌'}\n"
            f"<b>RPG:</b> {'ON ✅' if RPG_ACTIVO else 'OFF ❌'}"
        )
        return jsonify({"BS": BS_ACTIVO, "1VR": VR1_ACTIVO, "RPG": RPG_ACTIVO}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

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
