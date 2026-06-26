# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-012D (Extract GBA Engine) ejecutado — `evaluar_gba()` extraída de `evaluar_activo()` con ambos bloques (activación V1 + disparo V2-V7) exactos, ubicada inmediatamente después de `evaluar_gna()` como pedía el sprint. Sin cambiar GNA, RPG, 1VR, PM40, 4PASOS, Canales, ni Reset Diario. Verificado con py_compile y prueba funcional en ambos escenarios con datos sintéticos.

## Cambio realizado en este sprint

`evaluar_gba(simbolo, ed, v_open, v_close, v_alcista, v7_ayer, v1_close, hora_vela, es_v1)` — nueva función, ubicada justo después de `evaluar_gna()` y antes de `evaluar_activo()`. Contiene **exactamente** los 2 bloques de GBA que existían inline:
- `es_v1=True`: bloque de activación (gap_baja >= 0.1%, requiere vela verde) — idéntico al original, mismo print exacto.
- `es_v1=False`: bloque de disparo (v_alcista y v_close > v1_close) — idéntico al original, mismo flujo de `guardar_estado_dia()` + `enviar_senal_con_botones()` con el mismo texto exacto ("GAP BAJISTA ALZA").

Dentro de `evaluar_activo()`, ambos bloques GBA fueron reemplazados por una llamada cada uno:
- En V1: `evaluar_gba(simbolo, ed, v_open, v_close, v_alcista, v7_ayer, None, hora_vela, True)`
- En V2-V7: `evaluar_gba(simbolo, ed, v_open, v_close, v_alcista, v7_ayer, v1_close, hora_vela, False)`

**Ningún otro bloque dentro de `evaluar_activo()` fue tocado** — GNA, RPG, 1VR, PM40, 4PASOS, Canales y Reset Diario permanecen exactamente igual, en el mismo orden.

## Archivos modificados en este sprint

- **Modificado:** `server.py` — `evaluar_gba()` agregada, ambos bloques GBA reemplazados por llamadas.
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo).

## Último commit antes de este sprint

(commit de AX-012C, ver historial de git)

## Rama

main

## Sprint activo

AX-012D — Extract GBA Engine (este sprint)

## Próximo sprint sugerido

Según el orden documentado en `05-STRATEGY-ENGINE-DESIGN.md` sección 5: **AX-012E (renombrado a AX-012E en la planificación original) — extraer `evaluar_rpg_activacion()` y `evaluar_rpg_disparo()`** por separado (RPG, a diferencia de GNA/GBA, tiene umbrales y campos adicionales — `rpg_s20`/`rpg_s40` en la activación — por lo que conviene mantenerlas como dos funciones distintas en vez de una con flag `es_v1`).

## Riesgos abiertos

(Ver lista completa en `04-ARCHITECTURE-AUDIT.md` sección 6 y `05-STRATEGY-ENGINE-DESIGN.md` sección 4. Nota específica de este sprint:)

1. **NUEVO AX-012D:** durante la verificación funcional se cometieron 2 errores de cálculo manual en los datos de prueba (usar `v_close < v_open` cuando el bloque de activación de GBA requiere vela verde `v_close > v_open`) — ambos fueron corregidos y la prueba final confirmó comportamiento correcto. Queda como recordatorio reforzado: verificar a mano las condiciones booleanas de cada bloque (no solo los umbrales numéricos) antes de diseñar los datos de prueba.
2. **NUEVO AX-012D:** se confirma el patrón de AX-012C como repetible y estable — extracción con 2 bloques (V1/V2-V7), reemplazo de bloques inline ANTES de insertar la función nueva, y prueba funcional directa de la función extraída (no solo de `evaluar_activo()` completa) para aislar mejor cualquier fallo.
3. Los riesgos generales de la descomposición (variables compartidas, flags fired, interacción P2 dinámico/4PASOS, orden de evaluación inmutable) documentados en AX-012A siguen aplicando para todos los sub-sprints siguientes.

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Leer `05-STRATEGY-ENGINE-DESIGN.md` antes de cualquier sub-sprint de extracción — contiene el análisis función por función y el orden obligatorio
- Nunca codificar sin autorización explícita de Noel
- Al extraer una función con 2 caminos (V1/V2-V7), reemplazar PRIMERO los bloques inline por llamadas, y SOLO DESPUÉS insertar la definición de la función nueva (lección de AX-012C, confirmada de nuevo en AX-012D)
- Al diseñar datos de prueba sintéticos, verificar a mano TODAS las condiciones booleanas del bloque (no solo los umbrales numéricos) — un error de signo en vela verde/roja puede hacer fallar una prueba válida y generar una falsa alarma
- Verificar sintaxis Y prueba funcional con datos sintéticos después de cualquier extracción dentro de evaluar_activo()
- Validar cada sub-sprint en producción durante al menos un día de mercado completo antes de proceder al siguiente
