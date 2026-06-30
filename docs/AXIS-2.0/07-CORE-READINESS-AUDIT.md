# AXIS 2.0 — Core Readiness Audit

**Fecha:** 2026-06-30
**Versión:** v8.84
**Sprint:** AX-020
**Estado:** Solo diagnóstico. Sin cambios de código.

---

## 1. Estado actual del Core

### Funciones extraídas de `evaluar_activo()`

| Función | Sprint | Descripción |
|---|---|---|
| `evaluar_1vr_normal` | pre-AX-015 | Primera Vela Roja — activación y alerta |
| `evaluar_rpg_activacion` | pre-AX-015 | RPG — setup en V1 |
| `evaluar_rpg_disparo` | pre-AX-015 | RPG — disparo en V2-V7 |
| `evaluar_gna` | pre-AX-015 | Gap Norte Alcista — V1 y V2-V7 |
| `evaluar_gba` | pre-AX-015 | Gap Bajista Alza — V1 y V2-V7 |
| `evaluar_canal_v1` | pre-AX-015 | Canal RCB/CNF — setup en V1 |
| `evaluar_pm40_v1` | AX-015 | PM40 — setup en V1 |
| `evaluar_pm40_v2_v7` | AX-016 | PM40 — evaluación V2-V7, alerta CALL |
| `evaluar_4pasos_v1` | AX-017 | 4PASOS — setup P1 en V1 |
| `evaluar_4pasos_v2_v7` | AX-018 | 4PASOS — P2 + disparo señal PUT |
| `evaluar_canal_v2_v7` | AX-019 | Canal RCB/CNF — P2 dinámico + ruptura CALL |

### `evaluar_activo()` como orquestador limpio

El cuerpo actual de `evaluar_activo()` es exclusivamente llamadas — cero lógica inline:

```
V1:   1VR → RPG → GNA → GBA → Canal → PM40 → 4PASOS → return
V2-7: RPG → GNA → GBA → Canal → PM40 → 4PASOS → print
```

Funciones de soporte internas (no extraídas a módulo, viven en `server.py`):
- `preparar_contexto_vela` — normaliza hora, vela actual, OHLC
- `reset_diario_si_aplica` — detecta nueva fecha y reconstruye estado
- `calcular_techo_canal` / `calcular_piso_mitad_canal` — geometría del canal
- `velas_mercado_entre` — conteo de velas entre timestamps
- `verificar_slope_4ps` — validación de slope para 4PASOS

### Módulos separados (axis_*.py)

| Módulo | Contenido |
|---|---|
| `axis_config.py` | Constantes: EST, TRADIER_BASE, ORDEN_TIMEOUT_MIN, flags de estrategia |
| `axis_channels.py` | Estructura canal_vacio, CANALES_DEFAULT |
| `axis_market.py` | Lógica de mercado, horarios |
| `axis_orders.py` | Gestión de órdenes pendientes |
| `axis_portfolio.py` | Portfolio, Reto Millonario, DERBY_CABALLOS |
| `axis_storage.py` | I/O JSON: velas, señales, estado, canales |
| `axis_telegram.py` | enviar_telegram |
| `axis_tradier.py` | get_precio_tradier, get_opcion_tradier, ejecutar_orden_tradier |

---

## 2. Riesgos funcionales reales

### R1 — Sin reglas de riesgo de capital (P1 CRÍTICO)
No existe límite de pérdida diaria, máximo de posiciones abiertas simultáneas, ni tope de capital por operación. Hoy hay 8 posiciones abiertas con algunas a -89% y -77%. El sistema seguiría abriendo nuevas posiciones sin frenarse. **Impacto directo en dinero.**

### R2 — Posiciones vencidas o bajo el agua sin salida automática (P1)
`loop_polling_posiciones` cierra por GTC o vencimiento, pero no hay stop-loss dinámico. Una posición puede caer de $3.80 a $0.41 (AMZN, -89%) y el sistema la mantiene abierta esperando el GTC de 2x que nunca llegará. No hay regla de "cerrar si pierde más de X%".

### R3 — GTC fijo a 2x entrada: sin trailing stop (P1)
El único exit plan es GTC a 2× el ask. Si la posición sube a +80% y vuelve a 0%, el sistema no lo cierra — espera el GTC. Un trailing stop o cierre parcial a 50% capturaría ganancias reales.

### R4 — Señal duplicada V7 anticipada / V7 real (P2)
`evaluar_v7_anticipada()` corre a las 3:58 y llama `evaluar_activo` para SPY + otros símbolos. Si la señal se dispara a las 3:58 y `_fired` se marca, la evaluación real de las 4:00 no re-dispara — eso está protegido. **Sin embargo**, si el deploy ocurre justo entre 3:58 y 4:00, el estado en memoria se reinicia y ambas evaluaciones pueden disparar. Riesgo bajo pero real en redeploys en cierre.

### R5 — `historial_lows` potencialmente indefinido en 4PASOS (P2)
En `evaluar_4pasos_v2_v7`, la variable `historial_lows` se define en la rama `elif ed["4ps_p2_idx"] is None:` pero se referencia también en la rama `elif ed["4ps_p2_idx"] is not None:` (Casos A y C). Python raise `NameError` si esta segunda rama ejecuta sin que la primera haya corrido previamente en la misma llamada. Latente, no ha causado crash visible porque la condición es infrecuente, pero es un bug real.

### R6 — Sin backtesting contra historial (P2)
`axis_señales_historicas.json` registra señales disparadas pero no su resultado real (P&L) de forma sistemática. Las métricas de win rate existen en `/portfolio/claude` y en el endpoint de analytics pero son manuales y sólo para posiciones cerradas en papel. No hay backtesting automatizado contra datos históricos reales.

### R7 — `axis_velas_<SYMBOL>.json` como único cache de datos (P3)
Si el archivo se corrompe o el volumen de Railway falla, no hay fallback. El sistema simplemente no evalúa ese símbolo (retorna `None` en `preparar_contexto_vela`). No hay alerta ni reintento automatizado.

---

## 3. Qué falta para AXIS 2.0 "100% operativo"

| Área | Estado actual | Qué falta |
|---|---|---|
| **Motor de estrategia** | ✅ Completo — 11 funciones extraídas, orquestador limpio | — |
| **Módulos separados** | ✅ 8 módulos axis_*.py en producción | — |
| **Cierre de posiciones** | ⚠️ Solo GTC 2x o vencimiento | Stop-loss dinámico o cierre por % de caída |
| **Reglas de riesgo** | ❌ No existen | Límite diario de pérdida, max posiciones, max capital por trade |
| **Backtesting** | ❌ No existe | Replay de historial con señales contra precios reales |
| **Métricas de rendimiento** | ⚠️ Existe en `/portfolio` pero manual | Dashboard automático: win rate, P&L promedio, drawdown por estrategia |
| **Bug 4PASOS historial_lows** | ❌ Latente | Fix de la referencia indefinida en rama `p2 is not None` |
| **Revisión de alertas** | ⚠️ Todo llega a Telegram | Filtro de calidad: no disparar señal si mercado está en condición adversa global |
| **AI second opinion** | ⚠️ Existe `/portfolio/claude` pero manual | Integración automática opcional en señales de alta convicción |

---

## 4. Prioridad recomendada

### P1 — Impacta dinero o riesgo directo
1. **Stop-loss por posición** — cerrar automáticamente si P&L cae por debajo de -60% (o umbral configurable)
2. **Límite de posiciones abiertas simultáneas** — máximo configurable (ej. 6), no abrir más hasta que cierre alguna
3. **Fix bug `historial_lows`** — agregar `historial_lows = ed.get("4ps_historial_lows", [])` al inicio del bloque `elif p2 is not None` en `evaluar_4pasos_v2_v7`

### P2 — Mejora estrategia o previene errores silenciosos
4. **Métricas automáticas por estrategia** — win rate, P&L promedio, drawdown calculados al cerrar cada posición y expuestos en `/metricas`
5. **Trailing stop o cierre parcial** — cerrar 50% al llegar a +50%, dejar correr el resto

### P3 — Nice to have
6. **Backtesting** — replay de señales contra historial de velas almacenado
7. **Filtro global de mercado** — no disparar PUT en día con gap alcista extremo (>2%) en SPY
8. **AI second opinion automático** — llamar a Claude antes de ejecutar si la posición supera X contratos

---

## 5. Próximos 5 sprints recomendados

### AX-021 — Fix bug `historial_lows` en 4PASOS
**P1. ~30 minutos.**
En `evaluar_4pasos_v2_v7`, agregar `historial_lows = ed.get("4ps_historial_lows", [])` al inicio del bloque `elif ed["4ps_p2_idx"] is not None:`. Elimina el `NameError` latente. Un solo Edit, py_compile, commit.

### AX-022 — Stop-loss automático por posición
**P1. ~1 hora.**
En `loop_polling_posiciones`, al actualizar `pl_pct_actual`, si `pl_pct_actual < -60` (o constante `STOP_LOSS_PCT` en `axis_config.py`), llamar `cerrar_posicion(pos_id, bid, "stop_loss")`. Notificar via Telegram con emoji de alerta. Sin tocar el flujo GTC ni vencimiento.

### AX-023 — Límite máximo de posiciones abiertas
**P1. ~30 minutos.**
En `enviar_senal_con_botones`, antes de publicar el mensaje Telegram con botones EJECUTAR, verificar `len([p for p in _portfolio["posiciones"] if p["estado"]=="abierta"]) >= MAX_POSICIONES` (constante en `axis_config.py`, default 6). Si se supera, loggear y no enviar la alerta de ejecución (o enviar solo como FYI sin botones de ejecución).

### AX-024 — Endpoint `/metricas` automático
**P2. ~1 hora.**
Nueva ruta Flask `/metricas` que calcula sobre posiciones cerradas: win rate, P&L promedio, drawdown máximo y máximo consecutivo de pérdidas — desglosados por estrategia y por activo. Sin estado nuevo — lee `_portfolio["historico"]` que ya existe. Útil para evaluar qué estrategias realmente funcionan.

### AX-025 — Cierre parcial al 50% de ganancia
**P2. ~1 hora.**
En `loop_polling_posiciones`, si `pl_pct_actual >= 50` y la posición tiene más de 1 contrato y no tiene flag `parcial_cerrado`, cerrar la mitad de contratos al precio bid actual y marcar `parcial_cerrado: True`. Registrar en `historial_precios` de la posición. Requiere llamada a Tradier para vender N/2 contratos.

---

## Resumen ejecutivo

El **Core Strategy Engine está completo**: `evaluar_activo()` es un orquestador de 12 líneas que delega todo a funciones nombradas. El sistema está en producción, estable, generando señales y ejecutando órdenes paper en Tradier sandbox.

Lo que impide llamarlo "100% operativo para trading real" no es el motor de estrategia — es la **gestión de riesgo**. Hay posiciones abiertas a -89% sin salida automática, no existe tope de pérdida diaria, y el único exit plan es un GTC de 2x que puede nunca llegar.

Los próximos 3 sprints (AX-021, AX-022, AX-023) son todos P1, pequeños, y sin riesgo de regresión — no tocan el motor de estrategia.
