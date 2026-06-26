# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-012G (Extract 1VR Normal) ejecutado — `evaluar_1vr_normal()` extraída de `evaluar_activo()`, conteniendo exactamente el bloque de 1VR en la rama V1 normal. La reconstrucción 1VR dentro de `reset_diario_si_aplica()` permanece intacta y sin tocar, según regla explícita del sprint. Verificado con py_compile, AST, import real, y prueba funcional en ambos casos (V1 roja / V1 no roja).

## Cambio realizado en este sprint

`evaluar_1vr_normal(simbolo, ed, velas, vela_actual, v_open, v_close, v_roja)` — nueva función, ubicada inmediatamente después de `reset_diario_si_aplica()`. Contiene exactamente el bloque original: cálculo de techo/zona 30%/SMA, decisión del label (1VR vs 1VR+), y envío de la señal con el mismo texto exacto.

Dentro de `evaluar_activo()`: `evaluar_1vr_normal(simbolo, ed, velas, vela_actual, v_open, v_close, v_roja)` reemplaza el bloque inline. **No se tocó la reconstrucción 1VR dentro de `reset_diario_si_aplica()`** — sigue siendo código duplicado, sin cambios, según regla explícita del sprint (la unificación queda para un sprint futuro). Ningún otro bloque (RPG, GNA, GBA, PM40, 4PASOS, Canales) fue modificado.

## Archivos modificados en este sprint

- **Modificado:** `server.py` — `evaluar_1vr_normal()` agregada, bloque inline reemplazado por la llamada.
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo).

## Último commit antes de este sprint

b84e87b (commit previo a este sprint, ver historial de git)

## Rama

main

## Sprint activo

AX-012G — Extract 1VR Normal (este sprint)

## Próximo sprint sugerido

Según el orden documentado en `05-STRATEGY-ENGINE-DESIGN.md` sección 5: **AX-012H — unificar 1VR**, ahora que tanto `evaluar_1vr_normal()` como `reset_diario_si_aplica()` existen como funciones propias. Este sprint modificaría `reset_diario_si_aplica()` para llamar a `evaluar_1vr_normal()` en vez de duplicar su lógica internamente — el primer sprint que toca el contenido de `reset_diario_si_aplica()` desde que se creó en AX-012F, por lo que requiere especial cuidado y pruebas exhaustivas comparando el comportamiento antes/después.

## Riesgos abiertos

(Ver lista completa en `04-ARCHITECTURE-AUDIT.md` sección 6 y `05-STRATEGY-ENGINE-DESIGN.md` sección 4. Nota específica de este sprint:)

1. **NUEVO AX-012G:** la reconstrucción 1VR dentro de `reset_diario_si_aplica()` sigue siendo código duplicado respecto a `evaluar_1vr_normal()` — con nombres de variable distintos (`v1_close_r` vs `v_close`, `ahora_dt_r` vs `ahora_dt_vr`, etc.) pero lógica idéntica. Documentado para AX-012H.
2. **NUEVO AX-012G:** el patrón de verificación con `ast.parse()` antes de escribir (adoptado en AX-012F tras el incidente de esa sesión) se aplicó nuevamente en este sprint sin problemas — confirmado como práctica estándar efectiva para todos los sprints de extracción de aquí en adelante.
3. Los riesgos generales de la descomposición (variables compartidas, flags fired, interacción P2 dinámico/4PASOS, orden de evaluación inmutable) documentados en AX-012A siguen aplicando.

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Leer `05-STRATEGY-ENGINE-DESIGN.md` antes de cualquier sub-sprint de extracción
- Nunca codificar sin autorización explícita de Noel
- Extraer bloques de código directamente del archivo real con Python (`content.find()` + slicing) en vez de transcribirlos manualmente — confirmado como el método más confiable tras los incidentes de AX-012E y AX-012F
- Verificar `ast.parse()` del resultado ANTES de escribir el archivo, no solo `py_compile` después
- Al verificar resultados de comandos en terminal, usar agrupación `{ comando; } > archivo 2>&1; cat archivo; pbcopy < archivo` en vez de pipes con `tee` — más confiable para capturar la salida completa sin truncar
- Validar cada sub-sprint en producción durante al menos un día de mercado completo antes de proceder al siguiente
