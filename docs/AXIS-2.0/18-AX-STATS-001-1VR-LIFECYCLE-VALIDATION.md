# AX-STATS-001 — Validación de ciclo de vida 1VR

**Corte:** 2026-08-11 16:43 EST
**Fuente:** `/alerts/data`, `/analisis/data`, `/portfolio/data` y `/status` en
producción AXIS v8.97 (`35996b7`).

## Integridad de la cohorte

| Estado | Casos | Validación |
|---|---:|---|
| Alertas 1VR | 112 | Expediente persistente |
| CLOSED | 61 | 61/61 con posición vinculada |
| ACTIVE | 10 | 10/10 con posición e ID Tradier |
| CANCELLED | 41 | 33 expiradas, 2 sin opción, 6 fallos históricos de ejecución |

Los seis fallos de ejecución ya están marcados `excluida_metricas=true`; no
participan en resultados, P&L ni tuning. Las 25 posiciones abiertas actuales
de AXIS tienen alerta e ID Tradier.

## Resultados 1VR confirmados

| Métrica | Valor |
|---|---:|
| Ventana de cierres | 2026-07-13 a 2026-08-10 |
| Cierres | 61 |
| Ganadores / perdedores | 31 / 30 |
| Tasa de acierto | 50.8% |
| P&L % promedio | +19.5% |
| Ganador % promedio / mediano | +128.1% / +101.2% |
| Perdedor % promedio / mediano | -92.7% / -99.8% |
| MFE / MAE promedio | +87.3% / -66.1% |
| Duración promedio / mediana | 8,169 / 10,451 min |

Los motivos de cierre concuerdan con la mecánica: 31 GTC ganadores y 30
vencimientos perdedores. El retorno en dólares no se usa para decidir tuning,
porque depende de contratos y tamaño de cada operación.

## Lectura por activo

Las observaciones varían entre 4 y 11 cierres por activo: insuficiente para
reglas específicas. BA (0/5) y GLD (0/5) requieren seguimiento; META (4/4) y
AAPL (6/7) no justifican ampliar exposición aún. Las observaciones dentro de
un mismo día están correlacionadas por mercado, por lo que 61 operaciones no
equivalen a 61 experimentos independientes.

## Decisión

**No cambiar parámetros 1VR todavía.** La cohorte es suficiente para sostener
la telemetría y generar hipótesis, pero no para cambios permanentes: cubre 12
fechas de cierre y carece de ≥20 cierres por activo. Antes de AX-TUNE-002 se
requieren 30–40 sesiones de mercado completas y al menos 20 cierres por activo,
además de validar cualquier hipótesis contra el backtest proxy sin confundirlo
con P&L de opciones.
