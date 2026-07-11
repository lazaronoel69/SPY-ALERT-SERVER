# AX-TRACK-002 — Active Position Tracking

## Objetivo único

Medir automáticamente el comportamiento de cada opción activa desde su
entrada hasta el cierre, sin modificar la lógica de las estrategias ni tomar
nuevas decisiones de trading.

## Fuente y frecuencia

- Fuente: bid vigente de la opción en Tradier sandbox.
- Frecuencia: cada cinco minutos durante el horario operativo existente.
- Integración: `loop_polling_posiciones()`; no se crea un thread adicional.

## Datos por snapshot

- Timestamp EST.
- Bid de la opción.
- P&L porcentual y en dólares.
- Minutos desde la entrada.

## Métricas acumuladas

- `mfe_pct`: Maximum Favorable Excursion, mejor P&L observado.
- `mae_pct`: Maximum Adverse Excursion, peor P&L observado.
- `pl_pct_actual` y `pl_usd_actual`.
- `minutos_abierta`.
- `ts_ultimo_seguimiento`.
- `seguimiento`: serie cronológica completa de snapshots.

Las mismas métricas se copian al expediente identificado por `alert_id`. Al
cerrarse la posición, MFE, MAE, duración y resultado final permanecen en el
histórico de la posición y de la alerta.

## Reglas

1. Un bid ausente o cero no se convierte artificialmente en una pérdida.
2. El seguimiento nunca dispara, cancela ni cierra operaciones.
3. El polling GTC y vencimiento conserva su comportamiento existente.
4. Posiciones antiguas sin `alert_id` continúan funcionando.
5. No se modifica ninguna condición de estrategia.

## Criterios de aceptación

- Un polling válido agrega exactamente un snapshot a la posición.
- P&L porcentual y en dólares usan bid, entrada y número de contratos.
- MFE nunca disminuye y MAE nunca aumenta.
- El mismo estado aparece en el expediente de la alerta.
- Los datos sobreviven reinicios mediante `axis_portfolio.json` y
  `axis_alertas.json`.
