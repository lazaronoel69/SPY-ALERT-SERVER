# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-005 (Storage Baseline) ejecutado — funciones de persistencia JSON de bajo riesgo movidas a `axis_storage.py`, sin cambiar formato JSON, rutas, ni comportamiento. Verificado con py_compile y simulación de import real.

## Funciones movidas a axis_storage.py (AX-005)

1. `cargar_señales_historicas()`
2. `guardar_señales_historicas(data)`
3. `guardar_estado_dia(estado_dia)` — **cambio de firma controlado:** ahora recibe `estado_dia` como parámetro en vez de leerlo como variable global, porque axis_storage.py no debe depender de globals de server.py. server.py mantiene un wrapper `guardar_estado_dia()` sin argumentos (mismo nombre, misma firma pública) que llama internamente a la versión movida pasándole su propio global. Ninguna llamada existente en el resto de server.py se modificó.
4. `cargar_velas_local(simbolo)`
5. `guardar_velas_local(simbolo, data)`
6. `ruta_velas_local(simbolo)`

## Funciones NO movidas y razón (según regla explícita del sprint)

- **`guardar_ordenes()` / `cargar_ordenes()`** — dependen de la variable global `ordenes_pendientes` (dict en memoria con timestamps y reconstrucción de objetos datetime). Mover esto requeriría el mismo patrón de wrapper que `guardar_estado_dia`, pero el sprint las excluyó explícitamente para este paso.
- **`guardar_portfolio()` / `cargar_portfolio()`** — dependen de `_portfolio`, una variable global más compleja (posiciones, historial, derby con 4 caballos). Excluidas explícitamente.
- **`guardar_canales()` / `cargar_canales()`** — dependen de `canal[]` (dict por activo) y de `CANALES_DEFAULT`. Excluidas explícitamente.
- **`archivar_señales_dia(fecha)`** — depende de `estado_dia[]` (todos los activos) y de `ACTIVOS`. Excluida explícitamente. Es la función más reciente (v8.84) que guarda vela/hora exacta en el histórico — alto valor pero también mayor riesgo si se mueve sin cuidado.

## Archivos modificados en este sprint

- **Creado:** `axis_storage.py` — 6 funciones de persistencia JSON (5 puras + 1 con parámetro explícito).
- **Modificado:** `server.py` — las 6 funciones ahora se importan desde `axis_storage.py`. `guardar_estado_dia()` queda como wrapper de 2 líneas para preservar la firma pública original.

## Último commit antes de este sprint

52e2b01 — AX-004 Tradier Access Baseline

## Rama

main

## Sprint activo

AX-005 — Storage Baseline (este sprint)

## Próximo sprint sugerido

AX-006 — mover `guardar_ordenes`/`cargar_ordenes` usando el mismo patrón de wrapper que `guardar_estado_dia` (dependencia de `ordenes_pendientes`), como paso intermedio antes de abordar Portfolio/Derby y Canales, que son más complejos y de mayor riesgo.

## Riesgos abiertos

1. GLD sin canal bajista activo actualmente
2. Pendiente verificar visualmente que no hay alertas duplicadas tras v8.84
3. 4PASOS solo dentro de RCB
4. Tradier limita historial de 15min a ~40 días
5. Bug cosmético: chart marca "EN FORMACIÓN" en la última vela ya cerrada
6. Frontend aún calcula canales PM40/4PASOS en JavaScript
7. TWELVEDATA_KEY y FINNHUB_KEY siguen hardcodeados en server.py (riesgo de seguridad menor — ver AX-003)
8. `TRADIER_TOKEN`/`TRADIER_ACCOUNT`/`TRADIER_HEADERS` duplicados en server.py y axis_tradier.py (ver AX-004)
9. **NUEVO AX-005:** el patrón de wrapper usado en `guardar_estado_dia()` (función movida acepta parámetro, server.py mantiene wrapper sin argumentos) es ahora el patrón a seguir para `guardar_ordenes`/`guardar_portfolio`/`guardar_canales` en sprints futuros — documentado aquí para consistencia.
10. **NUEVO AX-005:** axis_storage.py no maneja la recuperación de tipos especiales (datetime, etc.) — las funciones movidas son JSON puro. Las funciones NO movidas (ordenes, portfolio, canales) sí tienen esa complejidad adicional, razón adicional por la que se excluyeron de este sprint.

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Nunca codificar sin autorización explícita de Noel
- Verificar sintaxis y simular orden de ejecución real después de cualquier fix (lección del crash de import os, 06/25)
- axis_storage.py es JSON puro — cualquier función que dependa de tipos complejos (datetime, objetos anidados con lógica) debe seguir el patrón de wrapper, no moverse directamente
