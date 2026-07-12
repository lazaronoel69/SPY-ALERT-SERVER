# AX-ASSET-001 — MU and SPCX

## Objective

Add Micron Technology (`MU`) and Space Exploration Technologies Corp.
(`SPCX`) to the existing AXIS monitoring universe without changing any
strategy rule or threshold.

## Evidence

- Tradier supplies daily and intraday data for both symbols.
- SPCX options are listed and actively traded.
- MU has sufficient historical depth for all current indicators.
- SPCX began trading on 2026-06-12 and initially lacks sufficient AXIS hourly
  history for SMA200/PM40. Existing data guards keep PM40 inactive until the
  required history accumulates; no fallback or fabricated SMA is allowed.

## Integration

- Hourly V1-V6 evaluation and independent V7 evaluation.
- Daily HED evaluation.
- Local candle cache and persistent daily state.
- Telegram alert, option selection and lifecycle tracking.
- Charts, journal, bitacora, backtest and daily review symbol lists.
- Channels start `OFF` with no P1/P2/P3 anchors.

## Acceptance

1. `/status` lists ten assets.
2. MU and SPCX receive local daily and 15-minute caches.
3. Both complete V1-V7 construction when market data is available.
4. Strategy functions remain byte-for-byte equivalent at the AST level.
5. SPCX never fabricates missing SMA200 history.
