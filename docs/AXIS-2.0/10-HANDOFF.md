# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-013 (Extract Canal V1) ejecutado — `evaluar_canal_v1()` extraída de `evaluar_activo()`, conteniendo exactamente el bloque de Canal V1 — P2 dinámico especial. Ubicada inmediatamente después de `evaluar_1vr_normal()`. Sin tocar PM40, 4PASOS, Canal V2-V7, RPG/GNA/GBA/1VR, ni Reset Diario. Verificado con py_compile, AST, import real, y prueba funcional (canal activo actualiza P2 / canal apagado no hace nada).

## Cambio realizado en este sprint

`evaluar_canal_v1(simbolo, c, vela_actual, v_high)` — nueva función. Contiene exactamente el bloque original: si el canal está activo y V1 (cualquier tipo de vela) rompe el techo proyectado con un high menor a P1, actualiza `p2_actual_high`, `p2["high"/"fecha"/"hora_est"]`, `p2_actual_ts`, llama a `guardar_canales()`, y emite el mismo print exacto ("P2 dinamico (V1)...").

Dentro de `evaluar_activo()`: `evaluar_canal_v1(simbolo, c, vela_actual, v_high)`. Ningún otro bloque fue modificado.

## Nota sobre la verificación funcional de este sprint

Durante la prueba funcional sobre el archivo real (sin mocks), `evaluar_canal_v1()` no actualizó P2 con los datos de prueba iniciales — esto **no fue un bug de la extracción**, sino que la función real `calcular_techo_canal()` (no mockeada) requiere un canal con P1/P2 y fechas reales y consistentes para calcular un techo válido; con datos de prueba mínimos devolvía un valor que no cumplía la condición. Al mockear `calcular_techo_canal()` con un valor de retorno fijo razonable, la prueba pasó exactamente como se esperaba. Documentado para que sprints futuros que dependan de `calcular_techo_canal()`/`calcular_piso_mitad_canal()` mockeen estas funciones explícitamente en sus pruebas, en vez de pasar datos de canal mínimos y esperar que el cálculo real funcione sin contexto completo.

## Archivos modificados en este sprint

- **Modificado:** `server.py` — `evaluar_canal_v1()` agregada, bloque inline reemplazado por la llamada.
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo).

## Último commit antes de este sprint

(commit de AX-012G, ver historial de git)

## Rama

main

## Sprint activo

AX-013 — Extract Canal V1 (este sprint)

## Próximo sprint sugerido

Según `05-STRATEGY-ENGINE-DESIGN.md` (sección 2.8): extraer **`evaluar_canal_v2_v7()`** — los 3 casos de ruptura (A: P2 dinámico silencioso, B: ruptura con alerta, C: apagado por HIGH≥P1) deben mantenerse como un bloque `if/elif/elif` intacto dentro de la función extraída. Mayor riesgo que este sprint por la cantidad de estado que modifica (canal y flags `rcb_fired`/`cnf_fired`).

## Riesgos abiertos

(Ver lista completa en `04-ARCHITECTURE-AUDIT.md` sección 6 y `05-STRATEGY-ENGINE-DESIGN.md` sección 4. Sin riesgos nuevos críticos de este sprint — solo la nota de testing documentada arriba.)

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Leer `05-STRATEGY-ENGINE-DESIGN.md` antes de cualquier sub-sprint de extracción
- Nunca codificar sin autorización explícita de Noel
- Extraer bloques directamente del archivo real con Python, nunca transcribir a mano
- Verificar `ast.parse()` del resultado completo antes de escribir el archivo
- **Al probar funciones que dependen de `calcular_techo_canal()`/`calcular_piso_mitad_canal()`, mockear estas funciones explícitamente** con un valor de retorno fijo razonable, en vez de pasar datos de canal mínimos esperando que el cálculo real funcione sin contexto completo (P1/P2/fechas consistentes)
- Validar cada sub-sprint en producción durante al menos un día de mercado completo antes de proceder al siguiente
