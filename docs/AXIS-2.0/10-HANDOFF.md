# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-016 (Extract PM40 V2-V7) ejecutado — `evaluar_pm40_v2_v7()` extraída de `evaluar_activo()`, conteniendo exactamente el bloque PM40 en V2-V7 (actualización de P1 si rompe, maduración tras 3 velas, fijación de P2, comparación contra techo proyectado vía slope, ruptura con alerta CALL, o actualización/invalidación de P2 si no rompe). Sin tocar PM40 V1, 4PASOS, Canal V2-V7 (aún revertido desde AX-014), 1VR/RPG/GNA/GBA, ni Reset Diario. Verificado con py_compile, AST, import real, prueba funcional (3 escenarios), logs de Railway, y 2 chequeos de `/status` espaciados 2 minutos.

## Cambio realizado en este sprint

`evaluar_pm40_v2_v7(simbolo, ed, c, v_high, v_close, v_alcista, hora_vela)` — nueva función. Contiene exactamente el bloque original: incrementa el índice de vela, actualiza P1 si el high lo supera (reiniciando todo el estado), suma velas bajo P1 hacia la maduración, fija P2 cuando hay distancia≥4 desde P1, calcula el techo proyectado (slope) una vez hay P2, dispara alerta CALL si rompe con vela alcista y `hora_vela > 9`, o actualiza/invalida P2 según corresponda si no rompe.

Dentro de `evaluar_activo()`: `evaluar_pm40_v2_v7(simbolo, ed, c, v_high, v_close, v_alcista, hora_vela)`. Ningún otro bloque fue modificado.

## Nota de testing (error propio detectado y corregido)

Durante la prueba funcional del "Caso 2" (ruptura con alerta), el primer intento usó un `v_high` mayor al propio P1, lo cual activa la rama de reinicio de P1 (comportamiento correcto y esperado), no la rama de comparación contra el techo proyectado — esto no fue un bug de la extracción, sino un valor de prueba mal elegido. Se corrigió usando un `v_high` entre P1 y el techo calculado, confirmando el disparo correcto. Documentado como recordatorio: al diseñar casos de prueba para PM40, verificar primero contra cuál rama (`v_high >= P1` vs. comparación con techo) caerá el valor elegido.

## Incidente menor de terminal (sin relación con el código)

Durante la verificación de este sprint, un comando con comillas simples anidadas dentro de comillas dobles (un comentario tipo `'CASO...'`) causó que la terminal de Noel entrara en modo `dquote>` (esperando cierre de comillas). Se resolvió con Ctrl+C y reformulando el comando con heredoc (`python3 << 'EOF' ... EOF'`), que evita el problema de anidación de comillas. Recomendación para sprints futuros: preferir heredocs sobre `python3 -c "..."` cuando el código de prueba contenga comillas simples dentro de strings con apóstrofes o comentarios complejos.

## Archivos modificados en este sprint

- **Modificado:** `server.py` — `evaluar_pm40_v2_v7()` agregada, bloque inline reemplazado por la llamada.
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo).

## Último commit antes de este sprint

1370134 — AX-015 Extract PM40 V1

## Rama

main

## Sprint activo

AX-016 — Extract PM40 V2-V7 (este sprint)

## Próximo sprint sugerido

Con PM40 V1 y V2-V7 ya extraídas, el motor PM40 está completo. Según `05-STRATEGY-ENGINE-DESIGN.md`: considerar **reintentar AX-014** (Canal V2-V7) con la verificación reforzada ya validada en AX-015 y AX-016, o avanzar con 4PASOS (sección 2.7 del diseño) — el componente de mayor estado interno y riesgo restante en la lista original.

## Riesgos abiertos

(Ver lista completa en `04-ARCHITECTURE-AUDIT.md` sección 6, `05-STRATEGY-ENGINE-DESIGN.md` sección 4, y `06-AX014-POSTMORTEM.md`. Sin riesgos nuevos críticos de este sprint.)

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Leer `05-STRATEGY-ENGINE-DESIGN.md` y `06-AX014-POSTMORTEM.md` antes de cualquier sub-sprint de extracción
- Nunca codificar sin autorización explícita de Noel
- Extraer bloques directamente del archivo real con Python, nunca transcribir a mano
- Verificar `ast.parse()` del resultado completo antes de escribir el archivo
- **Preferir heredocs (`python3 << 'EOF' ... EOF`) sobre `python3 -c "..."` para pruebas con comillas anidadas** — evita el modo `dquote>` que congela la terminal
- Al probar PM40, verificar contra cuál rama caerá el valor de `v_high` elegido (reinicio de P1 vs. comparación con techo) antes de asumir el resultado esperado
- Tras cada deploy: revisar logs de Railway con `railway logs --tail 200`, y verificar `/status` al menos 2 veces espaciadas varios minutos
