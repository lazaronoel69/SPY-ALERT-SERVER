# AX-TRACK-AUDIT-006 — Reconciliación semanal

**Corte lógico:** 2026-08-28 16:57 EDT
**Sesiones incluidas:** 2026-08-24 a 2026-08-28 (solo mercado completo)
**Base incremental:** AX-TRACK-AUDIT-005, corte 2026-08-22 10:15 EDT
**Fuentes verificadas:** `/version`, `/status`, `/alerts/data` y `/portfolio/data` autenticadas; producción v9.10, commit `c0569cf`.

## Resultado

- **55 resultados terminales nuevos:** 19 `CLOSED` y 36 `CANCELLED`.
- Los 19 cierres suman **-$5,456**; cuatro fueron ganadores (21.1%). P&L
  porcentual promedio: **-46.85%**; MFE promedio: **79.57%**; MAE promedio:
  **-83.47%**; duración mediana: **11,834 min**.
- Motivo de cierre: 18 por `VENCIMIENTO` y uno por `GTC`. Las cancelaciones se
  excluyen de la tasa de acierto.

## Cancelaciones y cadenas

| Resultado | Casos | Lectura |
|---|---:|---|
| `ORDER_EXPIRED` | 19 | Alertas no decididas dentro de su ventana. |
| `THESIS_COUNTERSIGNAL_SUPPRESSED` | 16 | Contraseñales bloqueadas por una tesis activa. |
| `NO_OPTION_AVAILABLE` | 1 | Sin contrato elegible para MU. |

- La cohorte de cierres contiene nueve cadenas CHAIN-001: nueve matrices y diez
  confirmaciones. Las contraseñales permanecen separadas de las operaciones.
- Las 36 cancelaciones no ejecutaron posición; por ello no alteran la
  trazabilidad ni la separación de cadenas de los 19 cierres.

## Integridad y excepciones

- Los 19 cierres están vinculados a `alert_id` y conservan vencimiento, MFE,
  MAE y duración; no hay campos métricos faltantes ni cadenas cerradas sin raíz.
- Al corte, las cinco posiciones abiertas son `CHAIN-001`, con `alert_id`, orden
  Tradier y GTC confirmada; no hay abiertas vencidas ni sin vínculo.
- La única excepción terminal operativa es `NO_OPTION_AVAILABLE` de MU; quedó
  como cancelación y no como posición.

## Conclusión de tuning

Este corte es observacional. No se recomienda modificar estrategias ni
parámetros: los cierres están concentrados en vencimientos y la cohorte
CHAIN-001 aún debe acumular más sesiones para análisis separado de matriz y
confirmación.

El detalle compacto de los 55 terminales está en
`data/2026-08-29-AX-TRACK-AUDIT-006.csv`.
