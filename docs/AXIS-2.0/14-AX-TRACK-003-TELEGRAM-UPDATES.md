# AX-TRACK-003 — Telegram Operational Updates

## Regla de comunicación

Telegram es el canal operativo oficial para toda información que el propietario
de AXIS deba conocer. Dashboards y endpoints son herramientas internas de
diagnóstico, no sustituyen las notificaciones.

## Notificaciones

- La alerta inicial incluye `Alert ID`.
- Se notifican una sola vez los hitos de P&L: -25%, -50%, -75%, +25%, +50%,
  +75% y +100%.
- Si se cruzan varios hitos en una consulta, se envía solo el más severo y los
  demás se marcan como cubiertos para evitar spam.
- Tres consultas consecutivas sin bid producen un aviso de interrupción.
- El primer bid posterior produce un aviso de restablecimiento.
- El cierre incluye P&L, MFE, MAE, duración, estrategia y Alert ID.
- El resumen diario incluye el estado completo de cada posición abierta.

## Persistencia anti-spam

Los hitos enviados, fallos consecutivos y estado de notificación se guardan en
`axis_portfolio.json`; un reinicio no vuelve a enviar hitos ya comunicados.

## Alcance

No modifica estrategias, entradas, salidas, GTC ni decisiones de trading. El
seguimiento continúa cada cinco minutos, pero Telegram recibe únicamente
eventos relevantes y el resumen diario.
