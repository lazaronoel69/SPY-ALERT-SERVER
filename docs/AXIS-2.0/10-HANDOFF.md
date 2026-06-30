# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. Backtest Engine v1 completo (BT-001 a BT-010).
Core Strategy Engine intacto — cero cambios a server.py durante toda la fase de backtest.

## Cambio realizado en este sprint

**Sprint BT-010 — Complete Backtest v1**

Agregadas a `backtest.py` dos funciones nuevas y 3 líneas de integración:

- `medir_outcome(señal, dia_velas, N=4)` — calcula movimiento proxy del subyacente
  en las N velas siguientes a la señal (misma sesión, sin cruzar día).
  Retorna: `mov_favorable_max_pct`, `mov_adverso_max_pct`, `acierto`,
  `n_velas_outcome`, `precio_cierre_outcome`.

- `calcular_metricas(signals)` — agrega métricas sobre todas las señales del run:
  `tasa_acierto`, `mov_favorable_avg`, `mov_adverso_avg`, `expectancy_proxy`,
  desglose `por_estrategia`.

- `evaluar_dia()` enriquece cada señal capturada con su outcome antes de retornar.
- `main()` agrega `"metricas"` al JSON de salida.

**Ningún cambio a server.py ni al Core.**

## Definición de acierto proxy

```
CALL: acierto = max(v.high - entrada) > max(entrada - v.low)   en N velas
PUT:  acierto = max(entrada - v.low)  > max(v.high - entrada)  en N velas
```

N=4 velas por defecto (mismo día, sin overnight). Parámetro configurable en `medir_outcome()`.

## Validación con datos reales

AAPL 2026-06-30 — GBA CALL — entrada=$286.97 — N=4 velas (V3..V6):
- `mov_favorable_max_pct`: 0.840 (high=$289.38 en V3)
- `mov_adverso_max_pct`:   0.122 (low=$286.62 en V3)
- `acierto`: true
- `expectancy_proxy`: 0.840

## Limitaciones conocidas del Backtest v1

**L1 — Canal no es histórico (la más importante)**
`cargar_canal_snapshot()` fetches el estado actual de producción vía `/canal_estado`.
No es reconstrucción histórica. Para fechas anteriores al `p1["fecha"]` del canal actual,
las estrategias RCB/CNF/4PASOS y PM40 pueden producir resultados históricamente incorrectos.
Días afectados por símbolo: SPY=22, AAPL=24, BA=8, GLD=0, NVDA=20, AMZN=18, GOOG=10, META=22.
Las estrategias sin dependencia de canal (1VR, RPG, GNA, GBA) son 100% correctas.

**L2 — Ventana de datos: 40 días (2026-05-04 a 2026-06-30)**
Solo 8 símbolos, un archivo `data/bt_velas_<SYMBOL>.json` por símbolo.
No comprometidos en git (excluidos via `.git/info/exclude`).

**L3 — Métricas son PROXY, NO P&L real de opciones**
Un acierto direccional (+0.84%) no equivale a rentabilidad del contrato.
Las opciones tienen apalancamiento, theta, IV, y bid/ask spread que este proxy ignora.
`expectancy_proxy` mide edge direccional, no retorno esperado en dólares.

**L4 — N=4 mide solo el mismo día**
Si el movimiento esperado ocurre la sesión siguiente, el proxy reporta fallo aunque el trade
habría ganado. V7 puede tener N_real < 4 (pocas velas restantes).

**L5 — Sin P&L real de opciones (v2 pendiente)**
v2 requeriría historial de bid/ask de opciones o reconstrucción Black-Scholes.
No disponible actualmente. Fuera de alcance.

## Archivos modificados en este sprint

- **Modificado:** `backtest.py` — `medir_outcome()`, `calcular_metricas()`,
  enriquecimiento en `evaluar_dia()`, `"metricas"` en `main()`
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo)

## Historia de sprints de backtest

| Sprint | Contenido |
|---|---|
| BT-001 | Diseño del Backtest Engine (`08-BACKTEST-DESIGN.md`) |
| BT-002 | Harness mínimo: monkey-patches, loop V1→V7, JSON output |
| BT-003 | Primera señal encontrada: AAPL 2026-06-30 GBA |
| BT-004 | Audit de paridad vs producción → D1/D2/D3 identificados |
| BT-005 | Fix D2: `filtradas[:50]` — paridad outputsize con producción |
| BT-006 | Re-audit: D2 cerrado, D1 pendiente, D3 cerrado |
| BT-007 | Diseño del fix D1 (canal snapshot vía HTTP) |
| BT-008 | Fix D1: `cargar_canal_snapshot()` desde `/canal_estado` |
| BT-009 | Audit final de paridad — todos los divergencias cerradas |
| BT-010 | Outcome proxy + métricas agregadas — Backtest v1 completo |

## Último commit antes de este sprint

a236681 — BT-008 Load channel snapshot

## Rama

main

## Próximos sprints sugeridos

### Backtest (continuación opcional)
- **BT-011** — Runner multi-día: iterar sobre rango de fechas, agregar métricas
  acumuladas. Solo loop en `main()`, sin tocar `evaluar_dia()`.
- **BT-012** — Runner multi-símbolo: iterar sobre los 8 símbolos, comparar estrategias.

### Gestión de riesgo (P1, según `07-CORE-READINESS-AUDIT.md`)
- **AX-022** — Stop-loss automático por posición (`pl_pct_actual < -60%`)
- **AX-023** — Límite máximo de posiciones abiertas simultáneas

## Riesgos abiertos en producción

R1 (P1 CRÍTICO): Sin reglas de riesgo de capital — sin stop-loss ni límite de posiciones.
R3 (P1): GTC fijo a 2x sin trailing stop.
R4 (P2): Señal duplicada posible en redeploy entre V7 anticipada y V7 real.

## Notas para quien continúe

- `python3 backtest.py --symbol AAPL --date 2026-06-30` — comando de referencia
- Los `data/bt_velas_*.json` no están en git — deben descargarse del endpoint `/velas`
- El Core Strategy Engine está completo y sin tocar — no modificar sin sprint explícito
- Preferir heredocs (`python3 << 'EOF' ... EOF`) sobre `python3 -c "..."` para pruebas con comillas
- Tras cada deploy: `railway logs --tail 200` y verificar `/status` al menos 2 veces
