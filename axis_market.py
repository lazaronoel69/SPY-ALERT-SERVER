#!/usr/bin/env python3
"""
AXIS Market Data — AX-010 Market Data Baseline
Funciones de construccion y actualizacion de velas locales (V1-V7),
extraidas de server.py sin cambiar la regla del :01, horarios de velas,
llamadas a Tradier, outputsize, ni formato JSON.

es_dia_mercado y restar_dias_habiles permanecen en server.py (se usan en
mucho mas que datos de mercado: canales, portfolio, etc). Para evitar un
import circular (axis_market necesitaria importar de server, y server
necesita importar de axis_market), las funciones que las requieren las
reciben como PARAMETRO en vez de importarlas. server.py las pasa al
llamar, sin cambiar su propio comportamiento ni firma publica hacia el
resto del codigo (los wrappers, si se necesitan, las inyectan).

cargar_velas_local y guardar_velas_local vienen de axis_storage.py (AX-005).
TRADIER_BASE_REAL y TRADIER_HEADERS_REAL vienen de axis_tradier.py si alli
existieran publicas; en este sprint se leen directo via os.environ igual
que el patron ya usado en axis_tradier.py (AX-004), para no depender de
variables internas de server.py.
"""

import os
import requests
from datetime import date, timedelta, datetime
from collections import defaultdict

from axis_config import ACTIVOS, EST
from axis_storage import cargar_velas_local, guardar_velas_local

TRADIER_TOKEN_REAL   = os.environ.get("TRADIER_TOKEN_REAL", "")
TRADIER_BASE_REAL    = "https://api.tradier.com/v1"
TRADIER_HEADERS_REAL = {
    "Authorization": f"Bearer {TRADIER_TOKEN_REAL}",
    "Accept":        "application/json",
}


def agregar_barra_diaria(simbolo, fecha_str=None):
    """Obtiene el OHLC diario OFICIAL directo de Tradier history (no lo
    construye desde barras 15min, para evitar discrepancias) y lo agrega
    a la base permanente si no existe ya."""
    if fecha_str is None:
        fecha_str = date.today().strftime("%Y-%m-%d")

    local = cargar_velas_local(simbolo)
    barras_daily = [b for b in local["barras"] if b.get("interval") == "daily"]
    fechas_existentes = {b["time"][:10] for b in barras_daily}
    if fecha_str in fechas_existentes:
        return False  # ya existe, no duplicar

    try:
        r = requests.get(
            f"{TRADIER_BASE_REAL}/markets/history",
            headers=TRADIER_HEADERS_REAL,
            params={"symbol": simbolo, "interval": "daily", "start": fecha_str, "end": fecha_str},
            timeout=15
        )
        if r.status_code != 200:
            print(f"{simbolo}: error HTTP {r.status_code} pidiendo daily {fecha_str}")
            return False
        hist = r.json().get("history") or {}
        dias = hist.get("day", [])
        if isinstance(dias, dict): dias = [dias]
        if not dias:
            return False  # Tradier aun no tiene el dato consolidado de ese dia
        d = dias[0]
        nueva_daily = {
            "time":     fecha_str + "T16:00:00",
            "open":     float(d["open"]),
            "high":     float(d["high"]),
            "low":      float(d["low"]),
            "close":    float(d["close"]),
            "volume":   int(d.get("volume", 0)),
            "interval": "daily"
        }
    except Exception as e:
        print(f"{simbolo}: error obteniendo daily Tradier {fecha_str}: {e}")
        return False

    local["barras"].append(nueva_daily)
    guardar_velas_local(simbolo, local)
    print(f"{simbolo}: barra diaria agregada (Tradier oficial) — {fecha_str} O:{nueva_daily['open']:.2f} C:{nueva_daily['close']:.2f}")
    return True


def rellenar_dias_faltantes(simbolo, es_dia_mercado, dias_atras=10):
    """Red de seguridad: revisa los ultimos N dias habiles y agrega
    cualquier barra diaria faltante. Recibe es_dia_mercado como parametro
    para evitar import circular con server.py."""
    hoy = date.today()
    agregadas = 0
    for i in range(dias_atras):
        fecha = hoy - timedelta(days=i)
        if fecha.weekday() >= 5:
            continue
        if not es_dia_mercado(EST.localize(datetime(fecha.year, fecha.month, fecha.day, 12, 0))):
            continue
        if agregar_barra_diaria(simbolo, fecha.strftime("%Y-%m-%d")):
            agregadas += 1
    return agregadas


def construir_base_datos_activo(simbolo, restar_dias_habiles):
    """Recibe restar_dias_habiles como parametro para evitar import
    circular con server.py."""
    local = cargar_velas_local(simbolo)
    if local["barras"]:
        print(f"{simbolo}: base de datos ya existe ({len(local['barras'])} registros)")
        return True

    print(f"{simbolo}: construyendo base de datos por primera vez...")
    hoy       = date.today()
    hace_2_anos = hoy.replace(year=hoy.year - 2)
    todas_barras = []

    try:
        r = requests.get(
            f"{TRADIER_BASE_REAL}/markets/history",
            headers=TRADIER_HEADERS_REAL,
            params={
                "symbol":   simbolo,
                "interval": "daily",
                "start":    hace_2_anos.strftime("%Y-%m-%d"),
                "end":      hoy.strftime("%Y-%m-%d"),
            },
            timeout=30
        )
        if r.status_code == 200:
            hist = r.json().get("history") or {}
            dias = hist.get("day", [])
            if isinstance(dias, dict): dias = [dias]
            for d in dias:
                todas_barras.append({
                    "time":     d["date"] + "T16:00:00",
                    "open":     float(d["open"]),
                    "high":     float(d["high"]),
                    "low":      float(d["low"]),
                    "close":    float(d["close"]),
                    "volume":   int(d.get("volume", 0)),
                    "interval": "daily"
                })
            print(f"  {simbolo} history diario: {len(dias)} días")
    except Exception as e:
        print(f"  {simbolo} error history diario: {e}")

    try:
        fecha_ini = restar_dias_habiles(hoy, 38)
        r2 = requests.get(
            f"{TRADIER_BASE_REAL}/markets/timesales",
            headers=TRADIER_HEADERS_REAL,
            params={
                "symbol":         simbolo,
                "interval":       "15min",
                "start":          f"{fecha_ini.strftime('%Y-%m-%d')} 09:00",
                "end":            f"{(hoy - timedelta(days=1)).strftime('%Y-%m-%d')} 16:30",
                "session_filter": "open",
            },
            timeout=30
        )
        if r2.status_code == 200:
            s = r2.json().get("series")
            if s and s != "null":
                b = s.get("data", [])
                if isinstance(b, dict): b = [b]
                for barra in b:
                    barra["interval"] = "15min"
                todas_barras.extend(b)
                print(f"  {simbolo} timesales 15min historial: {len(b)} barras")
        r3 = requests.get(
            f"{TRADIER_BASE_REAL}/markets/timesales",
            headers=TRADIER_HEADERS_REAL,
            params={
                "symbol":         simbolo,
                "interval":       "15min",
                "start":          f"{hoy.strftime('%Y-%m-%d')} 09:00",
                "end":            f"{hoy.strftime('%Y-%m-%d')} 16:30",
                "session_filter": "open",
            },
            timeout=30
        )
        if r3.status_code == 200:
            s3 = r3.json().get("series")
            if s3 and s3 != "null":
                b3 = s3.get("data", [])
                if isinstance(b3, dict): b3 = [b3]
                for barra in b3:
                    barra["interval"] = "15min"
                todas_barras.extend(b3)
                print(f"  {simbolo} timesales 15min hoy: {len(b3)} barras")
    except Exception as e:
        print(f"  {simbolo} error timesales: {e}")

    if not todas_barras:
        print(f"  {simbolo}: sin datos — base no construida")
        return False

    todas_barras.sort(key=lambda x: x["time"])
    ultima = todas_barras[-1]["time"]

    local["barras"]       = todas_barras
    local["ultima_barra"] = ultima
    guardar_velas_local(simbolo, local)
    print(f"  {simbolo}: base construida — {len(todas_barras)} registros | última: {ultima}")
    return True


def actualizar_velas_local(simbolo, restar_dias_habiles):
    """Recibe restar_dias_habiles como parametro (necesaria indirectamente
    via construir_base_datos_activo si la base no existe aun)."""
    local = cargar_velas_local(simbolo)

    if not local["barras"] or not local["ultima_barra"]:
        return construir_base_datos_activo(simbolo, restar_dias_habiles)

    ultima_str = local["ultima_barra"]
    try:
        if "T" in ultima_str:
            ultima_dt = datetime.strptime(ultima_str[:19], "%Y-%m-%dT%H:%M:%S")
        else:
            ultima_dt = datetime.strptime(ultima_str, "%Y-%m-%d")
    except:
        ultima_dt = datetime.now() - timedelta(days=1)

    desde = ultima_dt + timedelta(minutes=15)
    hoy   = date.today()

    if desde.date() > hoy:
        return True

    nuevas = []
    try:
        r = requests.get(
            f"{TRADIER_BASE_REAL}/markets/timesales",
            headers=TRADIER_HEADERS_REAL,
            params={
                "symbol":         simbolo,
                "interval":       "15min",
                "start":          desde.strftime("%Y-%m-%d %H:%M"),
                "end":            f"{hoy.strftime('%Y-%m-%d')} 16:30",
                "session_filter": "open",
            },
            timeout=30
        )
        if r.status_code == 200:
            s = r.json().get("series")
            if s and s != "null":
                b = s.get("data", [])
                if isinstance(b, dict): b = [b]
                for barra in b:
                    barra["interval"] = "15min"
                nuevas.extend(b)
    except Exception as e:
        print(f"Error actualizando velas {simbolo}: {e}")

    if nuevas:
        local["barras"].extend(nuevas)
        local["ultima_barra"] = nuevas[-1]["time"]
        guardar_velas_local(simbolo, local)
        print(f"{simbolo}: +{len(nuevas)} barras nuevas guardadas")

    return True


def construir_base_datos(es_dia_mercado, restar_dias_habiles):
    """Recibe es_dia_mercado y restar_dias_habiles como parametros para
    evitar import circular con server.py."""
    print("Verificando base de datos de velas...")
    for simbolo in ACTIVOS:
        construir_base_datos_activo(simbolo, restar_dias_habiles)
    print("Base de datos de velas lista.")
    print("Verificando barras diarias faltantes (red de seguridad)...")
    for simbolo in ACTIVOS:
        try:
            agregadas = rellenar_dias_faltantes(simbolo, es_dia_mercado, dias_atras=10)
            if agregadas:
                print(f"{simbolo}: {agregadas} barras diarias recuperadas")
        except Exception as e:
            print(f"Error rellenando dias faltantes {simbolo}: {e}")


def get_velas(simbolo, restar_dias_habiles, outputsize=280):
    """Construye las velas AXIS (V1-V7) agrupando barras de 15min, aplicando
    la regla de que una vela no existe hasta el :01 despues de su hora de
    cierre. Recibe restar_dias_habiles como parametro (necesaria
    indirectamente via actualizar_velas_local)."""
    try:
        actualizar_velas_local(simbolo, restar_dias_habiles)

        local = cargar_velas_local(simbolo)
        if not local["barras"]:
            print(f"get_velas {simbolo}: sin datos locales")
            return None

        barras_15min = [b for b in local["barras"] if b.get("interval") == "15min"]
        if not barras_15min:
            print(f"get_velas {simbolo}: sin barras 15min")
            return None

        dias_dict = defaultdict(lambda: defaultdict(list))
        for b in barras_15min:
            ts_str = b["time"].replace("T", " ")
            bdt    = datetime.strptime(ts_str[:19], "%Y-%m-%d %H:%M:%S")
            fecha  = bdt.strftime("%Y-%m-%d")
            h, m   = bdt.hour, bdt.minute
            if h == 9 and m in (30, 45):
                dias_dict[fecha]["V1"].append(b)
            elif h == 10: dias_dict[fecha]["V2"].append(b)
            elif h == 11: dias_dict[fecha]["V3"].append(b)
            elif h == 12: dias_dict[fecha]["V4"].append(b)
            elif h == 13: dias_dict[fecha]["V5"].append(b)
            elif h == 14: dias_dict[fecha]["V6"].append(b)
            elif h == 15: dias_dict[fecha]["V7"].append(b)

        vela_hora = {"V1":"09:30:00","V2":"10:00:00","V3":"11:00:00",
                     "V4":"12:00:00","V5":"13:00:00","V6":"14:00:00","V7":"15:00:00"}
        vela_bars = {"V1":2,"V2":4,"V3":4,"V4":4,"V5":4,"V6":4,"V7":4}
        resultado = []

        for fecha in sorted(dias_dict.keys(), reverse=True):
            for vela in ["V7","V6","V5","V4","V3","V2","V1"]:
                bs = dias_dict[fecha].get(vela, [])
                if not bs: continue
                o = float(bs[0]["open"])
                h = max(float(b["high"]) for b in bs)
                l = min(float(b["low"])  for b in bs)
                c = float(bs[-1]["close"])
                # Regla definitiva AXIS: una vela solo existe a partir del :01
                # despues de su hora de cierre completa
                vela_cierre_hora = {
                    "V1": 10, "V2": 11, "V3": 12, "V4": 13,
                    "V5": 14, "V6": 15, "V7": 16
                }
                try:
                    hora_cierre = vela_cierre_hora.get(vela)
                    if hora_cierre:
                        anno, mes, dia = int(fecha[:4]), int(fecha[5:7]), int(fecha[8:10])
                        cierre_dt = datetime(anno, mes, dia, hora_cierre, 1, 0)
                        cierre_est = EST.localize(cierre_dt)
                        if datetime.now(EST) < cierre_est:
                            continue  # vela no disponible aun
                except:
                    pass

                resultado.append({
                    "datetime":      f"{fecha} {vela_hora[vela]}",
                    "open":          str(round(o, 4)),
                    "high":          str(round(h, 4)),
                    "low":           str(round(l, 4)),
                    "close":         str(round(c, 4)),
                    "vela":          vela,
                    "bars":          len(bs),
                    "bars_expected": vela_bars[vela],
                    "completa":      len(bs) >= vela_bars[vela],
                })
            if len(resultado) >= outputsize:
                break

        if not resultado:
            print(f"get_velas {simbolo}: sin velas construidas")
            return None

        return resultado[:outputsize]

    except Exception as e:
        print(f"Error get_velas {simbolo}: {e}")
        return None
