# AXIS 2.0 — HANDOFF

---

## PROJECT STATUS

| Campo | Valor |
|---|---|
| **Estado** | PRODUCTION ACTIVE — TRACKING VALIDATION |
| **Versión actual** | v8.94 |
| **Commit producción** | `33d8587` |
| **Build producción** | 2026-07-13 14:00:44 UTC |
| **Core** | Frozen |
| **Backtest** | BT-001 → BT-011 COMPLETED |
| **Producción** | Running (Railway), `/version` y `/status` OK |
| **Universo** | 10 activos: SPY, AAPL, BA, GLD, NVDA, AMZN, GOOG, META, MU, SPCX |
| **Último sprint** | AX-TRACK-004 — seguimiento intradía silencioso y consolidación diaria por Telegram |
| **Alert Lifecycle** | 81 expedientes: 26 ACTIVE, 25 CLOSED, 30 CANCELLED |
| **Portfolio observado** | 26 posiciones abiertas; reconciliación interna aprobada en AX-TRACK-AUDIT-001 |
| **AX-TUNE-001A** | COMPLETED — reporte diario de señales (`tools/daily_signal_review.py`) |
| **AX-TUNE-001B** | COMPLETED — automated daily debrief (`axis_debrief.html`, `/daily_debrief/*`, Telegram 16:10) |
| **AX-TUNE-002A** | COMPLETED — root cause engine v1: anomalías estructuradas (CONFLICTO_DIRECCION, MULTIPLES_ESTRATEGIAS, SIMBOLO_SOBREACTIVO, ESTRATEGIA_DOMINANTE, SEÑAL_TARDIA) con prioridad ALTA/MEDIA/BAJA y accion_recomendada. Telegram filtra solo ALTA+MEDIA. |
| **Última verificación** | 2026-07-25 12:15 EST; mercado cerrado; cinco threads operativos presentes |

### Production Snapshot — 2026-07-25

- Producción ejecuta AXIS v8.94 desde el commit `33d8587`.
- El seguimiento de posiciones funciona aproximadamente cada cinco minutos y
  persiste bid, P&L actual, MFE, MAE, duración y snapshots.
- El último día de mercado disponible es 2026-07-24.
- El 2026-07-24 se registraron seis señales, todas 1VR. El Root Cause Engine
  clasificó la concentración como `ESTRATEGIA_DOMINANTE`, prioridad BAJA,
  acción `MONITOREAR`.
- `/data/axis_portfolio.json` ocupa aproximadamente 2.5 MB. El crecimiento se
  debe en parte a la serie completa de snapshots cada cinco minutos.
- AXIS reporta 26 posiciones abiertas, con vencimientos entre 2026-07-27 y
  2026-07-31. Antes de usar sus resultados para tuning debe verificarse que
  correspondan a las ejecuciones esperadas y que ninguna deba estar cerrada o
  reconciliada.

### Open Limitations

- **L1** — Canal snapshot no histórico: `cargar_canal_snapshot()` usa el estado actual de producción, no reconstrucción histórica. Afecta estrategias RCB/CNF/4PASOS en backtest.
- **L2** — Outcome proxy: métricas de backtest miden movimiento direccional del subyacente, no P&L real de opciones.
- **L3** — Datos históricos limitados a 40 días (2026-05-04 → 2026-06-30).
- **L4** — El historial de producción posterior a AX-TRACK ya mide opciones
  reales de sandbox, pero la muestra sigue siendo temprana y no debe usarse
  todavía para cambios de estrategia sin reconciliación y revisión estadística.
- **L5** — Las líneas manuales del chart están separadas en memoria por activo,
  pero el canvas no se redibuja al cambiar de símbolo; una línea de MU puede
  permanecer visualmente sobre SPCX hasta refrescar o redibujar. Bug
  diagnosticado, no corregido.

---

## NEXT ROADMAP

| Sprint | Nombre | Estado |
|---|---|---|
| **AX-UI-001** | High Visibility Theme | COMPLETED |
| **AX-TUNE-001** | Production Signal Review | COMPLETED (001A + 001B) |
| **AX-TUNE-002A** | Root Cause Engine v1 | COMPLETED |
| **AX-TRACK-001** | Persistent Alert Lifecycle | COMPLETED — v8.89 |
| **AX-TRACK-002** | Active Position Tracking | COMPLETED — v8.90 |
| **AX-FIX-EXP-001** | Expiration Reconciliation | COMPLETED — v8.91 |
| **AX-TRACK-003** | Telegram Operational Updates | COMPLETED — v8.92 |
| **AX-ASSET-001** | Add MU and SPCX | COMPLETED — v8.93 |
| **AX-TRACK-004** | Silent Intraday Tracking | COMPLETED — v8.94 |
| **AX-TRACK-AUDIT-001** | First Internal Reconciliation | COMPLETED — 2026-07-25 |
| **AX-STATS-001** | Validate Lifecycle Statistics | NEXT after more closed outcomes |
| **AX-TUNE-002** | Evidence-based Strategy Improvements | BLOCKED until audit/statistics |
| **AX-ASSET-002** | Add TSLA to Monitoring Universe | PENDING — include in next approved update |
| **AX-BT-012** | Historical Channel Reconstruction | FUTURE |

### Immediate Objective

AX-TRACK-AUDIT-001 confirmed internal consistency across 81 alerts and 26 open
positions. The next objective is to continue collecting terminal outcomes and
produce incremental reconciliations without rebuilding the initial period.
Strategy tuning remains blocked until each strategy has a materially larger
closed sample.

Baseline report:
[`reconciliations/2026-07-25-AX-TRACK-AUDIT-001.md`](reconciliations/2026-07-25-AX-TRACK-AUDIT-001.md)

### AX-TUNE-001 — Production Signal Review
Revisar señales reales disparadas en producción (últimas 4-6 semanas). Identificar patrones de falsos positivos por estrategia. Input requerido para AX-TUNE-002.

### AX-TUNE-002A — Root Cause Engine v1
Anomalías estructuradas en el Daily Debrief. Cinco tipos: CONFLICTO_DIRECCION (ALTA), MULTIPLES_ESTRATEGIAS (MEDIA), SIMBOLO_SOBREACTIVO (MEDIA), ESTRATEGIA_DOMINANTE (BAJA), SEÑAL_TARDIA (BAJA). Cada anomalía incluye `motivo_corto`, `motivo_detallado`, `accion_recomendada` (REVISAR_GRAFICO/MONITOREAR/SIN_ACCION). Telegram solo muestra ALTA y MEDIA. No toca estrategias ni motor.

### AX-TUNE-002 — Evidence-based Strategy Improvements
Toda mejora a parámetros de estrategia debe basarse en datos de AX-TUNE-001 o resultados de Backtest. Sin cambios subjetivos.

### AX-BT-012 — Historical Channel Reconstruction
Requiere historial de P1/P2 por fecha. Fuera de alcance hasta tener ese historial disponible.

---

## ENGINEERING RULES

1. **Ninguna estrategia se modifica sin evidencia.** Toda modificación requiere revisión de señales reales (AX-TUNE-001) o resultados de Backtest verificados.
2. **Toda modificación requiere revisión de señales reales o Backtest.** No se aceptan cambios basados en intuición o preferencia.
3. **No hacer refactors innecesarios.** Si el código funciona en producción y no hay bug documentado, no se toca.
4. **No tocar Core sin autorización explícita.** `evaluar_activo()` y todas las funciones de estrategia son off-limits sin sprint explícito y aprobado.
5. **Mantener `server.py` como fuente única del motor.** La lógica de estrategia vive ahí y solo ahí. No duplicar en backtest, frontend ni módulos auxiliares.

---

## BACKTEST ENGINE v1

**STATUS: COMPLETE**

Sprint BT-001 → BT-011. El motor de backtest reutiliza `evaluar_activo()` sin duplicar lógica.

### Uso

```bash
# Single day
python3 backtest.py --symbol SPY --date 2026-06-30

# Todos los símbolos, todos los días disponibles
python3 backtest.py --all-symbols

# Rango de fechas
python3 backtest.py --all-symbols --start 2026-06-01 --end 2026-06-30

# Un símbolo, rango de fechas
python3 backtest.py --symbol AAPL --start 2026-06-01 --end 2026-06-30
```

### Resultados del run completo (8 símbolos × 40 días = 320 días)

Run: 2026-05-04 a 2026-06-30.

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

> **AVISO:** Métricas son PROXY DIRECCIONAL del subyacente. No equivalen a P&L real de opciones.

### Historia de sprints

| Sprint | Contenido |
|---|---|
| BT-001 | Diseño del Backtest Engine (`08-BACKTEST-DESIGN.md`) |
| BT-002 | Harness mínimo: monkey-patches, loop V1→V7, JSON output |
| BT-003 | Primera señal encontrada: AAPL 2026-06-30 GBA |
| BT-004 | Audit de paridad vs producción — D1/D2/D3 identificados |
| BT-005 | Fix D2: `filtradas[:50]` — paridad outputsize con producción |
| BT-006 | Re-audit: D2 cerrado, D1 pendiente, D3 cerrado |
| BT-007 | Diseño del fix D1 (canal snapshot vía HTTP) |
| BT-008 | Fix D1: `cargar_canal_snapshot()` desde `/canal_estado` |
| BT-009 | Audit final de paridad — todas las divergencias cerradas |
| BT-010 | Outcome proxy + métricas agregadas |
| BT-011 | Multi-day multi-symbol runner — **Backtest v1 COMPLETE** |

---

## UI FIXES

| Sprint | Fix | Estado |
|---|---|---|
| AX-FIX-002 | "EN FORMACIÓN" label aparecía en última vela completa | RESOLVED — commit `478e553` |
| AX-UI-001 | High Visibility Chart Theme | COMPLETED — commit `31cf336` |
| AX-UI-DRAW-001 | Línea manual permanece visualmente al cambiar de activo | DIAGNOSED — pending authorization |

---

## RIESGOS ABIERTOS EN PRODUCCIÓN

| ID | Prioridad | Descripción |
|---|---|---|
| R1 | P1 CRÍTICO | Sin stop-loss automático — posición puede caer indefinidamente |
| R3 | P1 | GTC fijo a 2x sin trailing stop |
| R4 | RESOLVED | V7 provisional determinística y reintento seguro implementados en v8.87/v8.88 |
| R5 | P1 | 26 posiciones abiertas simultáneamente; no existe evidencia en este handoff de un límite operativo aplicado |
| R6 | P2 | Crecimiento continuo de `axis_portfolio.json` por snapshots cada cinco minutos; ~2.5 MB al 2026-07-25 |
| R7 | P3 | Bug visual de líneas manuales al cambiar de activo; no afecta estrategias ni persistencia |

---

## NOTAS PARA QUIEN CONTINÚE

- `python3 backtest.py --all-symbols` — run completo de referencia
- Los `data/bt_velas_*.json` no están en git — descargar del endpoint `/velas` si se necesitan
- El Core Strategy Engine está completo y sin tocar
- Tras cada deploy: verificar `/status` al menos 2 veces
- `--workers 1` en gunicorn es load-bearing — no cambiar sin rediseñar persistencia de estado
- `axis_bitacora.html` fetch usa paths relativos — solo funciona servida por Flask
- La comunicación operativa para el propietario se realiza por Telegram.
- No modificar código, documentación, Git ni producción sin autorización
  específica del propietario.
- No hacer `git push` sin autorización expresa.
- Este handoff describe estado actual; no reemplaza el Operating Manual.

## Rama

`main`, sincronizada con `origin/main` al 2026-07-25. Único archivo local no
tracked observado: `AGENTS.md` (preexistente; no modificar ni incluir sin
autorización).
