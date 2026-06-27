# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. **AX-014 (Extract Canal V2-V7) FUE REVERTIDO** por 502 persistente en producción tras el deploy original. El rollback restauró la versión anterior (estado de AX-013) y producción confirmó respuesta normal con las 8 posiciones reales, 7 canales activos, y los 5 threads operativos.

## EMERGENCIA — Rollback AX-014

AX-014 revertido por 502 persistente en producción.

- Commit revertido: `ae0c2a6` (AX-014 Extract Canal V2-V7)
- Commit de revert: `d6a3859`
- Acción tomada: `git revert ae0c2a6 --no-edit`
- Verificación de producción tras el revert: `/status` responde `200 OK` con `"sistema":"AXIS Breakout Sentinel v8.84"`, 8 posiciones intactas, 7 canales activos (AAPL, AMZN, BA, GOOG, META, NVDA, SPY en RCB/CNF; GLD off), 5 threads corriendo (`monitor_loop`, `loop_v7_anticipada`, `loop_limpiar_ordenes`, `loop_polling_posiciones`).
- **NO se intentó diagnosticar ni arreglar la causa del 502 en este sprint** — eso queda para un sprint de investigación separado, según indica la regla explícita de la emergencia.
- **NO se tocó PM40 ni 4PASOS.**

## Cronología de los hechos

1. AX-014 se aplicó, comiteó (`ae0c2a6`), y se subió a producción.
2. La primera verificación de `/status` inmediatamente después del push devolvió `502 Application failed to respond`.
3. Una segunda verificación ~30 segundos después mostró el sistema respondiendo normalmente con `v8.84` y todos los datos intactos — se interpretó como una demora normal de Railway al reiniciar.
4. El handoff de AX-014 se cerró documentando esto como resuelto sin intervención.
5. **Sin embargo, Noel reportó que producción seguía en 502 después de ese punto** — la verificación anterior no fue representativa del estado sostenido real.
6. Se ejecutó el rollback de emergencia: `git revert ae0c2a6 --no-edit`, confirmado con `py_compile`, subido a producción.
7. Verificación post-rollback: `/status` responde correctamente y de forma sostenida.

## Archivos modificados en este sprint (emergencia)

- **Revertido:** `server.py` — vuelve al estado de AX-013 (sin `evaluar_canal_v2_v7()`, con el bloque RCB/CNF — P2 dinámico + ruptura de vuelta inline dentro de `evaluar_activo()`).
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo).

## Último commit antes de este sprint

60e2b6f — Update 10-HANDOFF.md (cierre original de AX-014, ahora revertido)

## Commit de este sprint

d6a3859 — Revert "AX-014 Extract Canal V2-V7"

## Rama

main

## Sprint activo

EMERGENCY — Rollback AX-014 (este sprint)

## Próximo sprint sugerido

**Investigar la causa raíz real del 502 sostenido antes de volver a intentar AX-014.** Hipótesis a verificar con evidencia real (logs de Railway), sin asumir ninguna como confirmada:
- Posible fuga de memoria o bucle infinito en algún punto no detectado por las pruebas locales (que usaban mocks, no el entorno real de Railway).
- Posible incompatibilidad entre `evaluar_canal_v2_v7()` y algo del entorno de producción que no se replica en las pruebas locales (variables de entorno, timing de threads reales vs. simulados).
- Revisar logs de Railway del período exacto en que ocurrió el 502 sostenido, no solo el momento puntual donde la verificación posterior pareció exitosa.

No reintentar AX-014 sin esa investigación — la verificación que se hizo (un solo curl exitoso) resultó ser insuficiente para confirmar estabilidad sostenida en producción real.

## Riesgos abiertos

(Ver lista completa en `04-ARCHITECTURE-AUDIT.md` sección 6 y `05-STRATEGY-ENGINE-DESIGN.md` sección 4. Riesgo crítico de este incidente:)

1. **NUEVO — CRÍTICO:** una sola verificación exitosa de `/status` inmediatamente después de un deploy **no es suficiente** para confirmar estabilidad sostenida — el 502 puede reaparecer o haber persistido de forma intermitente sin que una verificación puntual lo detecte. A partir de ahora, la verificación de producción después de cualquier deploy debe incluir múltiples chequeos espaciados en el tiempo (varios minutos, no solo 15-30 segundos), y verificar explícitamente con Noel si el problema persiste desde su propia experiencia directa con el sistema, no solo confiar en el resultado de un curl puntual desde la terminal.
2. La causa raíz del 502 de AX-014 sigue sin confirmarse — `evaluar_canal_v2_v7()` puede tener un problema real no detectado por las pruebas locales con mocks.
3. Los riesgos generales de la descomposición documentados en AX-012A siguen aplicando para cualquier sprint futuro.

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- **NUNCA declarar un deploy estable basándose en una sola verificación de `/status`** — verificar varias veces espaciadas en el tiempo, y confirmar con el usuario si el problema persiste desde su experiencia real, antes de cerrar cualquier sprint como exitoso
- Nunca codificar sin autorización explícita de Noel
- Antes de reintentar AX-014, investigar los logs reales de Railway del incidente — no reconstruir la función desde cero sin entender qué falló
- Validar cada sub-sprint en producción durante al menos un día de mercado completo antes de proceder al siguiente — esta regla ya existía pero este incidente confirma su importancia real
