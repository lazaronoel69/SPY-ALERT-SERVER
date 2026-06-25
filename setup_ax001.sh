#!/bin/bash
set -e
mkdir -p docs/AXIS-2.0

cat > docs/AXIS-2.0/00-START-HERE.md << 'EOF'
# AXIS 2.0 — START HERE

## Estado detectado automáticamente (06/25/2026 ~18:00 EST)

| Campo | Valor |
|---|---|
| Versión server.py | v8.84 |
| Commit actual | 79f6e0a |
| Rama | main |
| Working tree | limpio (sin cambios pendientes) |
| Sintaxis (py_compile) | OK |

## Estado del proyecto

AXIS está en producción activa (Railway), operando en vivo sobre 8 activos (SPY, AAPL, BA, GLD, NVDA, AMZN, GOOG, META). El día 06/25/2026 se resolvió un incidente de seguridad crítico (token de Telegram comprometido) y varios bugs de evaluación de la vela V7. El sistema es estable a partir de v8.84.

Este sprint (AX-001) NO modifica nada del sistema en producción. Es exclusivamente la base de documentación de ingeniería para futuros sprints de AXIS 2.0.

## Sprint activo

**AX-001 — Engineering Baseline**
Crear la estructura de documentación (docs/AXIS-2.0/) y el backlog inicial, sin tocar lógica, funciones, ni comportamiento del sistema.

## Próximo sprint

**AX-002 — Core Map**
Mapeo completo de la arquitectura actual: módulos, funciones, dependencias entre ellas, y flujo de datos.

## Cómo usar esta carpeta

- 00-START-HERE.md — este archivo, punto de entrada
- 03-BACKLOG.md — lista de sprints planificados para AXIS 2.0
- 10-HANDOFF.md — estado de traspaso para quien continúe el trabajo
EOF

cat > docs/AXIS-2.0/03-BACKLOG.md << 'EOF'
# AXIS 2.0 — BACKLOG

| ID | Nombre | Descripción |
|---|---|---|
| AX-001 | Baseline | Documentación de ingeniería inicial. Sin cambios de lógica. |
| AX-002 | Core Map | Mapeo completo de arquitectura actual: módulos, funciones, dependencias. |
| AX-003 | Time Engine | Documentar el manejo de horarios, zona EST, días de mercado, y la regla de cierre de velas. |
| AX-004 | Candle Engine | Documentar la construcción de velas AXIS (V1-V7), incluyendo la vela provisional V7 (v8.83). |
| AX-005 | Channel Engine | Documentar la lógica de canales bajistas (CNF/RCB/PM40) y 4PASOS. |

Este backlog es la versión inicial — sujeta a reordenamiento según prioridad real del sistema en producción.
EOF

cat > docs/AXIS-2.0/10-HANDOFF.md << 'EOF'
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
EOF

echo "Archivos creados:"
find docs/AXIS-2.0 -type f
