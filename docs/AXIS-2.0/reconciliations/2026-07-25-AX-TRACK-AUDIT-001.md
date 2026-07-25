# AX-TRACK-AUDIT-001 — Primera reconciliación

**Fecha de corte:** 2026-07-25 12:15 EST

**Período:** 2026-07-13 → 2026-07-24

**Producción:** AXIS v8.94, commit `33d8587`

**Alcance:** consistencia interna entre expedientes de alertas, posiciones y
métricas persistidas. No constituye reconciliación independiente contra un
estado de cuenta del broker.

## Resultado ejecutivo

**RECONCILIACIÓN INTERNA APROBADA**

| Control | Resultado |
|---|---:|
| Alertas registradas | 81 |
| Posiciones/alertas activas | 26 / 26 |
| Alertas cerradas con resultado | 25 / 25 |
| Alertas canceladas | 30 |
| Alertas activas sin posición | 0 |
| Posiciones sin alerta | 0 |
| Alert IDs duplicados en posiciones | 0 |
| Posiciones activas sin MFE/MAE/último seguimiento | 0 |
| Cierres sin P&L, motivo o timestamp | 0 |
| Canceladas con posición vinculada | 0 |
| Posiciones vencidas todavía activas | 0 |

Los 81 expedientes son internamente coherentes al corte. Las 26 posiciones
abiertas no son una inconsistencia de datos: cada una tiene una alerta ACTIVE,
un identificador único y métricas de seguimiento.

## Muestra por estrategia

| Estrategia | Total | Cerradas | Activas | Canceladas | W-L cerradas | P&L medio cerrado |
|---|---:|---:|---:|---:|---:|---:|
| 1VR | 50 | 14 | 20 | 16 | 12-2 | +79.39% |
| GBA+2 | 12 | 4 | 3 | 5 | 1-3 | -49.16% |
| RPG | 9 | 2 | 2 | 5 | 2-0 | +113.35% |
| GNA+2 | 3 | 2 | 0 | 1 | 0-2 | -99.70% |
| RPG+ | 3 | 2 | 0 | 1 | 1-1 | +5.88% |
| GBA | 2 | 1 | 0 | 1 | 1-0 | +100.00% |
| GNA | 2 | 0 | 1 | 1 | 0-0 | — |

## Lectura preliminar

- La infraestructura de AX-TRACK produce una base consistente y reutilizable.
- 1VR domina la muestra: 50 de 81 alertas y 14 de 25 cierres.
- Los resultados cerrados de 1VR son favorables, pero su MAE medio aproximado
  de -49.65% muestra recorridos adversos amplios antes del cierre.
- GBA+2 y GNA+2 muestran resultados negativos en la muestra cerrada, pero sus
  tamaños muestrales son demasiado pequeños para cambiar reglas.
- La muestra permite análisis exploratorio y control operativo. No permite aún
  tuning permanente de estrategias.

## Decisión

1. Conservar este reporte como línea base oficial.
2. Continuar acumulando operaciones cerradas.
3. Realizar reconciliaciones incrementales; no reconstruir este período salvo
   que se detecte una corrección de datos.
4. No modificar estrategias usando solamente esta primera muestra.
5. Antes del tuning, evaluar también concentración, MFE/MAE, duración,
   vencimiento y motivo de cierre por estrategia.

## Evidencia

Dataset compacto:
[`data/2026-07-25-AX-TRACK-AUDIT-001.csv`](data/2026-07-25-AX-TRACK-AUDIT-001.csv)

El CSV contiene una fila por alerta y solo los campos necesarios para análisis
posterior. No incluye tokens, cuentas, Telegram IDs, historial completo de
snapshots ni otros datos sensibles o redundantes.
