# AX-FIX-EXEC-001 — Integridad de ejecución Tradier

## Objetivo

Evitar que AXIS registre una posición local sin confirmación de compra de
Tradier y separar explícitamente la compra real de la colocación del GTC.

## Causa raíz

El webhook llamaba `registrar_posicion()` aunque la ejecución devolviera error.
Además, el cliente Tradier devolvía éxito tras cualquier respuesta JSON, aun si
la API no incluía `order.id` o respondía con error HTTP.

## Invariantes v8.97

1. La compra debe responder HTTP 2xx, incluir `order.id` y no estar rechazada.
2. Sin esa confirmación, la alerta queda `CANCELLED` y no existe posición.
3. Si la compra fue confirmada pero el GTC no, la posición sí se conserva con
   `gtc_confirmada=false` y evento `GTC_SUBMISSION_FAILED`.
4. Los registros del incidente documentado desde 2026-08-03 sin `alert_id` ni
   `tradier_orden_id` se anulan con `integridad_ejecucion=NO_CONFIRMADA` y
   `excluida_metricas=true`; nunca se borran ni cuentan como P&L o resultado de
   estrategia. Registros legacy ambiguos permanecen intactos.

## Reconciliación posterior al despliegue

`POST /portfolio/reconciliar_ejecuciones` es dry-run por defecto.
Solo `{"confirmar": true}` realiza la anulación idempotente. Al corte previo
al despliegue hay cuatro posiciones abiertas candidatas (2026-08-05) y dos
registros históricos ya vencidos (2026-08-03).

## Resultado en producción — 2026-08-11 16:41 EST

- v8.97, commit `35deaff`, cinco hilos vivos y mercado cerrado.
- Cuatro abiertas fantasma anuladas: AAPL, AMZN, GOOG y META del 2026-08-05.
- Dos cierres del 2026-08-03 marcados como no confirmados y excluidos de
  métricas; las 25 posiciones abiertas restantes tienen alerta e ID Tradier.
- La repetición del dry-run no encontró candidatos. Un registro legacy de AMZN
  (2026-06-12) se preservó por falta de evidencia suficiente para clasificarlo.

## Validación local

- Matriz simulada: HTTP rechazado, respuesta sin ID, compra confirmada con GTC
  rechazado y compra+GTC confirmados.
- Matriz de Portfolio: dry-run, confirmación, preservación de órdenes reales y
  exclusión de métricas.
- AST de módulos y `git diff --check`.
