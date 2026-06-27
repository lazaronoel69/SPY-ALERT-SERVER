# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-014 (Extract Canal V2-V7) ejecutado — `evaluar_canal_v2_v7()` extraída de `evaluar_activo()`, conteniendo exactamente el bloque RCB/CNF — P2 dinámico + ruptura, con los 3 casos intactos (A: P2 dinámico silencioso, B: ruptura con alerta, C: apagado automático). Ubicada inmediatamente después de `evaluar_canal_v1()`. Sin tocar Canal V1, PM40, 4PASOS, 1VR/RPG/GNA/GBA, ni Reset Diario. Verificado con py_compile, AST, import real, y prueba funcional de los 3 casos.

## Cambio realizado en este sprint

`evaluar_canal_v2_v7(simbolo, ed, c, vela_actual, v_high, v_close, v_alcista, hora_vela)` — nueva función. Contiene exactamente el bloque original como un `if/elif/elif` intacto:
- **Caso A:** vela NO alcista, HIGH supera techo y es menor a P1 → actualiza P2 silenciosamente.
- **Caso B:** vela alcista estricta, CLOSE supera techo → si HIGH < P1: alerta de ruptura + canal roto/apagado; si HIGH >= P1: solo apagado sin alerta de ruptura.
- **Caso C:** HIGH >= P1 en cualquier vela (fuera del Caso B) → apagado automático sin alerta de ruptura.

Dentro de `evaluar_activo()`: `evaluar_canal_v2_v7(simbolo, ed, c, vela_actual, v_high, v_close, v_alcista, hora_vela)`. Ningún otro bloque fue modificado.

## Incidente menor durante verificación (resuelto sin intervención)

Tras el deploy, `curl /status` devolvió inicialmente `502 Application failed to respond`. Se investigó de inmediato (sin asumir que era el código) reintentando tras una breve espera — la segunda consulta confirmó el sistema completamente operativo, con las 8 posiciones reales, los 7 canales activos, y los 5 threads corriendo normalmente. El 502 fue una demora temporal normal de Railway durante el reinicio del proceso, no relacionada con el cambio de este sprint.

## Archivos modificados en este sprint

- **Modificado:** `server.py` — `evaluar_canal_v2_v7()` agregada, bloque inline reemplazado por la llamada.
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo).

## Último commit antes de este sprint

(commit de AX-013, ver historial de git)

## Rama

main

## Sprint activo

AX-014 — Extract Canal V2-V7 (este sprint)

## Próximo sprint sugerido

Según `05-STRATEGY-ENGINE-DESIGN.md`: con `evaluar_canal_v1()` y `evaluar_canal_v2_v7()` ya extraídas, el motor de canales bajistas está completo a nivel de evaluación. Los próximos candidatos de mayor valor son PM40 (sección 2.6) y 4PASOS (sección 2.7) — ambos marcados como riesgo alto y requieren diseñar primero una sub-división (por ejemplo, PM40-V1 vs PM40-V2-V7 como funciones separadas) antes de extraer, dado el mayor estado interno de ambas estrategias.

## Riesgos abiertos

(Ver lista completa en `04-ARCHITECTURE-AUDIT.md` sección 6 y `05-STRATEGY-ENGINE-DESIGN.md` sección 4. Sin riesgos nuevos críticos de este sprint.)

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Leer `05-STRATEGY-ENGINE-DESIGN.md` antes de cualquier sub-sprint de extracción
- Nunca codificar sin autorización explícita de Noel
- Extraer bloques directamente del archivo real con Python, nunca transcribir a mano
- Verificar `ast.parse()` del resultado completo antes de escribir el archivo
- Mockear explícitamente `calcular_techo_canal()`/`calcular_piso_mitad_canal()` en las pruebas de cualquier función que las use
- Si `/status` devuelve 502 inmediatamente después de un deploy, esperar y reintentar antes de asumir que el código falló — puede ser una demora normal de Railway al reiniciar el proceso
- Validar cada sub-sprint en producción durante al menos un día de mercado completo antes de proceder al siguiente
