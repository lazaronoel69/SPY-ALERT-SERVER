# AX-TRACK-AUDIT-005 — Reconciliación semanal (backfill)

**Corte lógico:** 2026-08-22 10:15 EDT
**Sesiones incluidas:** 2026-08-17 a 2026-08-21 (solo mercado completo)
**Base incremental:** AX-TRACK-AUDIT-004, corte 2026-08-15 15:54 EDT
**Ejecución del backfill:** 2026-08-26; no se estimaron datos fuera del intervalo.

## Resultado

- **38 resultados terminales nuevos:** 10 `CLOSED` y 28 `CANCELLED`.
- Los 10 cierres conservan `alert_id`, instrumento, vencimiento y métricas de
  MFE, MAE y duración. Cuatro fueron ganadores (40.0%).
- P&L de cierres: **$1,951** agregado; P&L porcentual promedio **-19.95%**.
  El contraste se explica por el distinto valor nocional de los contratos; no
  debe usarse como una métrica ponderada de estrategia.
- MFE promedio: **32.94%**; MAE promedio: **-57.80%**; duración mediana:
  **10,093 min**.

## Cancelaciones y tesis

| Resultado | Casos | Lectura |
|---|---:|---|
| `THESIS_COUNTERSIGNAL_SUPPRESSED` | 11 | CHAIN-001 bloqueó la dirección contraria por activo. |
| `ORDER_EXPIRED` | 8 | Alerta no decidida dentro de su ventana. |
| `TRADIER_REVIEW_EXPIRED` | 4 | Revisión de Tradier vencida sin compra. |
| `NO_OPTION_AVAILABLE` | 2 | Sin contrato elegible. |
| `NO_DERBY_LANE_AVAILABLE` | 3 | Sin carril disponible en Derby. |

La supresión de contraseñales quedó registrada como cancelación auditable y se
mantiene fuera de la tasa de acierto. Las confirmaciones y matrices de
CHAIN-001 siguen siendo cohortes separables para análisis posterior.

## Integridad y excepciones

- Los 10 cierres del período están vinculados a su `alert_id`.
- Las métricas MFE/MAE/duración están presentes en los 10 cierres del CSV.
- No se incluyeron secretos, IDs de Telegram ni snapshots completos.
- La ejecución programada original del 22 falló en preflight autenticado; este
  backfill conserva el corte y no inventa evidencia. La corrección del job se
  validó el 26: `/version`, `/status`, `/alerts/data` y `/portfolio/data`
  respondieron 200 con el encabezado administrativo local, sin exponerlo.

## Conclusión de tuning

No se recomienda alterar estrategias ni parámetros con este corte. El valor
principal es ampliar la cohorte trazable y confirmar el comportamiento de
CHAIN-001; la muestra continúa siendo observacional y heterogénea por activo.

El detalle compacto de los 38 terminales está en
`data/2026-08-22-AX-TRACK-AUDIT-005.csv`.
