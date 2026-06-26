# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-003 (Configuration Baseline) ejecutado — solo se movieron constantes de configuración simple a un archivo dedicado, sin cambiar ningún valor ni comportamiento. Verificado con py_compile y simulación de import real (no solo sintaxis).

## Archivos modificados en este sprint

- **Creado:** `axis_config.py` — contiene EST, ACTIVOS, HORAS_REPORTE, ACTIVOS_SPY, SISTEMA_ACTIVO, VR1_ON, RPG_ON, GNA_ON, GBA_ON, ORDEN_TIMEOUT_MIN, DATA_DIR, CANALES_FILE, PORTFOLIO_FILE, ORDENES_FILE, ESTADO_FILE, SEÑALES_FILE, BITACORA_FILE, TRADIER_BASE, TRADIER_BASE_REAL. Todos con los mismos valores exactos que tenían en server.py.
- **Modificado:** `server.py` — las constantes anteriores ahora se importan desde `axis_config.py` en vez de definirse localmente. Ninguna lógica de trading, evaluación, Telegram, ejecución de órdenes, Portfolio ni Derby fue tocada.

## Último commit antes de este sprint

1a0cdbc — cleanup: eliminar setup_ax001.sh temporal

## Rama

main

## Sprint activo

AX-003 — Configuration Baseline (este sprint)

## Próximo sprint sugerido

AX-004 — Candle Engine (según backlog AX-005 original, puede reordenarse: Time Engine también es candidato natural ya que EST y la lógica de horarios quedaron documentadas en AX-002 pero no extraídas como módulo propio)

## Riesgos abiertos

1. GLD sin canal bajista activo actualmente
2. Pendiente verificar visualmente que no hay alertas duplicadas tras v8.84
3. 4PASOS solo dentro de RCB
4. Tradier limita historial de 15min a ~40 días
5. Bug cosmético: chart marca "EN FORMACIÓN" en la última vela ya cerrada
6. Frontend aún calcula canales PM40/4PASOS en JavaScript
7. **NUEVO AX-003:** Tokens y claves (TELEGRAM_TOKEN, TRADIER_TOKEN, TRADIER_TOKEN_REAL, ANTHROPIC_API_KEY) permanecen en server.py leídos vía os.environ — correcto y seguro, pero TWELVEDATA_KEY y FINNHUB_KEY siguen hardcodeados como strings literales en server.py (líneas de configuración, no usados activamente según v8.84 pero presentes). No se tocaron en este sprint por estar fuera del alcance de "configuración simple" pedido — quedan documentados como riesgo de seguridad menor, ya que son claves de servicios externos no esenciales para la operación actual (TwelveData fue migrado/eliminado según v8.17).
8. **NUEVO AX-003:** axis_config.py depende únicamente de `pytz` — si en el futuro se agregan constantes que dependan de otras librerías, verificar que axis_config.py no termine importando algo que cause un ciclo de imports con server.py.

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Nunca codificar sin autorización explícita de Noel
- Verificar sintaxis y simular orden de ejecución después de cualquier fix (lección del crash de import os, 06/25)
- axis_config.py es solo el primer paso de modularización — no incluye nada de lógica de trading, Telegram, Tradier (ejecución), Portfolio ni Derby, según las reglas explícitas del sprint AX-003
