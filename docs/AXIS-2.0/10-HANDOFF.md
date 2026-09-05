# AXIS 2.0 — HANDOFF

---

## Estado de reconciliación — 2026-09-05

- **AX-TRACK-AUDIT-007** cubre exclusivamente las sesiones completas del
  2026-08-31 al 2026-09-04, posteriores al corte de `AUDIT-006` (2026-08-28
  16:57 EDT): 42 terminales nuevos, 6 `CLOSED` y 36 `CANCELLED`.
- Los seis cierres están correlacionados exactamente con Portfolio y conservan
  MFE, MAE, duración, vencimiento, `alert_id` y cadena; sus resultados suman
  -$271. Cinco cerraron por vencimiento y uno por GTC.
- Las 36 cancelaciones no abrieron posición: 27 expiraciones de orden, ocho
  contraseñales suprimidas y una revisión Tradier vencida. La única posición
  abierta sigue vinculada a CHAIN-001, con GTC confirmada y sin vencimiento.
- Preflight autenticado y salud verificados: `/version`, `/status`,
  `/alerts/data` y `/portfolio/data` respondieron 200; producción v9.10,
  commit `c162c49`, Railway saludable y seis hilos operativos.

## Estado de reconciliación — 2026-08-29

- **AX-TRACK-AUDIT-006** cubre exclusivamente las sesiones completas del
  2026-08-24 al 2026-08-28, posteriores al corte de `AUDIT-005` (2026-08-22
  10:15 EDT): 55 terminales nuevos, 19 `CLOSED` y 36 `CANCELLED`.
- Los cierres vinculados suman -$5,456; cuatro de 19 fueron ganadores. MFE,
  MAE y duración están presentes en los 19 cierres. El CSV compacto excluye
  secretos, IDs de Telegram y snapshots completos.
- Las cancelaciones incluyen 19 expiraciones de orden, 16 contraseñales
  suprimidas por CHAIN-001 y una señal sin opción. Ninguna cancelación ejecutó
  posición; no hay cierres sin `alert_id`.
- Preflight y salud posteriores verificados: `/version`, `/status`,
  `/alerts/data` y `/portfolio/data` autenticadas respondieron 200; producción
  v9.10, Railway saludable, cinco posiciones abiertas CHAIN-001 con GTC
  confirmada y sin vencimientos.

## PROJECT STATUS

| Campo | Valor |
|---|---|
| **Estado** | PRODUCTION ACTIVE — TRACKING VALIDATION |
| **Versión actual** | v8.99 |
| **Commit producción** | `d55b8e1` — AX-RISK-001 |
| **Build producción** | 2026-08-11 22:44 UTC |
| **Core** | Frozen |
| **Backtest** | BT-001 → BT-011 COMPLETED |
| **Producción** | Running (Railway), `/version` y `/status` OK |
| **Universo** | 10 activos: SPY, AAPL, BA, GLD, NVDA, AMZN, GOOG, META, MU, SPCX |
| **Último sprint** | AX-RISK-001 — telemetría de salidas sombra |
| **Alert Lifecycle** | 191 expedientes: 26 ACTIVE, 87 CLOSED, 78 CANCELLED |
| **Portfolio observado** | 25 posiciones abiertas: todas vinculadas a alerta e ID Tradier; 6 registros anulados/excluidos de métricas |
| **AX-TUNE-001A** | COMPLETED — reporte diario de señales (`tools/daily_signal_review.py`) |
| **AX-TUNE-001B** | COMPLETED — automated daily debrief (`axis_debrief.html`, `/daily_debrief/*`, Telegram 16:10) |
| **AX-TUNE-002A** | COMPLETED — root cause engine v1: anomalías estructuradas (CONFLICTO_DIRECCION, MULTIPLES_ESTRATEGIAS, SIMBOLO_SOBREACTIVO, ESTRATEGIA_DOMINANTE, SEÑAL_TARDIA) con prioridad ALTA/MEDIA/BAJA y accion_recomendada. Telegram filtra solo ALTA+MEDIA. |
| **AX-STATS-001** | COMPLETED — cohorte 1VR trazable validada; sin cambios de estrategia autorizados por la muestra |
| **Última verificación** | 2026-08-11 18:44 EDT — v8.99, 5 hilos vivos, Railway OK, 25 posiciones abiertas intactas |

### Seguridad del plano de control — AX-SEC-001

- Todas las APIs internas requieren `X-AXIS-Admin-Token`; no existen claves por
  defecto ni secretos en query strings.
- El webhook de Telegram valida su secreto oficial y el chat autorizado.
- Las mutaciones administrativas usan POST y CORS solo permite el dominio AXIS.
- Las dashboards internas piden el token una vez por sesión de navegador.
- Derby móvil usa `/mobile`: un código de 10 minutos se aprueba únicamente por
  mensaje directo de la cuenta creadora al bot y entrega una cookie `HttpOnly`
  de 30 días. El token administrativo no se muestra ni se comparte; `/axis revoke`
  en el chat privado del bot invalida todas las sesiones móviles.

### Integridad de ejecución — AX-FIX-EXEC-001

- Una posición se crea únicamente si la compra de Tradier devuelve HTTP 2xx e
  ID de orden; errores, rechazos y respuestas sin ID se cancelan sin Portfolio.
- La confirmación del GTC de salida se registra por separado: una compra real
  sin GTC queda visible como excepción, nunca se oculta ni se trata como fallo
  de compra.
- La reconciliación protegida tiene dry-run por defecto y anula de forma
  auditable solo el incidente documentado desde 2026-08-03, sin `alert_id` ni
  `tradier_orden_id`; deja intacto cualquier legacy ambiguo y excluye los
  anulados de P&L, tasa de acierto y tuning.
- Post-deploy: se anularon cuatro registros abiertos del 2026-08-05 y se
  excluyeron dos cierres del 2026-08-03. La segunda vista previa quedó vacía;
  el registro legacy ambiguo de 2026-06-12 no fue alterado.

### Estadísticas de ciclo de vida — AX-STATS-001

- Corte: 2026-08-11 16:43 EST. Cohorte 1VR trazable: 112 alertas, 61 cerradas
  y vinculadas, 10 activas y vinculadas, 41 canceladas (33 expiradas, 2 sin
  opción y 6 fallos de ejecución históricos ya excluidos).
- Los 61 cierres son 31 GTC ganadores y 30 vencimientos perdedores: 50.8% de
  acierto, P&L promedio +19.5%, MFE promedio +87.3%, MAE promedio -66.1% y
  duración mediana 10,451 min. Los resultados son coherentes con un GTC 2x.
- La muestra tiene solo 12 fechas de cierre y 4–11 operaciones por activo; es
  suficiente para hipótesis y monitoreo, no para alterar parámetros 1VR ni
  hacer decisiones por activo. BA y GLD son señales de observación, no cambios.

### Riesgo de salida — AX-RISK-001

- Evidencia al corte: 16 de 25 posiciones abiertas estaban por debajo de −50%
  y 11 habían alcanzado MAE ≤ −80%; 69 cierres históricos terminaron ≤ −80%.
  No existe todavía histórico intradía completo de MFE/MAE para simular un
  stop retrospectivo de forma válida.
- v8.99 registra en modo sombra el primer cruce hipotético de −25/−50/−75/−90%
  y los drawdowns de −25/−50% desde un MFE de al menos +25%. No vende, no
  modifica GTC, no manda Telegram adicional y no altera estrategias ni
  posiciones. Esta evidencia decidirá una política futura, no la presupone.

### Estado de reconciliación — 2026-08-15

- AX-TRACK-AUDIT-004 incluye exclusivamente sesiones completas del 2026-08-08
  y 2026-08-10 al 2026-08-14, con 56 resultados terminales nuevos (24 CLOSED
  y 32 CANCELLED) y fecha de corte 2026-08-15 15:54 EDT.
- Producción v9.06 / `772e207` y Railway `OK`; hay siete posiciones abiertas,
  todas vinculadas a `alert_id`, orden Tradier y GTC, sin vencidas ni huérfanas.
- Las métricas MFE/MAE/duración están disponibles para 20 de los 24 cierres;
  cuatro cierres antiguos quedan fuera de la ventana de 20 fichas de
  `/portfolio/data` y se documentan como limitación de visibilidad, no como
  datos estimados.
- La automatización formal quedó reforzada con recuperación idempotente en
  tres ventanas de cada sábado; su salida obligatoria es Markdown + CSV
  versionados y publicados.

### Open Limitations

- **L1** — Canal snapshot no histórico: `cargar_canal_snapshot()` usa el estado actual de producción, no reconstrucción histórica. Afecta estrategias RCB/CNF/4PASOS en backtest.
- **L2** — Outcome proxy: métricas de backtest miden movimiento direccional del subyacente, no P&L real de opciones.
- **L3** — Datos históricos limitados a 40 días (2026-05-04 → 2026-06-30).
- **L4** — 1VR ya permite análisis preliminar con 44 cierres. Las demás
  estrategias siguen con muestras demasiado pequeñas para cambios permanentes.
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
| **AX-TRACK-NOTIFY-001** | Weekly Reconciliation Telegram Delivery | COMPLETED — v8.95 |
| **AX-SEC-001** | Control Plane Hardening | COMPLETED — v8.96 |
| **AX-TRACK-AUDIT-001** | First Internal Reconciliation | COMPLETED — 2026-07-25 |
| **AX-TRACK-AUDIT-002** | Second Incremental Reconciliation | COMPLETED — 2026-08-05 |
| **AX-TRACK-AUDIT-003** | Weekly Incremental Reconciliation | COMPLETED — 2026-08-08 |
| **AX-FIX-EXEC-001** | Prevent positions when Tradier execution fails | COMPLETED — v8.97, reconciliación verificada |
| **AX-STATS-001** | Validate 1VR Lifecycle Statistics | COMPLETED — 2026-08-11 |
| **AX-MOBILE-001** | Secure mobile Derby access | COMPLETED — v8.98, Telegram pairing verified locally and Railway healthy |
| **AX-RISK-001** | Shadow exit-risk telemetry | COMPLETED — v8.99; observación sin stops activos |
| **AX-TUNE-002** | Evidence-based Strategy Improvements | RESEARCH ONLY — acumular 30–40 sesiones y ≥20 cierres por activo antes de cambios |
| **AX-ASSET-002** | Add TSLA to Monitoring Universe | PENDING — include in next approved update |
| **AX-BT-012** | Historical Channel Reconstruction | FUTURE |

### Immediate Objective

AX-RISK-001 está recopilando evidencia de stops y trailing en modo sombra, sin
intervenir órdenes. AX-MOBILE-001, AX-FIX-EXEC-001 y AX-STATS-001 permanecen
validados; la próxima decisión estratégica sigue siendo acumular 30–40
sesiones y ≥20 cierres por activo para AX-TUNE-002. Strategy rules remain frozen.

Latest report:
[`reconciliations/2026-08-15-AX-TRACK-AUDIT-004.md`](reconciliations/2026-08-15-AX-TRACK-AUDIT-004.md)

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
| R1 | P1 EN MEDICIÓN | Sin stop-loss automático; AX-RISK-001 mide cruces sombra antes de decidir una política |
| R3 | P1 EN MEDICIÓN | GTC fijo a 2x sin trailing activo; AX-RISK-001 mide drawdowns desde MFE |
| R4 | RESOLVED | V7 provisional determinística y reintento seguro implementados en v8.87/v8.88 |
| R5 | P1 | 26 posiciones abiertas simultáneamente; no existe evidencia en este handoff de un límite operativo aplicado |
| R6 | P2 | Crecimiento continuo de `axis_portfolio.json` por snapshots cada cinco minutos; ~2.5 MB al 2026-07-25 |
| R7 | P3 | Bug visual de líneas manuales al cambiar de activo; no afecta estrategias ni persistencia |
| R8 | RESOLVED v8.97 | `registrar_posicion()` exige confirmación Tradier; cuatro abiertas fantasma fueron anuladas y dos cierres se excluyeron de métricas |
| R9 | RESOLVED v8.96 | Rutas operativas, webhook y datos internos sin autenticación |

---

## NOTAS PARA QUIEN CONTINÚE

- `python3 backtest.py --all-symbols` — run completo de referencia
- Los `data/bt_velas_*.json` no están en git — descargar del endpoint `/velas` si se necesitan
- El Core Strategy Engine está completo y sin tocar
- Tras cada deploy: verificar `/status` al menos 2 veces con `X-AXIS-Admin-Token`
- `--workers 1` en gunicorn es load-bearing — no cambiar sin rediseñar persistencia de estado
- `axis_bitacora.html` fetch usa paths relativos — solo funciona servida por Flask
- La comunicación operativa para el propietario se realiza por Telegram.
- Cada nueva reconciliación desplegada se resume y entrega automáticamente por
  Telegram. El estado se verifica en `/reconciliation/notification-status`;
  `/data/axis_reconciliation_notify.json` evita envíos duplicados tras reinicios.
- No modificar código, documentación, Git ni producción sin autorización
  específica del propietario.
- No hacer `git push` sin autorización expresa.
- Automatización `AXIS — Reconciliación semanal` activa los sábados a las
  10:00 EST. Tiene autorización permanente y limitada para commit/push del
  reporte semanal, su CSV y esta actualización del handoff. No puede incluir
  código ni otros archivos.
- Este handoff describe estado actual; no reemplaza el Operating Manual.

## Rama

Base `main` en `f42df7d`. Único archivo local no tracked ajeno al sprint:
`AGENTS.md` (preexistente; no modificar ni incluir sin autorización).
