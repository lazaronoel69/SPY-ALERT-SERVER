"""
AXIS Backtest Engine — BT-002 Minimal Harness
Reutiliza evaluar_activo() del motor real sin duplicar lógica.
Ver docs/AXIS-2.0/08-BACKTEST-DESIGN.md para diseño completo.

Uso:
  python3 backtest.py --symbol SPY --date 2026-06-30
"""

import argparse
import json
import sys
from datetime import datetime

# ── 1. Importar server (el motor real) ──────────────────────────────────────
import server

# ── 2. Monkey-patches — desacoplar efectos secundarios ──────────────────────
# Señales interceptadas se acumulan aquí en lugar de ir a Telegram/Tradier.
_bt_signals = []

def _interceptor_senal(simbolo, estrategia, hora_label, precio_vela, tipo_opcion, extra=""):
    _bt_signals.append({
        "simbolo":    simbolo,
        "estrategia": estrategia,
        "hora_label": hora_label,
        "precio":     precio_vela,
        "tipo":       tipo_opcion,
        "extra":      extra,
    })

server.enviar_senal_con_botones          = _interceptor_senal
server.guardar_estado_dia                = lambda *a, **k: None
server.guardar_canales                   = lambda *a, **k: None
server.guardar_ordenes                   = lambda *a, **k: None
server.guardar_portfolio                 = lambda *a, **k: None
# Evita HTTP a Tradier al llamar get_velas() internamente
server._axis_market.actualizar_velas_local = lambda *a, **k: None

# ── 3-5. Cargar velas y filtrar por fecha ────────────────────────────────────

def cargar_velas_bt(symbol, fecha):
    """Lee data/bt_velas_<SYMBOL>.json y retorna velas <= fecha, newest-first."""
    path = f"data/bt_velas_{symbol}.json"
    try:
        with open(path) as f:
            todas = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {path} no existe. Ejecuta el download de datos primero.", file=sys.stderr)
        sys.exit(1)

    # Filtrar velas hasta la fecha objetivo (inclusive) para no contaminar
    # el contexto con datos futuros al evaluar fechas históricas.
    filtradas = [v for v in todas if v["datetime"][:10] <= fecha]
    # get_velas() devuelve newest-first; bt_velas ya viene en ese orden.
    return filtradas


def velas_del_dia(velas, fecha):
    """Retorna las velas AXIS de un día específico, ordenadas V1→V7."""
    dia = [v for v in velas if v["datetime"].startswith(fecha)]
    dia.sort(key=lambda v: v["datetime"])
    return dia


# ── 6. Loop de evaluación ────────────────────────────────────────────────────

# V1 empieza a las 09:30 (hour=9); preparar_contexto_vela busca dt.hour == ahora.hour - 1.
# Para que encuentre V1 (hour=9), ahora.hour debe ser 10.
_VELA_A_AHORA_HOUR = {
    "V1": 10, "V2": 11, "V3": 12,
    "V4": 13, "V5": 14, "V6": 15, "V7": 16,
}

def evaluar_dia(symbol, fecha):
    """Replay de un día completo: carga velas, resetea estado, llama evaluar_activo V1→V7."""
    from axis_config import EST

    # Asegurar que el símbolo tiene estado y canal inicializados
    if symbol not in server.estado_dia:
        server.estado_dia[symbol] = server.estado_diario_vacio()
    if symbol not in server.canal:
        from axis_channels import canal_vacio
        server.canal[symbol] = canal_vacio()

    # Forzar reset diario para que el día empiece limpio
    server.estado_dia[symbol] = server.estado_diario_vacio()

    velas = cargar_velas_bt(symbol, fecha)
    if not velas:
        return {"error": f"Sin velas para {symbol} hasta {fecha}"}

    dia = velas_del_dia(velas, fecha)
    if not dia:
        return {"error": f"Sin velas para {symbol} en {fecha}"}

    evaluadas = []
    señales_antes = len(_bt_signals)

    for vela in dia:
        nombre_vela = vela.get("vela", "?")
        ahora_hour  = _VELA_A_AHORA_HOUR.get(nombre_vela)
        if ahora_hour is None:
            continue

        # Construir datetime sintético EST para esta vela
        fecha_dt     = datetime.strptime(fecha, "%Y-%m-%d")
        ahora_naive  = fecha_dt.replace(hour=ahora_hour, minute=1, second=0)
        ahora_est    = EST.localize(ahora_naive)

        server.evaluar_activo(symbol, velas, ahora_est)
        evaluadas.append(nombre_vela)

    señales_capturadas = _bt_signals[señales_antes:]

    return {
        "symbol":          symbol,
        "date":            fecha,
        "velas_evaluadas": evaluadas,
        "signals":         señales_capturadas,
    }


# ── 7. Entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AXIS Backtest Engine v1")
    parser.add_argument("--symbol", required=True, help="Símbolo, ej. SPY")
    parser.add_argument("--date",   required=True, help="Fecha YYYY-MM-DD")
    args = parser.parse_args()

    resultado = evaluar_dia(args.symbol, args.date)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
