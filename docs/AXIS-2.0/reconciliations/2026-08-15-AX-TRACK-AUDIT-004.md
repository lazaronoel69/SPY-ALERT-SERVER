# AXIS 2.0 — Reconciliación semanal incremental

**ID:** AX-TRACK-AUDIT-004
**Corte técnico:** 2026-08-15 15:54 EDT
**Sesiones completas incluidas:** 2026-08-08, 2026-08-10 a 2026-08-14
**Línea base:** AX-TRACK-AUDIT-003 (corte 2026-08-08 11:38 EDT)
**Producción verificada:** v9.06, commit `772e207`, Railway `OK`

## Resultado

**PASS operativo con dos excepciones de datos para seguimiento.** Railway estaba
disponible, mercado cerrado, siete hilos activos y las diez cachés de velas
cerraron el 2026-08-14 en estado `OK`. No se realizaron mutaciones de
producción.

| Área | Resultado |
|---|---:|
| Alertas acumuladas | 216 (7 ACTIVE, 108 CLOSED, 98 CANCELLED, 3 NOTIFIED) |
| Alertas generadas en el período | 43 |
| Resultados terminales nuevos | 56 (24 CLOSED, 32 CANCELLED) |
| Posiciones abiertas | 7; 7/7 con `alert_id`, orden Tradier y GTC |
| Vencidas abiertas | 0 |
| Cierres con ficha de Portfolio disponible | 20/24 |

El número de terminales supera las alertas nuevas porque 13 expedientes
generados antes del período alcanzaron su desenlace esta semana.

## Cierres y cancelaciones

De los 20 cierres con ficha completa: 3 alcanzaron GTC y 17 vencieron. El P&L
promedio fue **-60.79%** (mediana **-99.70%**), MFE promedio **+30.34%**, MAE
promedio **-88.45%** y duración mediana **10,455 min**. Hubo 4 cierres
positivos y 16 negativos. Son observaciones incrementales, no evidencia
suficiente para cambiar reglas ni objetivos GTC.

Las 32 cancelaciones se clasifican así: 15 `ORDER_EXPIRED`, 9
`TRADIER_EXECUTION_FAILED`, 4 `THESIS_COUNTERSIGNAL_SUPPRESSED`, 3
`THESIS_LEGACY_MIXED_SUPPRESSED` y 1 `NO_OPTION_AVAILABLE`. Las siete
supresiones de tesis del 2026-08-14 son comportamiento esperado del bloqueo
direccional: no abrieron posiciones contradictorias.

## Integridad y excepciones

- **Vínculos:** las siete posiciones abiertas están completas y no hay
  posiciones abiertas vencidas ni huérfanas.
- **Métricas de cierre:** `/portfolio/data` expone las últimas 20 fichas de
  historial. Cuatro alertas marcadas `CLOSED` el 2026-08-10/11 no estaban en
  esa ventana, por lo que su MFE, MAE, duración y motivo quedan en blanco en
  el CSV. Es una limitación de visibilidad del endpoint, no una posición
  abierta ni una métrica inventada.
- **Ejecución:** los nueve `TRADIER_EXECUTION_FAILED` se mantuvieron como
  cancelaciones sin posición; esta reconciliación no detectó órdenes locales
  huérfanas.

## Artefacto de resultados

El CSV contiene exclusivamente los 56 resultados terminales incrementales y
omite secretos, IDs de Telegram y snapshots.

- [`2026-08-15-AX-TRACK-AUDIT-004.csv`](data/2026-08-15-AX-TRACK-AUDIT-004.csv)

## Conclusión

La reconciliación formal vuelve a quedar documentada en el repositorio. La
automatización ahora tiene tres ventanas de recuperación cada sábado y es
idempotente: no duplicará el reporte si el corte semanal ya existe. La
prioridad de seguimiento es conservar la trazabilidad completa de los cuatro
cierres fuera de la ventana de 20 registros antes de usarlos para tuning.
