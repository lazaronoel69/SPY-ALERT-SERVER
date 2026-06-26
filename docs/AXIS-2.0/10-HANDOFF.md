# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-006 (Telegram Baseline) ejecutado — solo `enviar_telegram` movida a `axis_telegram.py`, sin cambiar texto de alertas, botones, parse_mode, timeout, ni comportamiento. Verificado con py_compile y simulación de import real.

## Funciones movidas a axis_telegram.py (AX-006)

1. `enviar_telegram(mensaje)` — mismo parse_mode HTML, mismo timeout (10s), mismo formato de payload.

## Funciones NO movidas y razón

- **`enviar_telegram_botones(mensaje, orden_id)`** — depende fuertemente de `_portfolio` y de la lógica del Derby: lee `derby["activo"]`, `derby["turno_actual"]`, `derby["caballos"]` para decidir si mostrar el botón 🏇 DERBY y a cuál caballo asignarlo. Moverla a axis_telegram.py obligaría a ese módulo a depender de Portfolio/Derby, justo lo que el sprint prohíbe explícitamente. Queda en server.py.
- **`telegram_webhook()`** (ruta Flask) — excluida explícitamente por el sprint. Contiene lógica de órdenes, ejecución Tradier, Portfolio y Derby.
- **`enviar_senal_con_botones()`** — excluida explícitamente por el sprint. Orquesta `registrar_senal_disparada`, precio Tradier, opción Tradier, y `enviar_telegram_botones`.

## Archivos modificados en este sprint

- **Creado:** `axis_telegram.py` — 1 función (`enviar_telegram`), leyendo `TELEGRAM_TOKEN`/`TELEGRAM_CHAT_ID` vía `os.environ` igual que antes.
- **Modificado:** `server.py` — `enviar_telegram` ahora se importa desde `axis_telegram.py`. `enviar_telegram_botones` permanece sin cambios.

## Último commit antes de este sprint

0c355b8 — AX-005 Storage Baseline

## Rama

main

## Sprint activo

AX-006 — Telegram Baseline (este sprint)

## Próximo sprint sugerido

AX-007 — considerar mover `enviar_telegram_botones` usando el mismo patrón de wrapper de AX-005 (la función movida recibe el estado del Derby como parámetro en vez de leer `_portfolio` global), si se decide seguir modularizando Telegram antes de abordar Portfolio/Derby como módulo propio. Alternativamente, AX-007 podría enfocarse directamente en Channel Engine (canales bajistas), según el backlog original.

## Riesgos abiertos

1. GLD sin canal bajista activo actualmente
2. Pendiente verificar visualmente que no hay alertas duplicadas tras v8.84
3. 4PASOS solo dentro de RCB
4. Tradier limita historial de 15min a ~40 días
5. Bug cosmético: chart marca "EN FORMACIÓN" en la última vela ya cerrada
6. Frontend aún calcula canales PM40/4PASOS en JavaScript
7. TWELVEDATA_KEY y FINNHUB_KEY siguen hardcodeados en server.py (ver AX-003)
8. TRADIER_TOKEN/TRADIER_ACCOUNT/TRADIER_HEADERS duplicados en server.py y axis_tradier.py (ver AX-004)
9. guardar_ordenes/cargar_ordenes, guardar_portfolio/cargar_portfolio, guardar_canales/cargar_canales, archivar_señales_dia aún sin mover (ver AX-005)
10. **NUEVO AX-006:** `TELEGRAM_TOKEN`/`TELEGRAM_CHAT_ID` ahora existen duplicados en server.py y axis_telegram.py, ambos leyendo el mismo `os.environ` — mismo patrón de duplicación controlada que TRADIER_TOKEN en AX-004, documentado por consistencia.
11. **NUEVO AX-006:** `enviar_telegram_botones` sigue siendo la función con más responsabilidad mezclada en server.py respecto a Telegram (mensajería + decisión de Derby) — candidata principal para el patrón de wrapper en un futuro sprint.

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Nunca codificar sin autorización explícita de Noel
- Verificar sintaxis y simular orden de ejecución real después de cualquier fix (lección del crash de import os, 06/25)
- axis_telegram.py debe seguir conteniendo solo mensajería pura — cualquier función que decida lógica de negocio (Derby, Portfolio, órdenes) debe usar el patrón de wrapper visto en AX-005, no moverse directamente
