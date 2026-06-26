# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-012B (Prepare Candle Context) ejecutado — primer paso real de código en la descomposición de `evaluar_activo()`. `preparar_contexto_vela(simbolo, velas, ahora)` extraída como función pura, sin cambiar ninguna lógica de trading, flags, P2 dinámico, ni 4PASOS. Verificado con py_compile y prueba funcional completa (3 escenarios: contexto válido, evaluar_activo end-to-end, y caso sin vela encontrada).

## Cambio realizado en este sprint

`preparar_contexto_vela(simbolo, velas, ahora)` — nueva función, ubicada justo antes de `evaluar_activo()`. Hace exactamente lo que antes hacía el inicio inline de `evaluar_activo()`:
- Calcula `hora = ahora.hour`
- Busca `vela_actual` cuyo `dt_v.hour == hora - 1`
- Si no existe, imprime el mismo mensaje exacto (`"{simbolo}: no se encontro vela para hora {hora-1}"`) y devuelve `None`
- Extrae `v_open, v_close, v_high, v_low, fecha_hoy`
- Devuelve un dict con `hora, vela_actual, v_open, v_close, v_high, v_low, fecha_hoy`

`evaluar_activo()` ahora llama a `ctx = preparar_contexto_vela(simbolo, velas, ahora)`, verifica `if ctx is None: return`, y desempaqueta las mismas 7 variables desde `ctx`. **Ningún otro código dentro de `evaluar_activo()` fue modificado** — el reset diario, la vela alcista, la bifurcación V1/V2-7, y todas las estrategias (1VR, RPG, GNA, GBA, PM40, 4PASOS, canales) permanecen exactamente igual, en el mismo orden.

## Archivos modificados en este sprint

- **Modificado:** `server.py` — `preparar_contexto_vela()` agregada, `evaluar_activo()` usa `ctx` en sus primeras líneas.
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo).

## Último commit antes de este sprint

e10e7bc — Update 10-HANDOFF.md (AX-012A)

## Rama

main

## Sprint activo

AX-012B — Prepare Candle Context (este sprint)

## Próximo sprint sugerido

Según el orden documentado en `05-STRATEGY-ENGINE-DESIGN.md` sección 5: **AX-012C — extraer `evaluar_gna()` y `evaluar_gba()`** por separado, las dos estrategias más simples y simétricas del sistema (sección 2.5 del diseño).

## Riesgos abiertos

(Ver lista completa en `04-ARCHITECTURE-AUDIT.md` sección 6 y `05-STRATEGY-ENGINE-DESIGN.md` sección 4. Nota específica de este sprint:)

1. **NUEVO AX-012B:** existe un archivo `axis_report.sh` sin rastrear (untracked) en el repositorio local de Noel, detectado en el chequeo inicial de este sprint. No forma parte de ningún sprint conocido de AXIS 2.0 — no se tocó, queda documentado para que Noel confirme su propósito o lo elimine si es un archivo de prueba olvidado.
2. **NUEVO AX-012B:** este es el primer sprint que modifica código real dentro de `evaluar_activo()` (los sprints AX-003 a AX-010 modularizaron funciones *fuera* de ella). A partir de aquí, cada sub-sprint de extracción debe seguir el mismo nivel de rigor: bloque exacto verificado contra el código real, prueba funcional con datos sintéticos, y verificación de producción — nunca solo sintaxis.
3. Los riesgos generales de la descomposición (variables compartidas, flags fired, interacción P2 dinámico/4PASOS, orden de evaluación inmutable) documentados en AX-012A siguen aplicando para todos los sub-sprints siguientes (C en adelante).

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Leer `05-STRATEGY-ENGINE-DESIGN.md` antes de cualquier sub-sprint de extracción (B en adelante) — contiene el análisis función por función y el orden obligatorio
- Nunca codificar sin autorización explícita de Noel
- Verificar sintaxis Y prueba funcional con datos sintéticos después de cualquier extracción dentro de evaluar_activo() — la sintaxis sola no detecta cambios de comportamiento sutiles
- Validar cada sub-sprint en producción durante al menos un día de mercado completo antes de proceder al siguiente
