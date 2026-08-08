# AX-TRACK-AUDIT-003 — Reconciliación semanal incremental

**Fecha de corte técnico:** 2026-08-08 11:38 EST
**Sesiones de mercado incluidas:** 2026-08-05 → 2026-08-07 (tres sesiones completas)
**Línea base:** AX-TRACK-AUDIT-002, corte 2026-08-05 09:37 EST
**Producción:** AXIS v8.94, commit `0766456`; `/version`, `/status` y `/alerts/data` disponibles. Mercado cerrado al corte.

## Resultado ejecutivo

**RECONCILIACIÓN COMPLETA CON EXCEPCIÓN P1 AMPLIADA**

| Control | Resultado |
|---|---:|
| Alertas acumuladas | 173 |
| Alertas generadas en las sesiones incluidas | 27 |
| Alertas ACTIVE / CLOSED / CANCELLED | 23 / 84 / 66 |
| Resultados terminales nuevos | 29 |
| Nuevos cierres / cancelaciones | 20 / 9 |
| Cierres por GTC / vencimiento | 3 / 17 |
| Posiciones abiertas | 29 |
| ACTIVE sin posición | 0 |
| Posiciones abiertas vinculadas por `alert_id` | 23 |
| Posiciones abiertas sin `alert_id` | 6 |
| Cierres sin P&L, MFE, MAE o duración | 0 |
| Posiciones activas sin MFE, MAE o duración | 0 |
| Posiciones activas vencidas | 0 |

Las 27 alertas generadas en el período terminan en 17 ACTIVE, 1 CLOSED y 9
CANCELLED al corte. Los resultados terminales incluyen cierres de alertas
generadas antes del período que vencieron durante las tres sesiones incluidas.

## Resultados terminales nuevos

Los 20 cierres presentan P&L medio de **-65.21%**, MFE medio de **+50.80%**,
MAE medio de **-87.42%** y duración media de **10,206 minutos**. Diecisiete
cerraron por vencimiento; tres alcanzaron GTC. Las nueve cancelaciones son
cuatro `EXPIRED`, cuatro `EXECUTE` y una `DERBY`.

| Estrategia | Cierres | W-L | P&L medio | MFE medio | MAE medio | Duración media |
|---|---:|---:|---:|---:|---:|---:|
| 1VR | 15 | 0-15 | -99.08% | +35.77% | -99.76% | 11,605 min |
| CNF | 1 | 0-1 | -99.56% | +33.60% | -99.84% | 11,646 min |
| GBA | 1 | 1-0 | +178.16% | +236.18% | -3.75% | 2,805 min |
| GNA | 1 | 1-0 | +101.12% | +101.12% | -36.18% | 2,809 min |
| GNA+2 | 1 | 1-0 | +101.92% | +101.92% | -12.50% | 2,696 min |
| HED | 1 | 0-1 | -99.70% | +6.67% | -99.70% | 10,096 min |

## Integridad y excepciones

Las 23 alertas ACTIVE tienen una posición abierta correspondiente y ninguna
posición abierta está vencida. Se conservan las dos posiciones huérfanas ya
documentadas del 2026-08-03. Se agregan cuatro nuevas posiciones huérfanas,
coincidentes con alertas 1VR CANCELLED con decisión `EXECUTE` del 2026-08-05:
AAPL, AMZN, GOOG y META. En conjunto son seis posiciones abiertas sin
`alert_id`; las cuatro nuevas deben tratarse como ampliación de la excepción
P1 de ejecución, no como resultados aptos para tuning.

No se alteraron estrategias, parámetros, configuración ni producción.

## Evidencia

El CSV contiene exclusivamente los 29 resultados que alcanzaron estado terminal
después del corte anterior; omite secretos, identificadores de Telegram y
snapshots de seguimiento.

[`data/2026-08-08-AX-TRACK-AUDIT-003.csv`](data/2026-08-08-AX-TRACK-AUDIT-003.csv)
