# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

AXIS Breakout Sentinel — a single-process Flask app that watches intraday price action for a fixed
list of equities, detects a set of hand-coded breakout/reversal patterns, and pushes trade alerts (with
Telegram inline buttons to execute/skip) that place paper option orders on Tradier sandbox. It also
tracks a virtual options portfolio ("Reto Millonario" — 10 capital lanes that compound or get
eliminated) and serves a few static HTML dashboards that read from its own JSON API.

There is no test suite, no build step, and no package beyond `server.py` + four static HTML files.
Everything — strategy logic, persistence, Telegram bot, Tradier client, Flask routes, and even the
HTML for the landing page — lives in `server.py` (~3500 lines). Treat it as a single deployable unit.

## Running it

```bash
pip install -r requirements.txt
python server.py            # dev server on $PORT or 5000
```

Production runs on Railway via the `Procfile`:
```
web: gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1
```
**`--workers 1` is load-bearing** — all strategy/channel/portfolio state lives in in-process Python
dicts (`estado_dia`, `canal`, `_portfolio`, `ordenes_pendientes`). Running more than one worker would
split state across processes and break everything silently. Don't change this without redesigning
state storage.

No automated tests or linter are configured. Verify changes by hitting the running server's
diagnostic routes (see below) rather than writing unit tests for this codebase.

## Required environment variables

- `TRADIER_TOKEN`, `TRADIER_ACCOUNT` — Tradier **sandbox** (paper trading orders)
- `TRADIER_TOKEN_REAL` — Tradier **production** (read-only market data: quotes, history, timesales)
- `ANTHROPIC_API_KEY` — powers `/portfolio/claude` and Reto fallback recommendations
- `AXIS_PASSWORD` — gates `/source/<filename>` (defaults to `axis2026` if unset)
- Telegram bot token / chat ID and TwelveData/Finnhub keys are currently hardcoded constants near the
  top of `server.py` (`TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `TWELVEDATA_KEY`, `FINNHUB_KEY`) rather than
  env vars — TwelveData/Finnhub are vestigial (TwelveData was migrated off in v8.17; see file header).

## Persistence

Everything persists as flat JSON files under `/data` (a Railway volume — won't exist in a plain local
checkout unless you create it or change `DATA_DIR`/`*_FILE` constants):

| File | What |
|---|---|
| `axis_canales.json` | Per-symbol channel state (P1/P2/P3 anchor points) |
| `axis_portfolio.json` | Open positions, closed history, Reto Millonario lanes |
| `axis_ordenes.json` | Pending Telegram exec/skip orders (15 min TTL) |
| `axis_estado_dia.json` | Today's per-symbol strategy state (only kept if `fecha` matches today) |
| `axis_señales_historicas.json` | Archived daily signal log, keyed by date |
| `axis_bitacora.json` | Free-form dev log/changelog, written by `/bitacora/*` routes |
| `axis_velas_<SYMBOL>.json` | Local OHLC bar cache (15min + daily), one file per symbol |

State is loaded once at startup (`arrancar_monitor()`, 5s after boot) and every mutation immediately
calls the matching `guardar_*()` to survive a Railway restart. When adding a new piece of mutable
state, follow this same load-on-boot / save-on-mutation pattern — there is no database.

## Candle model: "AXIS velas"

The system does not use raw market candles. It pulls Tradier 15-minute bars and re-buckets them into
synthetic hourly "AXIS velas" (V1..V7) per trading day, anchored to specific EST hours:

- **V1** = 9:30 + 9:45 bars (pre-open, 2 bars) — the reference candle for most strategies
- **V2..V7** = the 10:00, 11:00, 12:00, 13:00, 14:00, 15:00 hours (4 bars each)
- SPY closes the session at V7 (~4:15 EST); other symbols close at 4:00 EST — hence the separate "V7
  anticipada" thread that evaluates V7 early at 3:58 and corrects the real close shortly after 4:00.

`get_velas()` (server.py) does this bucketing from the local `axis_velas_<SYMBOL>.json` cache, never
hitting Tradier directly for the bucketed view — `actualizar_velas_local()` / `construir_base_datos_activo()`
are what actually call Tradier's `timesales`/`history` endpoints to keep that cache warm.

## Strategy engine (`evaluar_activo`)

`evaluar_activo(simbolo, velas, ahora)` is the core decision function, called once per symbol per
hour by `reporte_horario()` (driven by `monitor_loop()`'s hourly tick during market hours) and also
re-run synthetically by the V7-anticipada thread. It is **stateful per symbol** via the `estado_dia[simbolo]`
dict, which tracks which signals have already fired today (`*_fired` flags) so each one only triggers once.

Strategies implemented (each maps to a Telegram alert with EJECUTAR/IGNORAR buttons):

- **1VR / 1VR+** — first V1 candle closes red; fires PUT alert if either inside a channel's RCB 30%
  zone (→ "1VR+") or SMA40 > SMA20 (→ "1VR")
- **RPG / RPG+** — gap-up V1 (verde) that later breaks back below its own low (the "piso")
- **GNA** — gap-up V1 with SMA20 > SMA40, confirmed by a strict bullish candle closing above V1
- **GBA** — gap-down V1 that still closes bullish later, same confirmation rule
- **RCB / CNF** — "channel" breakout. A channel is two anchor points P1 (resistance high) and P2 (an
  earlier point the slope is drawn through); RCB also has a P3 floor point, CNF doesn't. The
  "ceiling" (`techo`) is a straight line projected from P1 through P2 across market-hour candle
  counts (`calcular_techo_canal`/`velas_mercado_entre`). P2 walks forward automatically ("P2
  dinámico") whenever a non-bullish candle's high pokes above the ceiling without breaking it.
- **PM40** — bearish channel breakout that doesn't use the P1/P2/P3 channel struct; builds its own P1
  (local high) / P2 pivots from scratch once SMA20>SMA40>SMA100>SMA200 alignment holds
- **4PASOS** — the bearish mirror of PM40 but for an active RCB channel, using internal support pivots
- **HED** — daily-candle shooting-star pattern, evaluated once a day (not per-hour) by `evaluar_hed()`

A **"vela alcista estricta"** (strict bullish candle) — body ≥15% of range and upper wick ≤75% of body —
is the recurring confirmation filter used to avoid firing on weak/wicky candles. Most strategies that
need a "confirmed breakout" reuse this exact predicate; if you add a new strategy with the same shape
of confirmation, reuse `v_alcista` rather than inventing another threshold.

When the day's first evaluation lands mid-history (e.g. after a redeploy), `evaluar_activo` replays
state by re-deriving V1 from the historical bars before evaluating the live candle — see the "Reset
diario" block. Any change to a strategy's *firing* condition should be mirrored in that reconstruction
block too, or replayed days will fire inconsistently with live days (this caused the v8.62 1VR fix).

## Order/alert flow

1. A strategy fires → `enviar_senal_con_botones()` fetches a live price, picks a near-the-money option
   via `get_opcion_tradier()` (strike offset by a tiered OTM % based on underlying price, expiration
   ≥7 days out), and sends a Telegram message with **EJECUTAR / IGNORAR** (and **RETO Cn** if the Reto
   is active) inline buttons. The pending order sits in `ordenes_pendientes` (TTL 15 min, persisted).
2. `/telegram_webhook` receives the callback (`exec:<id>`, `skip:<id>`, `reto:<id>:<carril>`), places
   the real Tradier sandbox order (buy_to_open market, then a GTC sell_to_close limit at 2x ask), and
   calls `registrar_posicion()` to add it to the portfolio.
3. `loop_polling_posiciones()` (every 5 min during market hours) checks each open position's GTC order
   status and expiration date, closing the position via `cerrar_posicion()` when the GTC fills or the
   contract expires.
4. `loop_limpiar_ordenes()` (every 60s) expires unanswered pending orders after 15 minutes and edits
   the original Telegram message to say so.

"Reto Millonario" is a separate 10-lane capital-compounding game layered on the same signals: each
lane starts at whatever the first contract costs, reinvests 80% of capital on each subsequent signal,
and gets `eliminado` (eliminated) below a $280 capital floor. Lane assignment round-robins via
`turno_actual`.

## HTTP surface

All state-mutating/diagnostic routes are plain `GET` query-param endpoints (no auth except `/source`),
designed to be hit by hand, by the dashboards, or by an AI agent reading `/bitacora/data`. Notable ones
beyond the obvious CRUD-ish routes:

- `/status` — single largest diagnostic payload: threads alive, channel state, today's fired signals,
  open positions, Reto summary, local file sizes, candle-cache health per symbol. Check this first
  when debugging a "why didn't X fire" question.
- `/diagnostico?simbolo=&fecha=` — replays a specific symbol/date's candles and explains exactly which
  strategy conditions were/weren't met, without sending any Telegram alert or placing orders.
- `/canal_lineas?activo=` / `/canal_estado` — what the dashboards poll to draw the channel ceiling/mid/
  floor lines; computed server-side so the chart always matches what the evaluator actually used.
- `/source/<filename>?key=...` — serves raw source of `server.py` and the HTML dashboards for AI
  agents to read directly from the deployed instance (password gated via `AXIS_PASSWORD`).
- `/bitacora/*` — a JSON-backed changelog/task log (`axis_bitacora.json`) read by `axis_bitacora.html`
  and by `/bitacora/data`, which embeds `instrucciones_ai` telling any connecting AI: **converse and
  get Noel's approval before making changes, one change at a time, verify via `/status` after each
  deploy.** Honor that instruction if you're operating against the live deployment.

## Frontend dashboards

`axis_charts.html`, `axis_portfolio.html`, `axis_analisis.html`, `axis_bitacora.html` are standalone
static pages (no build step, no framework) served directly by Flask routes (`/charts`, `/portfolio`,
`/analisis`, `/bitacora`). Each hardcodes the production backend URL as a `RAILWAY` JS constant
(`https://web-production-bf9d0.up.railway.app`) and talks to it via `fetch` — so **editing these files
locally and opening them in a browser still hits the live production API**, not localhost, unless you
edit `RAILWAY` first. `axis_bitacora.html` is the exception — it fetches relative paths (`/bitacora/...`),
so it only works when actually served by the Flask app it's requesting from.

## Versioning convention

The file header docstring in `server.py` is a running changelog (v8.x) — read it before making changes
to understand the most recent intentional fixes, and append a one-line entry there (plus bump the
version string referenced in a few HTML titles/footers and `axis_bitacora.json`'s `versiones` block)
when you change behavior, matching the existing terse Spanish style.
