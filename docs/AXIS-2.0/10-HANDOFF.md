# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-021 (Fix historial_lows) ejecutado — bug real de `NameError` latente en `evaluar_4pasos_v2_v7` corregido con una línea. Core Strategy Engine completo y limpio. AX-017 a AX-019 completados previamente (extracción de 4PASOS V1, 4PASOS V2-V7, Canal V2-V7).

## Cambio realizado en este sprint

**Bug corregido:** En `evaluar_4pasos_v2_v7` (server.py), la variable `historial_lows` era definida solo en la rama `elif ed["4ps_p2_idx"] is None:` pero referenciada en la rama mutuamente excluyente `elif ed["4ps_p2_idx"] is not None:` (Casos A y C). Esto causaría `NameError` en producción al ejecutar Caso A (P2 actualizado por mecha) o Caso C (P2 sube con tendencia alcista), una vez que 4PASOS tiene P2 fijado.

**Fix:** Una sola línea agregada al inicio del bloque `elif ed["4ps_p2_idx"] is not None:`, línea 1309:
```python
historial_lows = ed.get("4ps_historial_lows", [])
```

Sin cambio de lógica. Sin cambio de comportamiento. Ninguna otra línea tocada.

## Análisis del bug

- Caso B (señal PUT) no usa `historial_lows` → nunca crasheó visiblemente
- Casos A y C sí lo usan → `NameError` al intentar actualizar P2 post-fijación
- El bug era latente porque 4PASOS requiere varias velas para llegar a P2 fijado, y los Casos A/C son condiciones específicas de precio — infrecuente pero real

## Archivos modificados en este sprint

- **Modificado:** `server.py` — línea 1309, una línea agregada en `evaluar_4pasos_v2_v7`
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo)

## Último commit antes de este sprint

0a82b16 — AX-020 Core Readiness Audit

## Rama

main

## Sprint activo

AX-021 — Fix historial_lows (este sprint)

## Próximos sprints sugeridos

Según `07-CORE-READINESS-AUDIT.md`:
- **AX-022** (P1) — Stop-loss automático por posición: cerrar si `pl_pct_actual < -60%`
- **AX-023** (P1) — Límite máximo de posiciones abiertas simultáneas
- **AX-024** (P2) — Endpoint `/metricas` automático por estrategia
- **AX-025** (P2) — Cierre parcial al 50% de ganancia

## Riesgos abiertos

R1 (P1 CRÍTICO): Sin reglas de riesgo de capital — sin stop-loss ni límite de posiciones. Ver `07-CORE-READINESS-AUDIT.md`.
R3 (P1): GTC fijo a 2x sin trailing stop.
R4 (P2): Señal duplicada posible en redeploy entre V7 anticipada y V7 real.
R5 (RESUELTO en AX-021): `historial_lows` indefinido en rama `p2 is not None`.

## Notas para quien continúe

- Leer siempre `07-CORE-READINESS-AUDIT.md` para prioridades P1/P2/P3 actuales
- Preferir heredocs (`python3 << 'EOF' ... EOF`) sobre `python3 -c "..."` para pruebas con comillas anidadas
- Tras cada deploy: revisar logs de Railway con `railway logs --tail 200`, y verificar `/status` al menos 2 veces espaciadas varios minutos
- El Core Strategy Engine está completo — los próximos sprints son de gestión de riesgo, no de extracción
