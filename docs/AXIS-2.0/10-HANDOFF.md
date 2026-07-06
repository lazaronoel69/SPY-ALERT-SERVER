# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. **Backtest Engine v1 COMPLETO** (BT-001 a BT-011).
Core Strategy Engine intacto — cero cambios a server.py durante toda la fase de backtest.

## Cambio realizado en este sprint

**Sprint BT-011 — Multi-day Multi-symbol Runner**

Completada la última pieza del Backtest Engine v1. Cambios en `backtest.py`:

- `SYMBOLS` — lista de los 8 símbolos del sistema
- `_canal_raw` — cache de la respuesta HTTP de `/canal_estado` (1 llamada por proceso,
  no 1 por día; elimina ~312 llamadas redundantes en run completo)
- `fechas_disponibles(symbol, start, end)` — extrae fechas únicas del archivo local
  `bt_velas_<SYMBOL>.json` filtradas por rango
- `run_multi(symbols, start, end)` — runner principal; itera símbolos × fechas llamando
  exactamente `evaluar_dia()` sin duplicar lógica; agrega métricas globales + por_simbolo
- `main()` extendido con `--all-symbols`, `--start`, `--end`; modo single-day intacto

**Ningún cambio a server.py ni al Core.**

## Modos de uso

```bash
# Single day (comportamiento original)
python3 backtest.py --symbol AAPL --date 2026-06-30

# Todos los símbolos, todos los días disponibles
python3 backtest.py --all-symbols

# Rango de fechas
python3 backtest.py --all-symbols --start 2026-06-01 --end 2026-06-30

# Un símbolo, rango de fechas
python3 backtest.py --symbol AAPL --start 2026-06-01 --end 2026-06-30
```

## Resultados del run completo (8 símbolos × 40 días = 320 días)

Run: 2026-05-04 a 2026-06-30, todos los símbolos.

| Métrica | Valor |
|---|---|
| Total días evaluados | 320 |
| Total señales | 253 |
| Señales con outcome | 247 |
| Tasa de acierto | 50.2% |
| Expectancy proxy | -0.027 |

### Por estrategia

| Estrategia | Señales | Tasa | Fav avg | Adv avg |
|---|---|---|---|---|
| RPG+ | 9 | 77.8% | +0.886% | -0.556% |
| RPG | 33 | 69.7% | +0.998% | -1.017% |
| 1VR+ | 3 | 66.7% | +0.331% | -0.452% |
| GNA+2 | 5 | 60.0% | +1.140% | -0.781% |
| GBA | 18 | 50.0% | +1.018% | -0.986% |
| GNA | 8 | 50.0% | +0.606% | -0.858% |
| 1VR | 144 | 46.5% | +1.364% | -1.457% |
| GBA+2 | 27 | 33.3% | +1.111% | -0.840% |

### Por símbolo

| Símbolo | Señales | Tasa | Expectancy |
|---|---|---|---|
| AAPL | 31 | 63.3% | +0.344 |
| GLD | 32 | 59.4% | +0.241 |
| META | 29 | 60.7% | +0.058 |
| AMZN | 33 | 46.9% | -0.096 |
| SPY | 30 | 41.4% | -0.110 |
| NVDA | 37 | 44.4% | -0.135 |
| BA | 33 | 42.4% | -0.239 |
| GOOG | 28 | 44.4% | -0.271 |

> **AVISO:** Estas métricas son PROXY DIRECCIONAL del subyacente. No equivalen a P&L real
> de opciones. El apalancamiento, theta, IV y bid/ask spread no están modelados.
> Una tasa de acierto del 50% no implica breakeven real.

## Limitaciones conocidas del Backtest v1

**L1 — Canal no es histórico (la más importante)**
`cargar_canal_snapshot()` usa el estado actual de producción vía `/canal_estado` (cacheado
una vez por proceso). No es reconstrucción histórica. Días afectados por símbolo:
SPY=22, AAPL=24, BA=8, GLD=0, NVDA=20, AMZN=18, GOOG=10, META=22.
Estrategias sin canal (1VR, RPG, GNA, GBA) son 100% correctas históricamente.

**L2 — Ventana de datos: 40 días (2026-05-04 a 2026-06-30)**
8 símbolos. Archivos `data/bt_velas_*.json` no están en git (excluidos en `.git/info/exclude`).

**L3 — Métricas son PROXY, NO P&L real de opciones**
Expectancy_proxy mide edge direccional del subyacente, no retorno en dólares de contratos.

**L4 — N=4 mide solo el mismo día**
Si el movimiento ocurre la sesión siguiente, el proxy reporta fallo aunque el trade ganara.
V7 puede tener N_real < 4.

**L5 — Sin P&L real de opciones (v2 pendiente)**
Requeriría historial de bid/ask o reconstrucción Black-Scholes. Fuera de alcance v1.

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
| BT-010 | Outcome proxy + métricas agregadas |
| BT-011 | Multi-day multi-symbol runner — **Backtest v1 COMPLETO** |

## Archivos modificados en este sprint

- **Modificado:** `backtest.py` — SYMBOLS, canal cache, fechas_disponibles, run_multi, main()
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo)

## Rama

main

## Próximos sprints sugeridos

### Gestión de riesgo (P1, prioridad máxima)
- **AX-022** — Stop-loss automático por posición (`pl_pct_actual < -60%`)
- **AX-023** — Límite máximo de posiciones abiertas simultáneas

### Backtest (mejoras opcionales)
- **BT-012** — Actualizar datos: descargar velas más recientes vía `/velas?simbolo=X&outputsize=N`
- **BT-013** — Reconstrucción histórica del canal (requiere historial de P1/P2 por fecha)

## Riesgos abiertos en producción

R1 (P1 CRÍTICO): Sin reglas de riesgo de capital — sin stop-loss ni límite de posiciones.
R3 (P1): GTC fijo a 2x sin trailing stop.
R4 (P2): Señal duplicada posible en redeploy entre V7 anticipada y V7 real.

## Notas para quien continúe

- `python3 backtest.py --all-symbols` — run completo de referencia
- Los `data/bt_velas_*.json` no están en git — descargar del endpoint `/velas` si se necesitan
- El Core Strategy Engine está completo y sin tocar — no modificar sin sprint explícito
- Preferir heredocs (`python3 << 'EOF' ... EOF`) sobre `python3 -c "..."` para pruebas con comillas
- Tras cada deploy: `railway logs --tail 200` y verificar `/status` al menos 2 veces
