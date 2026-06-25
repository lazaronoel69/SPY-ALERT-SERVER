# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. Sin cambios de comportamiento en este sprint.

## Último commit antes de este sprint

79f6e0a — fix: V7 una sola evaluacion + historico con vela real + frontend sin recalculo v8.84

## Rama

main

## Sprint activo

AX-001 — Engineering Baseline (este sprint)

## Próximo sprint

AX-002 — Core Map

## Riesgos abiertos

1. GLD sin canal bajista activo actualmente
2. Pendiente verificar visualmente que no hay alertas duplicadas tras v8.84
3. 4PASOS solo dentro de RCB
4. Tradier limita historial de 15min a ~40 días
5. Bug cosmético: chart marca "EN FORMACIÓN" en la última vela ya cerrada
6. Frontend aún calcula canales PM40/4PASOS en JavaScript

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Nunca codificar sin autorización explícita de Noel
- Verificar sintaxis y simular orden de ejecución después de cualquier fix
