# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-012C (Extract GNA Engine) ejecutado — `evaluar_gna()` extraída de `evaluar_activo()` con ambos bloques (activación V1 + disparo V2-V7) exactos, sin cambiar GBA, RPG, 1VR, PM40, 4PASOS, Canales, ni Reset Diario. Verificado con py_compile y prueba funcional en ambos escenarios (V1 y V2-V7) con datos sintéticos.

## Cambio realizado en este sprint

`evaluar_gna(simbolo, ed, velas, v_open, v_close, v_alcista, v7_ayer, v1_close, hora_vela, es_v1)` — nueva función, ubicada justo antes de `evaluar_activo()`. Contiene **exactamente** los 2 bloques de GNA que existían inline:
- `es_v1=True`: bloque de activación (gap_alza >= 0.1%, SMA20>SMA40) — idéntico al original, mismo print exacto.
- `es_v1=False`: bloque de disparo (v_alcista y v_close > v1_close) — idéntico al original, mismo flujo de `guardar_estado_dia()` + `enviar_senal_con_botones()` con el mismo texto exacto.

Recibe explícitamente todas las variables necesarias — no lee nada implícito de un scope compartido.

Dentro de `evaluar_activo()`, ambos bloques GNA fueron reemplazados por una sola línea de llamada cada uno:
- En V1: `evaluar_gna(simbolo, ed, velas, v_open, v_close, v_alcista, v7_ayer, None, hora_vela, True)`
- En V2-V7: `evaluar_gna(simbolo, ed, velas, v_open, v_close, v_alcista, v7_ayer, v1_close, hora_vela, False)`

**Ningún otro bloque dentro de `evaluar_activo()` fue tocado** — GBA, RPG, 1VR, PM40, 4PASOS, Canales y Reset Diario permanecen exactamente igual, en el mismo orden.

## Archivos modificados en este sprint

- **Modificado:** `server.py` — `evaluar_gna()` agregada, ambos bloques GNA reemplazados por llamadas.
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo).

## Último commit antes de este sprint

5e04f61 — AX-012B Prepare Candle Context

## Rama

main

## Sprint activo

AX-012C — Extract GNA Engine (este sprint)

## Próximo sprint sugerido

Según el orden documentado en `05-STRATEGY-ENGINE-DESIGN.md` sección 5: **AX-012D — extraer `evaluar_gba()`** (la estrategia hermana de GNA, misma estructura, mismo patrón de extracción ya validado en este sprint).

## Riesgos abiertos

(Ver lista completa en `04-ARCHITECTURE-AUDIT.md` sección 6 y `05-STRATEGY-ENGINE-DESIGN.md` sección 4. Nota específica de este sprint:)

1. **NUEVO AX-012C:** durante la verificación funcional de este sprint, se detectó que un mock simplificado de `calcular_sma()` (devolviendo el mismo valor para SMA20 y SMA40) hacía fallar la prueba del caso V1 — esto era un error en la simulación de prueba, no en el código real. Queda documentado como recordatorio: al probar funciones extraídas que dependen de comparaciones entre 2+ valores calculados, los mocks deben producir valores genuinamente distintos para cada uno, o la prueba no detecta nada real.
2. **NUEVO AX-012C:** `evaluar_gna()` recibe `v1_close=None` cuando se llama desde la rama V1 (donde esa variable aún no existe en ese punto del flujo original) — esto es intencional y preserva el comportamiento exacto, ya que el bloque original de V1 nunca leía `v1_close`. Documentado para que sprints futuros (GBA, RPG) sigan el mismo patrón si aplica.
3. Los riesgos generales de la descomposición (variables compartidas, flags fired, interacción P2 dinámico/4PASOS, orden de evaluación inmutable) documentados en AX-012A siguen aplicando para todos los sub-sprints siguientes (D en adelante).

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Leer `05-STRATEGY-ENGINE-DESIGN.md` antes de cualquier sub-sprint de extracción — contiene el análisis función por función y el orden obligatorio
- Nunca codificar sin autorización explícita de Noel
- Al extraer una función con 2 caminos (V1/V2-V7), reemplazar PRIMERO los bloques inline por llamadas, y SOLO DESPUÉS insertar la definición de la función nueva — si se hace al revés, el texto del bloque original puede aparecer duplicado (una vez en el código original, otra dentro de la función recién insertada) y romper la búsqueda exacta de reemplazo
- Verificar sintaxis Y prueba funcional con datos sintéticos (con mocks que produzcan valores genuinamente distintos cuando se comparan) después de cualquier extracción dentro de evaluar_activo()
- Validar cada sub-sprint en producción durante al menos un día de mercado completo antes de proceder al siguiente
