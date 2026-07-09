#!/usr/bin/env python3
"""
AX-TUNE-001A — Daily Signal Review
Reporte diario de señales reales de AXIS para revisión manual.

Fuentes:
  - /status          → señales vivas de hoy (labels completos con variante +2)
  - /señales_historicas → historial por fecha/símbolo (hora, tipo, vela)
  - /velas?simbolo=X → precio de la vela de señal (close)

Uso:
  python3 tools/daily_signal_review.py               # hoy
  python3 tools/daily_signal_review.py --date 2026-07-08
  python3 tools/daily_signal_review.py --days 3      # últimos 3 días
"""

import argparse
import sys
from datetime import date, timedelta
from typing import Optional

import requests

RAILWAY = "https://web-production-bf9d0.up.railway.app"
SYMBOLS = ["SPY", "AAPL", "BA", "GLD", "NVDA", "AMZN", "GOOG", "META"]

TIPO_DESCRIPCION = {
    "1VR":  "PRIMERA VELA ROJA",
    "RPG":  "RUPTURA PISO GAP",
    "GNA":  "GAP NORTE ALZA",
    "GBA":  "GAP BAJISTA ALZA",
    "RCB":  "CANAL RCB",
    "CNF":  "CANAL CNF",
    "PM40": "CANAL PM40",
    "4PS":  "4 PASOS",
    "HED":  "SHOOTING STAR",
}

CALL_TIPOS = {"GNA", "GBA"}


def tipo_a_dir(tipo: str) -> str:
    base = tipo.rstrip("+0123456789")
    return "CALL" if base in CALL_TIPOS else "PUT "


# ── Fetchers ────────────────────────────────────────────────────────────────

def fetch_status() -> dict:
    r = requests.get(f"{RAILWAY}/status", timeout=8)
    r.raise_for_status()
    return r.json()


def fetch_historial() -> dict:
    r = requests.get(f"{RAILWAY}/señales_historicas", timeout=8)
    r.raise_for_status()
    return r.json().get("historial", {})


def fetch_velas_simbolo(simbolo: str) -> tuple:
    """Retorna (velas: list, senales_hoy: list)."""
    r = requests.get(f"{RAILWAY}/velas", params={"simbolo": simbolo, "outputsize": 7}, timeout=8)
    r.raise_for_status()
    d = r.json()
    return d.get("velas", []), d.get("senales_hoy", [])


# ── Helpers ─────────────────────────────────────────────────────────────────

def precio_vela(velas: list, fecha: str, nombre_vela: str) -> Optional[str]:
    for v in velas:
        if v.get("datetime", "").startswith(fecha) and v.get("vela") == nombre_vela:
            return v.get("close")
    return None


def label_de_status(disparadas: list, tipo_base: str) -> str:
    """Busca el label completo (con variante) en la lista de señales disparadas de /status."""
    for label in disparadas:
        if tipo_base in label:
            return label
    return TIPO_DESCRIPCION.get(tipo_base, tipo_base)


# ── Construcción de señales por fecha ────────────────────────────────────────

def señales_hoy(status: dict) -> list:
    """
    Construye lista de señales para HOY combinando /status (labels completos)
    con /velas por símbolo (hora, vela, precio).
    """
    hoy = date.today().isoformat()
    resultado = []

    for sym in SYMBOLS:
        info = status.get("señales_hoy", {}).get(sym, {})
        disparadas = info.get("señales_disparadas", [])
        if not disparadas:
            continue

        try:
            velas, senales_velas = fetch_velas_simbolo(sym)
        except Exception as e:
            print(f"  [WARN] No se pudo obtener /velas para {sym}: {e}", file=sys.stderr)
            velas, senales_velas = [], []

        if senales_velas:
            for s in senales_velas:
                tipo  = s.get("tipo", "?")
                vela  = s.get("vela", "?")
                hora  = s.get("hora", "?")
                precio = precio_vela(velas, hoy, vela)
                label  = label_de_status(disparadas, tipo)
                resultado.append({
                    "fecha":   hoy,
                    "hora":    hora,
                    "simbolo": sym,
                    "tipo":    tipo,
                    "label":   label,
                    "vela":    vela,
                    "precio":  precio,
                    "dir":     tipo_a_dir(tipo),
                })
        else:
            # Fallback: señales del status sin hora ni precio
            for label in disparadas:
                tipo = label.split(" ")[0].split("+")[0]
                resultado.append({
                    "fecha":   hoy,
                    "hora":    "—",
                    "simbolo": sym,
                    "tipo":    tipo,
                    "label":   label,
                    "vela":    "—",
                    "precio":  None,
                    "dir":     tipo_a_dir(tipo),
                })

    return sorted(resultado, key=lambda s: (s["simbolo"], s["hora"]))


def señales_historicas(historial: dict, fecha: str) -> list:
    """Construye lista de señales para una fecha histórica desde /señales_historicas."""
    resultado = []
    dia = historial.get(fecha, {})

    for sym in SYMBOLS:
        for s in dia.get(sym, []):
            # Historial antiguo: strings simples ["1VR"]; reciente: dicts {tipo,hora,vela}
            if isinstance(s, str):
                tipo, hora, vela = s, "—", "—"
            else:
                tipo  = s.get("tipo", "?")
                hora  = s.get("hora", "—")
                vela  = s.get("vela", "—")
            label = TIPO_DESCRIPCION.get(tipo, tipo)
            resultado.append({
                "fecha":   fecha,
                "hora":    hora,
                "simbolo": sym,
                "tipo":    tipo,
                "label":   label,
                "vela":    vela,
                "precio":  None,
                "dir":     tipo_a_dir(tipo),
            })

    return sorted(resultado, key=lambda s: (s["simbolo"], s["hora"]))


# ── Imprimir reporte ─────────────────────────────────────────────────────────

def print_reporte(fecha: str, señales: list) -> None:
    linea = "─" * 54

    print()
    print(f"  AXIS SIGNAL REVIEW — {fecha}")
    print(f"  {'═' * 42}")

    if not señales:
        print(f"  Sin señales registradas para {fecha}.")
        print()
        return

    total = len(señales)
    syms_con_senal = len({s["simbolo"] for s in señales})
    print(f"  TOTAL: {total} señal{'es' if total != 1 else ''}  |  {syms_con_senal} símbolo{'s' if syms_con_senal != 1 else ''}")
    print()

    # ── Por símbolo ──
    by_sym = {}
    for s in señales:
        by_sym.setdefault(s["simbolo"], []).append(s)

    for sym in SYMBOLS:
        if sym not in by_sym:
            continue
        print(f"  ── {sym} {'─' * (48 - len(sym))}")
        for s in by_sym[sym]:
            precio_str = f"  ${float(s['precio']):.2f}" if s["precio"] else ""
            vela_hora  = f"{s['vela']:3s}  {s['hora']:12s}"
            print(f"     {vela_hora}  {s['tipo']:6s}  {s['dir']}{precio_str}")
            print(f"        ↳ {s['label']}")
            print(f"        [ ] BUENA   [ ] MEJORABLE   [ ] MALA")
            print(f"        OBSERVACIÓN: _______________________________________")
            print()

    # ── Resumen por estrategia ──
    print(f"  {linea}")
    print(f"  RESUMEN POR ESTRATEGIA")
    by_strat = {}
    for s in señales:
        base = s["tipo"].rstrip("+0123456789")
        by_strat.setdefault(base, []).append(s["simbolo"])
    for tipo, syms in sorted(by_strat.items(), key=lambda x: -len(x[1])):
        desc  = TIPO_DESCRIPCION.get(tipo, tipo)
        count = len(syms)
        print(f"    {tipo:6s}  ({count})  {', '.join(syms):<30s}  — {desc}")

    # ── Resumen CALL / PUT ──
    calls = [s for s in señales if "CALL" in s["dir"]]
    puts  = [s for s in señales if "PUT"  in s["dir"]]
    print()
    print(f"  CALL: {len(calls)}  |  PUT: {len(puts)}")
    print()


# ── Main ─────────────────────────────────────────────────────────────────────

def send_telegram_debrief() -> None:
    """Llama /daily_debrief/send?force=1 en el servidor de producción."""
    url = f"{RAILWAY}/daily_debrief/send?force=1"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        d = r.json()
        if d.get("ok"):
            print(f"  ✓ Debrief enviado a Telegram — {d.get('mensaje', '')}")
        else:
            print(f"  [WARN] Respuesta inesperada: {d}", file=sys.stderr)
    except Exception as e:
        print(f"  [ERROR] No se pudo enviar debrief: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="AXIS Daily Signal Review (AX-TUNE-001A)")
    parser.add_argument("--date", help="Fecha YYYY-MM-DD (default: hoy)")
    parser.add_argument("--days", type=int, help="Últimos N días")
    parser.add_argument("--send-telegram", action="store_true",
                        help="Envía el daily debrief a Telegram vía /daily_debrief/send?force=1")
    args = parser.parse_args()

    hoy = date.today().isoformat()

    if args.send_telegram:
        print(f"\n  Fuente: {RAILWAY}")
        send_telegram_debrief()
        return

    print(f"\n  Fuente: {RAILWAY}")

    try:
        status = fetch_status()
        print(f"  Servidor: {status.get('hora_est', '?')}  |  Mercado: {status.get('mercado', '?')}")
    except Exception as e:
        print(f"  [ERROR] No se pudo obtener /status: {e}", file=sys.stderr)
        status = {}

    try:
        historial = fetch_historial()
    except Exception as e:
        print(f"  [ERROR] No se pudo obtener historial: {e}", file=sys.stderr)
        historial = {}

    if args.days:
        fechas = [
            (date.today() - timedelta(days=i)).isoformat()
            for i in range(args.days - 1, -1, -1)
        ]
    elif args.date:
        fechas = [args.date]
    else:
        fechas = [hoy]

    for fecha in fechas:
        if fecha == hoy:
            senal_list = señales_hoy(status)
        else:
            senal_list = señales_historicas(historial, fecha)
        print_reporte(fecha, senal_list)


if __name__ == "__main__":
    main()
