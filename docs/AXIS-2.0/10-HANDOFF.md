# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-012A (Strategy Engine Design) ejecutado — diseño completo de cómo dividir `evaluar_activo()` (601 líneas) en subfunciones, sin modificar ningún código. `evaluar_activo()` permanece exactamente igual.

## Resumen del diseño (ver 05-STRATEGY-ENGINE-DESIGN.md para detalle completo)

- **10 subfunciones propuestas**, cada una con inputs/outputs/estado/riesgo documentado.
- **3 de menor riesgo** (extraíbles ahora sin sub-división): `preparar_contexto_vela()`, `evaluar_gna()`/`evaluar_gba()`, `evaluar_rpg_activacion()`/`evaluar_rpg_disparo()`.
- **2 de riesgo alto que requieren sub-división obligatoria antes de extraerse:** PM40 y 4PASOS (mucho estado interno, lógica de maduración/proyección compleja).
- **1 que requiere cambio de comportamiento real** (`persistir_estado_si_cambia()`) — fuera de alcance hasta tener aprobación explícita separada.
- **Orden de evaluación documentado como inmutable** — cualquier sub-sprint futuro debe preservar el orden exacto actual.

## Archivos modificados en este sprint

- **Creado:** `docs/AXIS-2.0/05-STRATEGY-ENGINE-DESIGN.md` — diseño completo.
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo).
- **Sin cambios en código** (server.py ni ningún axis_*.py).

## Último commit antes de este sprint

9ba47d7 — AX-011 Architecture Audit (Create 04-ARCHITECTURE-AUDIT.md)

## Rama

main

## Sprint activo

AX-012A — Strategy Engine Design (este sprint)

## Próximo sprint sugerido

**AX-012B — extraer `preparar_contexto_vela()`** — la subfunción de menor riesgo de toda la lista (pura, sin estado, sin dependencia de `ed`/`c`). Primer paso real de código hacia la descomposición de `evaluar_activo()`, siguiendo el orden B→C→D→E→F→G→H→I→J documentado en 05-STRATEGY-ENGINE-DESIGN.md sección 5.

## Riesgos abiertos

(Ver lista completa en `04-ARCHITECTURE-AUDIT.md` sección 6. Riesgos específicos de este sprint:)

1. **NUEVO AX-012A:** `ahora_dt` se reconstruye de forma idéntica en al menos 5-7 lugares distintos dentro de `evaluar_activo()` — cualquier descomposición debe decidir explícitamente si preserva esta redundancia (más seguro, menos elegante) o la consolida (requiere verificación extra de que el valor es idéntico en todos los puntos de uso).
2. **NUEVO AX-012A:** la persistencia (`guardar_estado_dia()`/`guardar_canales()`) se llama de forma inconsistente dentro de la función actual — algunos bloques guardan inline, otros no explícitamente. Esta inconsistencia es preexistente (no introducida por ningún sprint), pero cualquier descomposición debe documentar conscientemente si la preserva tal cual o la corrige (y si la corrige, eso es un cambio de comportamiento que requiere aprobación separada, ver AX-012J).
3. **NUEVO AX-012A:** PM40 y 4PASOS escriben directamente sobre `canal[simbolo]` (el dict compartido con el módulo de canales separado en AX-009) — cualquier extracción de estas dos estrategias debe mantener esa escritura compartida intacta, no una copia local.
4. **NUEVO AX-012A:** el camino de reconstrucción (dentro del reset diario) duplica la lógica completa de 1VR con nombres de variable distintos — esto es código duplicado ya existente en producción, identificado pero no corregido en este sprint (solo documentado). AX-012E (unificar 1VR) es el sprint que abordaría esto.
5. **NUEVO AX-012A:** no existe ninguna prueba automatizada que valide el comportamiento actual de `evaluar_activo()` antes de comenzar cualquier extracción — sigue siendo la recomendación más fuerte de AX-011, ahora más urgente dado que AX-012B en adelante empezará a tocar código real de esta función.

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Leer `05-STRATEGY-ENGINE-DESIGN.md` completo antes de iniciar AX-012B o cualquier sub-sprint de extracción — contiene el análisis función por función y el orden obligatorio de sub-sprints
- Nunca codificar sin autorización explícita de Noel
- Verificar sintaxis y simular orden de ejecución real después de cualquier fix (lección del crash de import os, 06/25)
- Cada sub-sprint de AX-012B en adelante debe validarse en producción durante al menos un día de mercado completo antes de proceder al siguiente — `evaluar_activo()` genera alertas reales, el riesgo de regresión silenciosa es alto
