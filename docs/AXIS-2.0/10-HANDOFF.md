# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-008 (Portfolio Baseline) ejecutado — `DERBY_CABALLOS`, `portfolio_vacio`, `cargar_portfolio` y `guardar_portfolio` movidas a `axis_portfolio.py`, sin cambiar estructura JSON ni comportamiento observable (incluyendo el guardado automático en los 3 casos de migración reto→derby/derby faltante/portfolio nuevo). Verificado con py_compile, simulación de import real, y prueba funcional completa de `cargar_portfolio()`.

## Funciones/datos movidos a axis_portfolio.py (AX-008)

1. `DERBY_CABALLOS` — lista de los 4 caballos (Noel, Paula, Noel Andres, Emilia).
2. `portfolio_vacio()` — función pura, sin cambios.
3. `cargar_portfolio()` — ahora **devuelve** `(data, debe_guardar)` en vez de asignar el global `_portfolio` directamente. `debe_guardar` es `True` en los mismos 3 casos donde el original llamaba a `guardar_portfolio()` internamente (migración reto→derby, derby faltante, portfolio nuevo).
4. `guardar_portfolio(data)` — recibe el dict como parámetro en vez de leer el global.

server.py mantiene wrappers `cargar_portfolio()` y `guardar_portfolio()` sin argumentos: el wrapper de `cargar_portfolio()` asigna el resultado a su propio global `_portfolio` y llama a su propio `guardar_portfolio()` si `debe_guardar` es `True` — preservando exactamente el mismo efecto observable (el archivo se guarda en los mismos momentos que antes).

## Funciones NO movidas y razón (según regla explícita del sprint)

- **`registrar_posicion(...)`** — lógica de negocio (crea posición, actualiza Derby si `es_reto`). Excluida explícitamente. Sigue llamando a `cargar_portfolio()`/`guardar_portfolio()` (los wrappers) exactamente igual que antes.
- **`cerrar_posicion(...)`** — lógica de negocio (cálculo de P&L, actualización de capital del Derby, detección de ganador). Excluida explícitamente.
- **Funciones de Derby** (`derby_activar`, `derby_desactivar`, `derby_status`, etc.) — excluidas explícitamente.

## Archivos modificados en este sprint

- **Creado:** `axis_portfolio.py` — `DERBY_CABALLOS`, `portfolio_vacio()`, y versiones parametrizadas de `cargar_portfolio()`/`guardar_portfolio()`.
- **Modificado:** `server.py` — wrappers que preservan el global `_portfolio` y el comportamiento de guardado automático.

## Último commit antes de este sprint

5c9bc32 — AX-007 Orders Baseline

## Rama

main

## Sprint activo

AX-008 — Portfolio Baseline (este sprint)

## Próximo sprint sugerido

AX-009 — Channel Engine (canales bajistas CNF/RCB/PM40, según backlog original) o continuar con `guardar_canales`/`cargar_canales` usando el mismo patrón de parámetro+wrapper, como paso intermedio antes de abordar la lógica completa de canales.

## Riesgos abiertos

1. GLD sin canal bajista activo actualmente
2. Pendiente verificar visualmente que no hay alertas duplicadas tras v8.84
3. 4PASOS solo dentro de RCB
4. Tradier limita historial de 15min a ~40 días
5. Bug cosmético: chart marca "EN FORMACIÓN" en la última vela ya cerrada
6. Frontend aún calcula canales PM40/4PASOS en JavaScript
7. TWELVEDATA_KEY y FINNHUB_KEY siguen hardcodeados en server.py (ver AX-003)
8. TRADIER_TOKEN/TRADIER_ACCOUNT/TRADIER_HEADERS duplicados en server.py y axis_tradier.py (ver AX-004)
9. guardar_canales/cargar_canales, archivar_señales_dia aún sin mover (ver AX-005)
10. TELEGRAM_TOKEN/TELEGRAM_CHAT_ID duplicados en server.py y axis_telegram.py (ver AX-006)
11. enviar_telegram_botones sigue acoplada a Portfolio/Derby en server.py (ver AX-006)
12. **NUEVO AX-008:** `registrar_posicion` y `cerrar_posicion` siguen siendo las funciones de mayor responsabilidad sobre `_portfolio` en server.py — candidatas principales para un futuro AX-00X dedicado a "Portfolio Logic" (distinto de este sprint, que solo cubrió estructura/persistencia básica).
13. **NUEVO AX-008:** el patrón "devolver tupla (data, debe_guardar)" usado en `cargar_portfolio()` es nuevo respecto a los patrones anteriores (AX-005 y AX-007 solo usaban parámetro simple) — documentado aquí porque preserva un efecto secundario (guardado condicional) que los patrones anteriores no tenían que resolver.

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Nunca codificar sin autorización explícita de Noel
- Verificar sintaxis y simular orden de ejecución real después de cualquier fix (lección del crash de import os, 06/25)
- axis_portfolio.py no debe crecer para incluir registrar_posicion, cerrar_posicion, ni lógica de Derby — solo estructura y persistencia básica, según el alcance explícito de AX-008
