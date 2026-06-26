# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-011 (Architecture Audit) ejecutado — auditoría completa del estado real del sistema tras 7 sprints de modularización (AX-003 a AX-010). Documento `04-ARCHITECTURE-AUDIT.md` creado con datos exactos (líneas, tamaños, dependencias, top 10 funciones). Ningún código fue modificado en este sprint.

## Resumen de la auditoría (ver 04-ARCHITECTURE-AUDIT.md para detalle completo)

- **server.py:** 3,370 líneas, 160 KB.
- **8 módulos axis_*.py creados:** 1,095 líneas en total (~24.5% del código del sistema).
- **Mayor riesgo identificado:** `evaluar_activo()` sigue siendo un monolito de 601 líneas, nunca tocado en ningún sprint.
- **Ningún módulo axis_*.py importa de server.py** — todas las dependencias hacia atrás se resuelven con inyección de parámetro, evitando imports circulares.

## Archivos modificados en este sprint

- **Creado:** `docs/AXIS-2.0/04-ARCHITECTURE-AUDIT.md` — auditoría completa.
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo).
- **Sin cambios en código** (server.py ni ningún axis_*.py).

## Último commit antes de este sprint

e199ef7 — AX-010 Market Data Baseline

## Rama

main

## Sprint activo

AX-011 — Architecture Audit (este sprint)

## Próximo sprint sugerido

Según la recomendación de 5 sprints en `04-ARCHITECTURE-AUDIT.md`, el siguiente debería ser **AX-012 — Time Engine** (mover `es_dia_mercado`, `restar_dias_habiles`, `calcular_festivos`, `calcular_pascua` a `axis_time.py`), ya que es el sprint de menor riesgo y mayor beneficio inmediato (permite que módulos futuros, incluyendo `axis_market.py` ya existente, dejen de necesitar inyección de parámetro para estas funciones).

## Riesgos abiertos

(Ver lista completa y detallada en `04-ARCHITECTURE-AUDIT.md`, sección 6. Resumen aquí:)

1. GLD sin canal bajista activo actualmente
2. Pendiente verificar visualmente que no hay alertas duplicadas tras v8.84
3. 4PASOS solo dentro de RCB
4. Tradier limita historial de 15min a ~40 días
5. Bug cosmético: chart marca "EN FORMACIÓN" en la última vela ya cerrada
6. Frontend aún calcula canales PM40/4PASOS en JavaScript
7. TWELVEDATA_KEY y FINNHUB_KEY siguen hardcodeados en server.py
8. Credenciales duplicadas (controladamente) entre server.py y 3 módulos (Tradier sandbox, Tradier real, Telegram)
9. archivar_señales_dia aún sin mover
10. enviar_telegram_botones sigue acoplada a Portfolio/Derby en server.py
11. registrar_posicion/cerrar_posicion siguen en server.py
12. calcular_techo_canal/calcular_piso_mitad_canal siguen en server.py
13. **NUEVO AX-011:** `evaluar_activo()` (601 líneas) es el mayor riesgo arquitectónico identificado — concentra 7+ estrategias distintas en una sola función, nunca tocada en ningún sprint.
14. **NUEVO AX-011:** no existe ninguna suite de pruebas automatizadas en el repositorio — toda verificación ha sido manual (simulación de import + curl a /status).
15. **NUEVO AX-011:** 3 patrones de wrapper ligeramente distintos coexisten (parámetro simple, tupla con flag, múltiples parámetros) — sin unificar todavía.

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Leer `04-ARCHITECTURE-AUDIT.md` completo antes de planificar cualquier sprint futuro — contiene el mapa de dependencias y la justificación de cada recomendación
- Nunca codificar sin autorización explícita de Noel
- Verificar sintaxis y simular orden de ejecución real después de cualquier fix (lección del crash de import os, 06/25)
- El sprint de mayor riesgo recomendado (descomposición de evaluar_activo) requiere diseño extenso y aprobación explícita antes de cualquier código — no debe iniciarse a la ligera
