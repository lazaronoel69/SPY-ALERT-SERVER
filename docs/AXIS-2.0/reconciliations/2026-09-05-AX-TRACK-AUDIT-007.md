# AX-TRACK-AUDIT-007 — Reconciliación semanal

**Corte lógico:** 2026-09-04 16:17 EDT
**Sesiones incluidas:** 2026-08-31 a 2026-09-04 (solo mercado completo)
**Base incremental:** AX-TRACK-AUDIT-006, corte 2026-08-28 16:57 EDT
**Fuentes verificadas:** `/version`, `/status`, `/alerts/data` y `/portfolio/data` autenticadas; producción v9.10, commit `c162c49`.

## Resultado

- **42 resultados terminales nuevos:** 6 `CLOSED` y 36 `CANCELLED`.
- Los seis cierres suman **-$271**; uno fue ganador (16.7%). P&L porcentual
  promedio: **-59.79%**; MFE promedio: **51.90%**; MAE promedio: **-86.32%**;
  duración mediana: **10,445.5 min**.
- Cinco cierres fueron por `vencimiento` y uno por `gtc`. Las cancelaciones se
  excluyen de la tasa de acierto.

## Cancelaciones y cadenas

| Resultado | Casos | Lectura |
|---|---:|---|
| `ORDER_EXPIRED` | 27 | Alertas no decididas dentro de su ventana. |
| `THESIS_COUNTERSIGNAL_SUPPRESSED` | 8 | Contraseñales bloqueadas por una tesis activa. |
| `TRADIER_REVIEW_EXPIRED` | 1 | Revisión de ejecución no confirmada que venció sin reintento. |

- Los seis cierres pertenecen a `CHAIN-001`: dos matrices y cuatro
  confirmaciones; las seis raíces de cadena existen y coinciden con su cadena.
- Quince cancelaciones conservan contexto de `CHAIN-001`; ninguna de las 36
  cancelaciones abrió una posición.

## Integridad y excepciones

- Los seis `alert_id` de cierre coinciden exactamente con Portfolio y conservan
  vencimiento, MFE, MAE y duración; no hay métricas, vínculos ni raíces de
  cadena faltantes.
- La única excepción terminal fue una alerta GLD `1VR` en
  `TRADIER_REVIEW_EXPIRED`, tras una compra no confirmada (HTTP 500); no se
  registró posición.
- Al corte hay una posición abierta `CHAIN-001` (SPCX), con `alert_id`, orden
  Tradier y GTC confirmada; vence el 2026-09-11, por lo que no está vencida.

## Conclusión de tuning

Este corte sigue siendo observacional. No se recomienda modificar estrategias
ni parámetros: cinco de seis cierres terminaron por vencimiento y la evidencia
CHAIN-001 continúa siendo insuficiente para tuning separado de matrices y
confirmaciones.

El detalle compacto de los 42 terminales está en
`data/2026-09-05-AX-TRACK-AUDIT-007.csv`.
