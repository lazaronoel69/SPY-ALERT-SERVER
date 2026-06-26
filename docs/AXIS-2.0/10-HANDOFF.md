# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-004 (Tradier Access Baseline) ejecutado — funciones puras de acceso a Tradier movidas a `axis_tradier.py`, sin cambiar comportamiento, URLs, headers ni payloads. Verificado con py_compile y simulación de import real.

## Funciones movidas a axis_tradier.py (AX-004)

1. `cancelar_orden_tradier(orden_id)`
2. `get_bid_opcion_tradier(option_symbol)`
3. `vender_opcion_tradier(option_symbol, simbolo, contratos, precio_limit)`
4. `get_precio_tradier(simbolo)`
5. `get_opcion_tradier(simbolo, tipo, precio_actual)`
6. `ejecutar_orden_tradier(opcion)`
7. `ejecutar_orden_tradier_contratos(opcion, contratos)`
8. `get_pct_otm(precio)` — auxiliar pura, dependencia directa de `get_opcion_tradier`, no estaba en la lista original pero se movió junto por ser usada exclusivamente por una función que sí se movía.

Todas mantienen exactamente el mismo nombre, firma, comportamiento, URLs y payloads. `server.py` ahora las importa: `from axis_tradier import (...)`.

## Funciones NO movidas y razón

- **`get_estado_orden_tradier(orden_id)`** — no estaba en la lista pedida. Usa `TRADIER_BASE`, `TRADIER_ACCOUNT`, `TRADIER_HEADERS` igual que las demás, pero queda fuera del alcance explícito de este sprint. Candidata natural para un futuro AX-00X de "Tradier Polling".
- **`tradier_test()` (ruta Flask `/tradier_test`)** — no es una función pura de acceso, es un endpoint que además llama a `enviar_telegram()`. Mezclar rutas Flask con el módulo de acceso puro violaría la regla de "no tocar Telegram" del sprint.
- **`buscar_opcion_reto(opcion_original, presupuesto)`** y **`recomendar_opcion_claude(...)`** — no estaban en la lista pedida. La primera depende de lógica de negocio del Derby (busca opciones alternativas dentro de presupuesto), la segunda depende de Anthropic/Claude. Ninguna es "acceso puro a Tradier" en el sentido del sprint.
- **`TRADIER_TOKEN`, `TRADIER_ACCOUNT`, `TRADIER_HEADERS` permanecen también en `server.py`** (no solo en `axis_tradier.py`) porque `tradier_test()` y `get_estado_orden_tradier()` —que no se movieron— siguen necesitándolas ahí. axis_tradier.py tiene su propia copia idéntica de estas variables, leyendo el mismo `os.environ`, para no crear una dependencia cruzada innecesaria del módulo nuevo hacia variables internas de server.py.

## Archivos modificados en este sprint

- **Creado:** `axis_tradier.py` — 8 funciones de acceso Tradier (las 7 pedidas + `get_pct_otm`).
- **Modificado:** `server.py` — las 7 funciones pedidas ahora se importan desde `axis_tradier.py`. Ningún payload, URL, header, ni nombre público cambió.

## Último commit antes de este sprint

4299664 — AX-003 Configuration Baseline

## Rama

main

## Sprint activo

AX-004 — Tradier Access Baseline (este sprint)

## Próximo sprint sugerido

AX-005 — Channel Engine (documentar/extraer la lógica de canales bajistas CNF/RCB/PM40 y 4PASOS, según backlog original) — o alternativamente un AX-004b más pequeño para mover `get_estado_orden_tradier()` junto con el polling de posiciones, si se decide continuar profundizando en el módulo Tradier antes de pasar a canales.

## Riesgos abiertos

1. GLD sin canal bajista activo actualmente
2. Pendiente verificar visualmente que no hay alertas duplicadas tras v8.84
3. 4PASOS solo dentro de RCB
4. Tradier limita historial de 15min a ~40 días
5. Bug cosmético: chart marca "EN FORMACIÓN" en la última vela ya cerrada
6. Frontend aún calcula canales PM40/4PASOS en JavaScript
7. TWELVEDATA_KEY y FINNHUB_KEY siguen hardcodeados como strings literales en server.py (riesgo de seguridad menor, servicios externos no esenciales — ver AX-003)
8. **NUEVO AX-004:** `TRADIER_TOKEN`/`TRADIER_ACCOUNT`/`TRADIER_HEADERS` ahora existen DUPLICADOS en dos archivos (server.py y axis_tradier.py), ambos leyendo el mismo `os.environ`. Funcionalmente correcto y seguro (mismo valor siempre), pero es deuda técnica: si en el futuro se decide centralizar esto en axis_config.py, hay que actualizar ambos archivos a la vez.
9. **NUEVO AX-004:** `get_estado_orden_tradier()` quedó en server.py, acoplada a `loop_polling_posiciones()` — no se tocó por estar fuera del alcance pedido, pero es funcionalmente idéntica en estilo a las funciones que sí se movieron.

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Nunca codificar sin autorización explícita de Noel
- Verificar sintaxis y simular orden de ejecución real después de cualquier fix (lección del crash de import os, 06/25)
- axis_tradier.py no depende de Telegram, Portfolio, Derby, ni estado_dia/canal — mantenerlo así en futuros sprints para que siga siendo un módulo puro y testeable de forma aislada
