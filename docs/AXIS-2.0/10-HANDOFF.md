# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-012G (Extract 1VR Normal) ejecutado — `evaluar_1vr_normal()` extraída de `evaluar_activo()`, conteniendo exactamente el bloque de 1VR en la rama V1 normal, sin tocar la reconstrucción 1VR dentro de `reset_diario_si_aplica()` (que permanece duplicada e intacta, según regla explícita del sprint). Ubicada inmediatamente después de `reset_diario_si_aplica()`. Verificado con py_compile, AST, import real, y prueba funcional en ambos casos (V1 roja / V1 no roja).

## Cambio realizado en este sprint

`evaluar_1vr_normal(simbolo, ed, velas, vela_actual, v_open, v_close, v_roja)` — nueva función. Contiene exactamente el bloque original de 1VR en V1: calcula techo/mitad del canal, zona 30% RCB, SMA20 vs SMA40, decide label (1VR vs 1VR+), marca `vr1_fired`, llama a `guardar_estado_dia()` y `enviar_senal_con_botones()` con el mismo texto exacto.

Dentro de `evaluar_activo()`: `evaluar_1vr_normal(simbolo, ed, velas, vela_actual, v_open, v_close, v_roja)`. Ningún otro bloque fue modificado — la reconstrucción 1VR dentro del Reset Diario sigue siendo código duplicado, sin tocar.

## Proceso de extracción (aplicando lecciones de AX-012E/F)

El bloque se extrajo directamente del archivo real con Python (`content.find()` + slicing), no transcrito manualmente — confirmado byte por byte contra el original antes de construir el script. El script de migración usa el patrón de verificación con `ast.parse()` sobre una copia en memoria antes de escribir, adoptado en AX-012F. La inserción de la función se ancló a `def evaluar_activo(...)` (en vez de a la firma de `reset_diario_si_aplica`), evitando el riesgo de insertar contenido dentro de una función existente como ocurrió en el incidente de AX-012F.

## Archivos modificados en este sprint

- **Modificado:** `server.py` — `evaluar_1vr_normal()` agregada, bloque inline reemplazado por la llamada.
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo).

## Último commit antes de este sprint

(commit de AX-012F, ver historial de git)

## Rama

main

## Sprint activo

AX-012G — Extract 1VR Normal (este sprint)

## Próximo sprint sugerido

Según `05-STRATEGY-ENGINE-DESIGN.md` y la nota explícita de AX-012F: considerar un sprint dedicado a **unificar 1VR normal con 1VR reconstrucción** — ahora que ambas existen como bloques identificables (`evaluar_1vr_normal()` y el bloque inline dentro de `reset_diario_si_aplica()`), se podría hacer que la reconstrucción llame a `evaluar_1vr_normal()` en vez de duplicar la lógica, eliminando finalmente esa redundancia documentada desde AX-012A. Este sprint fue explícitamente excluido de AX-012G ("Este sprint NO intenta unificar...").

Alternativamente, continuar con el patrón de extracción para PM40 y 4PASOS (sección 2.6/2.7 de `05-STRATEGY-ENGINE-DESIGN.md`), ambas marcadas como riesgo alto y candidatas a sub-división — el sprint siguiente debería primero diseñar esa sub-división antes de codificar, dado el mayor estado interno de ambas estrategias.

## Riesgos abiertos

(Ver lista completa en `04-ARCHITECTURE-AUDIT.md` sección 6 y `05-STRATEGY-ENGINE-DESIGN.md` sección 4. Nota específica de este sprint:)

1. **NUEVO AX-012G:** 1VR ahora existe en 2 lugares: `evaluar_1vr_normal()` (función propia) y el bloque de reconstrucción dentro de `reset_diario_si_aplica()` (inline, duplicado). Ambos deben mantenerse sincronizados manualmente si la lógica de 1VR cambia en el futuro, hasta que se unifiquen en un sprint dedicado.
2. Los riesgos generales de la descomposición (variables compartidas, flags fired, interacción P2 dinámico/4PASOS, orden de evaluación inmutable) documentados en AX-012A siguen aplicando.

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Leer `05-STRATEGY-ENGINE-DESIGN.md` antes de cualquier sub-sprint de extracción
- Nunca codificar sin autorización explícita de Noel
- Extraer bloques directamente del archivo real con Python, nunca transcribir a mano
- Verificar `ast.parse()` del resultado completo antes de escribir el archivo
- Anclar inserciones de funciones nuevas a marcadores estables que no estén dentro de otra función (como `def evaluar_activo(...)`), nunca a la firma de una función recién creada en el mismo sprint
- Validar cada sub-sprint en producción durante al menos un día de mercado completo antes de proceder al siguiente
