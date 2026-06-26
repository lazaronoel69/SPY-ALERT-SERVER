# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-012E (Extract RPG Engine) ejecutado — `evaluar_rpg_activacion()` y `evaluar_rpg_disparo()` extraídas de `evaluar_activo()` como dos funciones independientes (siguiendo lo pedido explícitamente por el sprint, dado que RPG tiene campos adicionales `rpg_s20`/`rpg_s40` que GNA/GBA no tenían). Ubicadas inmediatamente después de `evaluar_gba()`. Sin tocar GNA, GBA, 1VR, PM40, 4PASOS, Canales, ni la reconstrucción RPG dentro del Reset Diario. Verificado con py_compile y prueba funcional mínima de ambos escenarios.

## Cambio realizado en este sprint

1. **`evaluar_rpg_activacion(simbolo, ed, velas, v_open, v_close, v_low, v7_ayer)`** — contiene exactamente el bloque de activación RPG en V1 (gap mínimo 0.5%, vela verde). Mismo print exacto, mismos campos guardados (`rpg_activo`, `rpg_piso`, `rpg_s20`, `rpg_s40`).
2. **`evaluar_rpg_disparo(simbolo, ed, vela_actual, v_close, hora_vela)`** — contiene exactamente el bloque de disparo RPG en V2-V7 (ruptura del piso, label RPG vs RPG+ según condición adicional). Mismo flujo de `guardar_estado_dia()` + `enviar_senal_con_botones()` con el mismo texto exacto.

Dentro de `evaluar_activo()`:
- En V1: `evaluar_rpg_activacion(simbolo, ed, velas, v_open, v_close, v_low, v7_ayer)`
- En V2-V7: `evaluar_rpg_disparo(simbolo, ed, vela_actual, v_close, hora_vela)`

**No se tocó la reconstrucción RPG dentro del Reset Diario** (bloque que re-activa RPG si el sistema detecta que V1 ya existe en el histórico tras un reinicio) — queda exactamente igual, según regla explícita del sprint. **Ningún otro bloque fue modificado** — GNA, GBA, 1VR, PM40, 4PASOS y Canales permanecen exactamente igual, en el mismo orden.

## Archivos modificados en este sprint

- **Modificado:** `server.py` — ambas funciones RPG agregadas, ambos bloques inline reemplazados por llamadas.
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo).

## Último commit antes de este sprint

69bcffb — AX-INF-001 Tools Automation

## Rama

main

## Sprint activo

AX-012E — Extract RPG Engine (este sprint)

## Próximo sprint sugerido

Según el orden documentado en `05-STRATEGY-ENGINE-DESIGN.md` sección 5: **AX-012F — unificar y extraer `evaluar_1vr()`**, consolidando el camino normal (V1) y el de reconstrucción (dentro del Reset Diario) en una sola función reutilizable, con pruebas exhaustivas comparando ambos caminos antes/después — este es el sprint de mayor cuidado hasta ahora, dado que requiere tocar por primera vez el bloque de Reset Diario.

## Riesgos abiertos

(Ver lista completa en `04-ARCHITECTURE-AUDIT.md` sección 6 y `05-STRATEGY-ENGINE-DESIGN.md` sección 4. Nota específica de este sprint:)

1. **NUEVO AX-012E:** RPG quedó dividida en 2 funciones (no 1 con flag `es_v1` como GNA/GBA) porque sus 2 caminos comparten muy poca estructura real — la activación guarda 4 campos distintos (`rpg_activo`, `rpg_piso`, `rpg_s20`, `rpg_s40`) y el disparo lee/calcula 6+ variables propias (`techo_rpg`, `zona_30_rpg`, `en_rcb_30_rpg`, etc.) que no existen en la activación. Forzar un flag `es_v1` aquí habría resultado en una función con una rama mucho más compleja que la otra — el patrón de 2 funciones es más legible y más seguro para RPG específicamente.
2. **NUEVO AX-012E:** la reconstrucción RPG en el Reset Diario sigue siendo código DUPLICADO respecto a `evaluar_rpg_activacion()` (misma lógica, distintos nombres de variable con sufijo `_r`) — exactamente la misma situación que ya se documentó para 1VR en AX-012A/C. Este sprint NO la tocó por regla explícita; queda pendiente para cuando se aborde el Reset Diario (AX-012F en adelante, o un sprint dedicado).
3. Los riesgos generales de la descomposición (variables compartidas, flags fired, interacción P2 dinámico/4PASOS, orden de evaluación inmutable) documentados en AX-012A siguen aplicando.

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Leer `05-STRATEGY-ENGINE-DESIGN.md` antes de cualquier sub-sprint de extracción
- Nunca codificar sin autorización explícita de Noel
- Cuando una estrategia tiene 2 caminos (V1/V2-V7) con poca estructura compartida real (como RPG), preferir 2 funciones separadas en vez de 1 función con flag — más legible y más seguro
- Reemplazar PRIMERO los bloques inline por llamadas, y SOLO DESPUÉS insertar la definición de la función nueva, para evitar texto duplicado durante la búsqueda exacta
- Verificar sintaxis Y prueba funcional con datos sintéticos (revisando a mano todas las condiciones booleanas, no solo los umbrales numéricos) después de cualquier extracción
- Validar cada sub-sprint en producción durante al menos un día de mercado completo antes de proceder al siguiente
- Usar `tools/pre_sprint.sh` y `tools/chatgpt_report.sh` para acelerar las verificaciones de cada sub-sprint
