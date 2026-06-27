# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-015 (Extract PM40 V1) ejecutado — `evaluar_pm40_v1()` extraída de `evaluar_activo()`, conteniendo exactamente el bloque de PM40 en la rama V1 (P1 dinámico: inicialización, actualización de P1 si rompe, maduración tras 3 velas bajo P1, fijación/actualización de P2 con invalidación si P2≥P1). Sin tocar PM40 V2-V7, 4PASOS, Canal V2-V7 (AX-014 sigue revertido), 1VR/RPG/GNA/GBA, ni Reset Diario. Verificado con py_compile, AST, import real, prueba funcional (3 casos), **y verificación sostenida de producción siguiendo la lección de AX-014.**

## Cambio realizado en este sprint

`evaluar_pm40_v1(simbolo, ed, c, velas, v_high)` — nueva función. Contiene exactamente el bloque original: si el canal manual está apagado y PM40 no ha disparado, calcula las 4 SMAs (20/40/100/200), verifica el orden bajista requerido, inicializa o actualiza P1 según corresponda, incrementa el conteo de velas bajo P1 hacia la maduración (3+), y fija/actualiza P2 escribiendo directamente sobre `canal[simbolo]` cuando aplica (incluyendo la invalidación si P2≥P1).

Dentro de `evaluar_activo()`: `evaluar_pm40_v1(simbolo, ed, c, velas, v_high)`. Ningún otro bloque fue modificado.

## Verificación reforzada (lección de AX-014 aplicada)

Tras el incidente de AX-014, este sprint se verificó con rigor adicional:
1. Logs de Railway capturados con `railway logs --tail 200` tras el deploy — confirmaron arranque completamente limpio (gunicorn, 8 canales cargados, 8 posiciones, base de datos de velas verificada, threads arrancados), sin ningún traceback, y **más de 3 horas de operación estable** antes del siguiente reinicio normal.
2. `/status` verificado **dos veces, espaciadas 2 minutos entre sí** (no solo segundos) — ambas devolvieron `HTTP 200` con `"sistema":"AXIS Breakout Sentinel v8.84"` consistente.

## Archivos modificados en este sprint

- **Modificado:** `server.py` — `evaluar_pm40_v1()` agregada, bloque inline reemplazado por la llamada.
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo).

## Último commit antes de este sprint

a13c56a — AX-014A Post Rollback Diagnosis

## Rama

main

## Sprint activo

AX-015 — Extract PM40 V1 (este sprint)

## Próximo sprint sugerido

Según `05-STRATEGY-ENGINE-DESIGN.md`: **AX-016 — extraer PM40 V2-V7** (maduración, fijación/actualización de P2 con slope proyectado, ruptura con alerta CALL, o actualización si no rompe) — mayor riesgo que este sprint por la cantidad de estado y la lógica de comparación contra el techo proyectado. Alternativamente, **reintentar AX-014** (Canal V2-V7) ahora que se confirmó que no había ninguna causa real de código en el intento anterior, aplicando la misma verificación reforzada usada en este sprint.

## Riesgos abiertos

(Ver lista completa en `04-ARCHITECTURE-AUDIT.md` sección 6, `05-STRATEGY-ENGINE-DESIGN.md` sección 4, y `06-AX014-POSTMORTEM.md`. Sin riesgos nuevos críticos de este sprint — la verificación reforzada confirmó estabilidad sostenida.)

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Leer `05-STRATEGY-ENGINE-DESIGN.md` y `06-AX014-POSTMORTEM.md` antes de cualquier sub-sprint de extracción
- Nunca codificar sin autorización explícita de Noel
- Extraer bloques directamente del archivo real con Python, nunca transcribir a mano
- Verificar `ast.parse()` del resultado completo antes de escribir el archivo
- **Tras cada deploy: revisar logs de Railway con `railway logs --tail 200`, y verificar `/status` al menos 2 veces espaciadas varios minutos** — patrón confirmado como efectivo en este sprint tras la lección de AX-014
- Validar cada sub-sprint en producción durante al menos un día de mercado completo antes de proceder al siguiente
