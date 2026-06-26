# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-010 (Market Data Baseline) ejecutado — las 6 funciones de construcción/actualización de velas locales movidas a `axis_market.py`, sin cambiar la regla del `:01`, horarios de velas (V1-V7), llamadas a Tradier, outputsize, ni formato JSON. Sin import circular: `es_dia_mercado` y `restar_dias_habiles` permanecen en server.py y se inyectan como parámetro. Verificado con py_compile, simulación de import real, y prueba funcional de `get_velas()` end-to-end a través de los wrappers.

## Funciones movidas a axis_market.py (AX-010)

1. `agregar_barra_diaria(simbolo, fecha_str=None)` — sin dependencias de `es_dia_mercado`/`restar_dias_habiles`.
2. `rellenar_dias_faltantes(simbolo, es_dia_mercado, dias_atras=10)` — recibe `es_dia_mercado` como parámetro.
3. `construir_base_datos_activo(simbolo, restar_dias_habiles)` — recibe `restar_dias_habiles` como parámetro.
4. `actualizar_velas_local(simbolo, restar_dias_habiles)` — recibe `restar_dias_habiles` como parámetro (la necesita indirectamente, vía `construir_base_datos_activo`).
5. `construir_base_datos(es_dia_mercado, restar_dias_habiles)` — recibe ambas como parámetro.
6. `get_velas(simbolo, restar_dias_habiles, outputsize=280)` — recibe `restar_dias_habiles` como parámetro (indirectamente, vía `actualizar_velas_local`). Contiene la regla del `:01` intacta, sin modificar.

server.py mantiene wrappers con las **firmas públicas originales exactas** (`get_velas(simbolo, outputsize=280)`, `construir_base_datos()`, etc., sin parámetros nuevos visibles) que inyectan `es_dia_mercado`/`restar_dias_habiles` automáticamente al llamar a `axis_market.py`. Ninguna llamada existente en el resto de server.py (incluyendo `reporte_horario()`, `arrancar_monitor()`, `evaluar_v7_anticipada()`, etc.) se modificó.

## Decisión de diseño: por qué no hay import circular

`es_dia_mercado` y `restar_dias_habiles` permanecen en server.py porque se usan en mucho más que datos de mercado (canales, portfolio, polling de posiciones, etc.). Si `axis_market.py` hiciera `from server import es_dia_mercado`, y `server.py` hace `from axis_market import get_velas`, esto crearía un import circular — el mismo tipo de error de orden de ejecución identificado el 06/25 con el crash de `import os`. La solución: las funciones de `axis_market.py` que las necesitan las reciben como **parámetro**, nunca las importan directamente.

## Archivos modificados en este sprint

- **Creado:** `axis_market.py` — las 6 funciones, con `cargar_velas_local`/`guardar_velas_local` importadas desde `axis_storage.py` (AX-005), y `TRADIER_TOKEN_REAL`/`TRADIER_BASE_REAL`/`TRADIER_HEADERS_REAL` leídas vía `os.environ` (mismo patrón que `axis_tradier.py`, AX-004).
- **Modificado:** `server.py` — 6 wrappers que preservan las firmas públicas originales.

## Último commit antes de este sprint

e242e4a — AX-009 Channels Baseline

## Rama

main

## Sprint activo

AX-010 — Market Data Baseline (este sprint)

## Próximo sprint sugerido

AX-011 — considerar mover `es_dia_mercado`/`calcular_festivos`/`calcular_pascua`/`restar_dias_habiles` a un módulo `axis_time.py` propio (Time Engine, del backlog original AX-003) — una vez que viva ahí, `axis_market.py` podría importarlas directamente sin riesgo de circularidad, ya que ninguno de los dos dependería del otro.

## Riesgos abiertos

1. GLD sin canal bajista activo actualmente
2. Pendiente verificar visualmente que no hay alertas duplicadas tras v8.84
3. 4PASOS solo dentro de RCB
4. Tradier limita historial de 15min a ~40 días
5. Bug cosmético: chart marca "EN FORMACIÓN" en la última vela ya cerrada
6. Frontend aún calcula canales PM40/4PASOS en JavaScript
7. TWELVEDATA_KEY y FINNHUB_KEY siguen hardcodeados en server.py (ver AX-003)
8. TRADIER_TOKEN/TRADIER_ACCOUNT/TRADIER_HEADERS duplicados en server.py y axis_tradier.py (ver AX-004); ahora TAMBIÉN TRADIER_TOKEN_REAL/TRADIER_BASE_REAL/TRADIER_HEADERS_REAL duplicados en server.py y axis_market.py, mismo patrón.
9. archivar_señales_dia aún sin mover (ver AX-005)
10. TELEGRAM_TOKEN/TELEGRAM_CHAT_ID duplicados en server.py y axis_telegram.py (ver AX-006)
11. enviar_telegram_botones sigue acoplada a Portfolio/Derby en server.py (ver AX-006)
12. registrar_posicion/cerrar_posicion siguen en server.py (ver AX-008)
13. calcular_techo_canal/calcular_piso_mitad_canal siguen en server.py (ver AX-009)
14. **NUEVO AX-010:** `es_dia_mercado` y `restar_dias_habiles` siguen viviendo en server.py, ahora como dependencia inyectada de 6 funciones nuevas además de las que ya las usaban — alta centralidad, candidatas principales para AX-011 (Time Engine).
15. **NUEVO AX-010:** axis_market.py es ahora el módulo más grande creado hasta el momento (367 líneas) — si crece más, considerar dividirlo en construcción de base de datos vs. construcción de velas AXIS (V1-V7).

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Nunca codificar sin autorización explícita de Noel
- Verificar sintaxis y simular orden de ejecución real después de cualquier fix (lección del crash de import os, 06/25)
- Patrón establecido para evitar import circular: cuando un módulo nuevo necesita una función que vive en server.py y server.py necesita importar del módulo nuevo, la función de server.py se pasa como PARÁMETRO, nunca se importa directamente
