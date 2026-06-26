# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-012F (Extract Reset Daily) ejecutado — `reset_diario_si_aplica()` extraída de `evaluar_activo()`, conteniendo exactamente el bloque de reset diario completo, incluyendo la reconstrucción 1VR/RPG/GNA/GBA sin reutilizar las funciones ya extraídas (según regla explícita del sprint). Ubicada después de `evaluar_rpg_disparo()`. Verificado con py_compile, AST, import real, y prueba funcional en ambos casos (misma fecha / nueva fecha).

## Cambio realizado en este sprint

`reset_diario_si_aplica(simbolo, velas, fecha_hoy, ed, c, hora)` — nueva función. Contiene exactamente el bloque original:
- Detecta si `ed["fecha"] != fecha_hoy`
- Si aplica: busca V7 de ayer, llama a `reset_diario_activo()`, guarda P2 al inicio del día, y reconstruye 1VR/RPG/GNA/GBA desde el histórico **tal cual existía inline** (código duplicado respecto a las funciones ya extraídas en AX-012C/D/E — intencional, sin tocar, según regla del sprint)
- Devuelve `(ed, c)` actualizados

Dentro de `evaluar_activo()`: `ed, c = reset_diario_si_aplica(simbolo, velas, fecha_hoy, ed, c, hora)`. Ningún otro bloque fue modificado.

## Incidente durante este sprint (documentado con transparencia)

El primer intento de script de migración (`aplicar_ax012f.py` v1) tenía un bug de diseño: al insertar la función nueva usando `content.replace(MARKER, FUNC_DEF + MARKER, 1)` después de ya haber aplicado el primer reemplazo, el texto se insertó en una posición incorrecta, generando una definición de función anidada corrupta (`return ed, cdef reset_diario_si_aplica(...)`) que rompía la sintaxis. **Se detectó inmediatamente vía `python3 -m py_compile` (SyntaxError explícito), nunca llegó a comitearse ni a desplegarse.** Se revirtió con `git checkout server.py` y se reconstruyó el script (v2) agregando una verificación con `ast.parse()` **antes** de escribir el archivo — si el resultado no parsea como Python válido, el script no escribe nada y termina con error, dejando el archivo original intacto. Esta verificación adicional se usará en todos los scripts de migración futuros de este proyecto.

## Archivos modificados en este sprint

- **Modificado:** `server.py` — `reset_diario_si_aplica()` agregada, bloque inline reemplazado por la llamada.
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo).

## Último commit antes de este sprint

(commit de AX-012E, ver historial de git)

## Rama

main

## Sprint activo

AX-012F — Extract Reset Daily (este sprint)

## Próximo sprint sugerido

Según el orden documentado en `05-STRATEGY-ENGINE-DESIGN.md` sección 5: **AX-012G — unificar `evaluar_1vr()`**, ahora que el Reset Diario ya está extraído como función propia. Este sprint puede reutilizar `evaluar_1vr()` (una vez creada) tanto desde el flujo normal de V1 como desde dentro de `reset_diario_si_aplica()`, eliminando finalmente la duplicación de código que se ha documentado desde AX-012A.

## Riesgos abiertos

(Ver lista completa en `04-ARCHITECTURE-AUDIT.md` sección 6 y `05-STRATEGY-ENGINE-DESIGN.md` sección 4. Nota específica de este sprint:)

1. **NUEVO AX-012F:** se confirma que los scripts de migración deben verificar `ast.parse()` del resultado completo ANTES de escribir el archivo, no solo `py_compile` después — esto hubiera prevenido el incidente de este sprint con cero impacto en producción (el bug nunca llegó a comitearse), pero agrega una capa de seguridad adicional para sprints futuros con bloques grandes y complejos.
2. **NUEVO AX-012F:** la reconstrucción 1VR/RPG/GNA/GBA dentro de `reset_diario_si_aplica()` sigue siendo código duplicado respecto a las funciones ya extraídas — explícitamente no resuelto en este sprint, queda para AX-012G en adelante.
3. Los riesgos generales de la descomposición (variables compartidas, flags fired, interacción P2 dinámico/4PASOS, orden de evaluación inmutable) documentados en AX-012A siguen aplicando.

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Leer `05-STRATEGY-ENGINE-DESIGN.md` antes de cualquier sub-sprint de extracción
- Nunca codificar sin autorización explícita de Noel
- **Extraer bloques de código directamente del archivo real con Python** (`content.find()` + slicing) en vez de transcribirlos manualmente desde vistas parciales — esto evitó 2 errores de formato en AX-012E y se mantuvo en AX-012F
- **Verificar `ast.parse()` del resultado ANTES de escribir el archivo**, no solo `py_compile` después — patrón adoptado a partir de este sprint tras el incidente documentado arriba
- Si un script de migración aplica 2+ pasos secuenciales, aplicarlos sobre una copia en memoria y validar el resultado completo antes de tocar el archivo en disco
- Validar cada sub-sprint en producción durante al menos un día de mercado completo antes de proceder al siguiente
