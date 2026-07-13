# AX-TRACK-003/004 — Seguimiento silencioso y cierre diario

## Regla de comunicación

El seguimiento de opciones continúa cada cinco minutos, pero sus resultados se
consolidan para evitar interrupciones durante la sesión. Telegram conserva las
alertas operativas de trading y recibe el reporte de seguimiento al cierre.

## Notificaciones

- La alerta inicial incluye `Alert ID`.
- Los hitos de P&L no generan mensajes durante la sesión.
- Los fallos y restablecimientos del seguimiento se registran en el expediente,
  sin enviar Telegram.
- El cierre incluye P&L, MFE, MAE, duración, estrategia y Alert ID.
- El resumen diario incluye el estado completo de cada posición abierta y de
  cada posición cerrada durante el día.

## Persistencia

Los snapshots, fallos consecutivos y estados de interrupción se guardan en
`axis_portfolio.json`. Los eventos de interrupción y recuperación también
quedan vinculados al expediente de la alerta.

## Alcance

No modifica estrategias, entradas, salidas, GTC ni decisiones de trading. El
seguimiento continúa cada cinco minutos en silencio y Telegram recibe el
reporte consolidado al cierre diario.
