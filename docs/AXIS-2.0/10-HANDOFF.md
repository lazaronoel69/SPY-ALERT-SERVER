# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-007 (Orders Baseline) ejecutado — `guardar_ordenes`/`cargar_ordenes` movidas a `axis_orders.py` (reciben `ordenes_pendientes` como parámetro), con wrappers en server.py manteniendo los nombres y firmas originales sin argumentos. Sin cambios en formato de axis_ordenes.json ni en ORDEN_TIMEOUT_MIN. Verificado con py_compile, simulación de import real, y prueba funcional del wrapper modificando el dict global in-place.

## Funciones movidas a axis_orders.py (AX-007)

1. `guardar_ordenes(ordenes_pendientes)` — recibe el dict como parámetro.
2. `cargar_ordenes(ordenes_pendientes)` — recibe el dict como parámetro, lo modifica in-place (mismo comportamiento que el original con el global).

server.py mantiene wrappers `guardar_ordenes()` y `cargar_ordenes()` sin argumentos que llaman a `axis_orders.guardar_ordenes(ordenes_pendientes)` / `axis_orders.cargar_ordenes(ordenes_pendientes)`, pasando su propio global. Ninguna llamada existente (incluyendo `loop_limpiar_ordenes`, que llama a `guardar_ordenes()` sin argumentos) se modificó.

## Funciones NO movidas y razón (según regla explícita del sprint)

- **`loop_limpiar_ordenes()`** — thread que revisa órdenes expiradas cada 60s y edita mensajes de Telegram. Excluida explícitamente. Sigue llamando a `guardar_ordenes()` (el wrapper) exactamente igual que antes.
- **`enviar_senal_con_botones()`** — orquesta Tradier + Telegram + esta persistencia (`guardar_ordenes()`). Excluida explícitamente.
- **`telegram_webhook()`** — maneja ejecución de órdenes, Portfolio y Derby. Excluida explícitamente.

## Archivos modificados en este sprint

- **Creado:** `axis_orders.py` — 2 funciones parametrizadas, mismo formato JSON, mismo `ORDEN_TIMEOUT_MIN` (leído desde `axis_config.py`).
- **Modificado:** `server.py` — `guardar_ordenes`/`cargar_ordenes` ahora son wrappers de 2 líneas que llaman a `axis_orders.py`.

## Último commit antes de este sprint

1cc6a84 — AX-006 Telegram Baseline

## Rama

main

## Sprint activo

AX-007 — Orders Baseline (este sprint)

## Próximo sprint sugerido

AX-008 — Channel Engine (canales bajistas CNF/RCB/PM40, según backlog original) o continuar el patrón de wrapper con `guardar_portfolio`/`cargar_portfolio` (dependencia de `_portfolio`, incluyendo Derby) como paso intermedio antes de Canales.

## Riesgos abiertos

1. GLD sin canal bajista activo actualmente
2. Pendiente verificar visualmente que no hay alertas duplicadas tras v8.84
3. 4PASOS solo dentro de RCB
4. Tradier limita historial de 15min a ~40 días
5. Bug cosmético: chart marca "EN FORMACIÓN" en la última vela ya cerrada
6. Frontend aún calcula canales PM40/4PASOS en JavaScript
7. TWELVEDATA_KEY y FINNHUB_KEY siguen hardcodeados en server.py (ver AX-003)
8. TRADIER_TOKEN/TRADIER_ACCOUNT/TRADIER_HEADERS duplicados en server.py y axis_tradier.py (ver AX-004)
9. guardar_portfolio/cargar_portfolio, guardar_canales/cargar_canales, archivar_señales_dia aún sin mover (ver AX-005)
10. TELEGRAM_TOKEN/TELEGRAM_CHAT_ID duplicados en server.py y axis_telegram.py (ver AX-006)
11. enviar_telegram_botones sigue acoplada a Portfolio/Derby en server.py (ver AX-006)
12. **NUEVO AX-007:** el patrón de wrapper con parámetro explícito (en vez de global) ya se usó en AX-005 (`guardar_estado_dia`) y ahora en AX-007 (`guardar_ordenes`/`cargar_ordenes`) — establecido como el patrón estándar para cualquier función futura que dependa de estado global mutable.

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Nunca codificar sin autorización explícita de Noel
- Verificar sintaxis y simular orden de ejecución real después de cualquier fix (lección del crash de import os, 06/25)
- axis_orders.py no debe crecer para incluir lógica de envío de Telegram ni ejecución Tradier — solo persistencia del dict ordenes_pendientes
