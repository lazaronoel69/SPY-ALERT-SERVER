import sys

# Bloques exactos extraidos del server.py v8.84 real confirmado

OLD_BLOCKS_NEW = [
    # 1. EST -- se mantiene la linea import pytz (server.py la usa en otros lados
    #    como pytz.utc), solo reemplazamos la asignacion de EST por el import
    #    desde axis_config, manteniendo el mismo valor.
    (
        'EST              = pytz.timezone("America/New_York")',
        'from axis_config import EST  # AX-003: movido a axis_config.py, mismo valor'
    ),
    # 2. ACTIVOS, HORAS_REPORTE, ACTIVOS_SPY, SISTEMA_ACTIVO + switches estrategia
    (
        'ACTIVOS          = ["SPY", "AAPL", "BA", "GLD", "NVDA", "AMZN", "GOOG", "META"]\n'
        'HORAS_REPORTE    = [10, 11, 12, 13, 14, 15]\n'
        '# v8.84: hora 16 (4:00 PM / V7) eliminada de aqui -- V7 se evalua\n'
        '# EXCLUSIVAMENTE a las 3:58 PM via loop_v7_anticipada() con la vela\n'
        '# provisional. monitor_loop ya NO vuelve a evaluar V7 a las 4:01 PM,\n'
        '# evitando alertas duplicadas/falsas (caso GOOG RPG falso 06/25).\n'
        '# SPY cierra 4:15 PM EST — excepción única\n'
        'ACTIVOS_SPY      = ["SPY"]\n'
        'SISTEMA_ACTIVO   = True\n'
        '\n'
        '# Switches estrategias globales\n'
        'VR1_ON  = True\n'
        'RPG_ON  = True\n'
        'GNA_ON  = True\n'
        'GBA_ON  = True',
        '# AX-003: ACTIVOS, HORAS_REPORTE, ACTIVOS_SPY, SISTEMA_ACTIVO y switches\n'
        '# de estrategia movidos a axis_config.py, mismos valores y nombres.\n'
        'from axis_config import (\n'
        '    ACTIVOS, HORAS_REPORTE, ACTIVOS_SPY, SISTEMA_ACTIVO,\n'
        '    VR1_ON, RPG_ON, GNA_ON, GBA_ON,\n'
        ')'
    ),
    # 3. ORDEN_TIMEOUT_MIN
    (
        'ORDEN_TIMEOUT_MIN = 15  # minutos antes de expirar',
        'from axis_config import ORDEN_TIMEOUT_MIN  # AX-003: mismo valor (15)'
    ),
    # 4. Archivos de persistencia + DATA_DIR
    (
        'CANALES_FILE    = "/data/axis_canales.json"\n'
        'PORTFOLIO_FILE  = "/data/axis_portfolio.json"\n'
        'ORDENES_FILE    = "/data/axis_ordenes.json"\n'
        'ESTADO_FILE     = "/data/axis_estado_dia.json"\n'
        'SEÑALES_FILE    = "/data/axis_señales_historicas.json"\n'
        'BITACORA_FILE   = "/data/axis_bitacora.json"\n'
        'DATA_DIR        = "/data"',
        '# AX-003: rutas de persistencia movidas a axis_config.py, mismos valores.\n'
        'from axis_config import (\n'
        '    CANALES_FILE, PORTFOLIO_FILE, ORDENES_FILE, ESTADO_FILE,\n'
        '    SEÑALES_FILE, BITACORA_FILE, DATA_DIR,\n'
        ')'
    ),
    # 5. TRADIER_BASE y TRADIER_BASE_REAL
    (
        'TRADIER_BASE    = "https://sandbox.tradier.com/v1"',
        'from axis_config import TRADIER_BASE  # AX-003: mismo valor'
    ),
    (
        'TRADIER_BASE_REAL    = "https://api.tradier.com/v1"',
        'from axis_config import TRADIER_BASE_REAL  # AX-003: mismo valor'
    ),
]

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []
cambios_ok = 0

for old, new in OLD_BLOCKS_NEW:
    count = content.count(old)
    if count != 1:
        errors.append(f"Bloque no encontrado exactamente 1 vez (encontrado {count}x): {old[:60]}...")
    else:
        content = content.replace(old, new, 1)
        cambios_ok += 1

print(f"Cambios aplicados: {cambios_ok}/{len(OLD_BLOCKS_NEW)}")

if errors:
    print("ERRORES:")
    for e in errors:
        print("  - " + e)
    sys.exit(1)

with open("server.py", "w", encoding="utf-8") as f:
    f.write(content)
print("server.py actualizado — constantes ahora importadas desde axis_config.py")
