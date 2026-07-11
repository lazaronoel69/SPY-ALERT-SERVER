# AX-FIX-EXP-001 — Expiration Reconciliation

## Problema

Las posiciones se cerraban solo cuando `expiration < hoy` y únicamente dentro
del polling de un día de mercado. Un contrato que vencía el viernes podía
permanecer abierto en AXIS hasta el lunes.

## Corrección

- Un contrato vence operativamente a las 16:15 EST de su fecha de expiración.
- El polling reconcilia vencimientos antes de comprobar horario o día hábil.
- El arranque reconcilia inmediatamente después de cargar el portfolio.
- El cierre usa el bid vigente cuando existe; si no, usa el último bid
  persistido. Solo usa cero cuando no existe ningún precio observable.

## Alcance

No cambia señales, parámetros, condiciones de estrategia, órdenes GTC ni la
selección de opciones. Corrige exclusivamente el estado de posiciones vencidas.

## Criterios de aceptación

1. Una posición no cierra antes de las 16:15 EST de su fecha final.
2. Cierra desde las 16:15 EST del mismo día.
3. Una posición de fecha anterior cierra incluso en fin de semana o al arrancar.
4. Reiniciar AXIS no deja vencimientos antiguos como activos.
5. Se conserva el mejor precio de cierre observable.
