# AXIS 2.0 — ARCHITECTURE AUDIT

**Sprint:** AX-011 | **Fecha:** 06/26/2026 | **Base:** server.py v8.84, post-AX-010 (commit e199ef7)

> Auditoría puramente documental. No se modificó ningún código durante su creación.

---

## 1. TAMAÑO ACTUAL

### server.py
- **Líneas:** 3,370
- **Tamaño:** 160 KB

### Módulos axis_*.py (creados en AX-003 a AX-010)

| Módulo | Líneas |
|---|---|
| axis_market.py | 367 |
| axis_tradier.py | 253 |
| axis_channels.py | 125 |
| axis_portfolio.py | 106 |
| axis_orders.py | 81 |
| axis_storage.py | 79 |
| axis_config.py | 50 |
| axis_telegram.py | 34 |
| **Total módulos** | **1,095** |
| **Total sistema (server.py + módulos)** | **4,465** |

**Lectura:** después de 7 sprints de modularización (AX-003 a AX-010), los módulos extraídos representan aproximadamente el **24.5%** del código total (1,095 de 4,465 líneas). server.py sigue siendo el 75.5% restante.

---

## 2. MÓDULOS ACTUALES Y SU RESPONSABILIDAD

| Módulo | Responsabilidad |
|---|---|
| **axis_config.py** | Constantes simples: zona horaria (EST), lista de activos, horarios de reporte, switches de estrategia, rutas de archivos de persistencia, URLs base de Tradier. Sin lógica, sin funciones más allá de los valores. |
| **axis_tradier.py** | Acceso puro a la API de Tradier sandbox: buscar opciones, ejecutar órdenes (compra + GTC venta), cancelar órdenes, consultar bid/precio. Sin dependencia de Telegram, Portfolio, ni Derby. |
| **axis_storage.py** | Persistencia JSON de bajo riesgo: señales históricas, estado del día (recibe el dict como parámetro), velas locales por activo (cargar/guardar/ruta). |
| **axis_telegram.py** | Mensajería simple de Telegram: solo `enviar_telegram()` (texto plano, sin botones). |
| **axis_orders.py** | Persistencia de órdenes pendientes (`ordenes_pendientes`): guardar/cargar desde JSON, recibiendo el dict como parámetro. |
| **axis_portfolio.py** | Estructura y persistencia básica del portfolio: `DERBY_CABALLOS`, `portfolio_vacio()`, cargar/guardar portfolio (con migración reto→derby incluida). |
| **axis_channels.py** | Estructura y persistencia básica de canales bajistas: `canal_vacio()`, `CANALES_DEFAULT`, guardar/cargar canales (recibiendo `canal`/`ACTIVOS` como parámetros). |
| **axis_market.py** | Construcción y actualización de velas locales: descarga de Tradier, agrupación en velas AXIS V1-V7, la regla del `:01`, base de datos diaria. Recibe `es_dia_mercado`/`restar_dias_habiles` como parámetro para evitar import circular con server.py. |

---

## 3. FUNCIONES CRÍTICAS QUE SIGUEN DENTRO DE SERVER.PY

Estas son las funciones de mayor importancia para el funcionamiento de AXIS que **no se han movido** a ningún módulo:

- **`evaluar_activo()`** (601 líneas) — el cerebro del sistema. Evalúa todas las estrategias (1VR, RPG, GNA, GBA, PM40, 4PASOS, CNF/RCB) para cada vela. Nunca se ha tocado en ningún sprint, por regla explícita de todos los sprints hasta ahora.
- **`telegram_webhook()`** (191 líneas) — maneja los callbacks de los botones de Telegram (ejecutar, derby, multi-contrato).
- **`cerrar_posicion()`** (119 líneas) — lógica de cierre de posición, cálculo de P&L, actualización de capital del Derby.
- **`registrar_posicion()`** (54 líneas) — lógica de apertura de posición.
- **`construir_v7_provisional()`** (78 líneas) — construcción de la vela V7 provisional con datos reales (v8.83), crítica para evitar alertas falsas.
- **`evaluar_hed()`** (61 líneas) — estrategia HED (shooting star diaria), ejecución automática.
- **`enviar_senal_con_botones()`** (58 líneas) — punto único de entrada hacia Telegram/Tradier para cualquier señal con confirmación manual.
- **`buscar_opcion_reto()`** (58 líneas) — búsqueda de opción alternativa dentro de presupuesto para el Derby.
- **`calcular_techo_canal()` / `calcular_piso_mitad_canal()`** — cálculo matemático del techo/piso/mitad de canales bajistas (slope P1→P2). Núcleo matemático de CNF/RCB/PM40.
- **`es_dia_mercado()` / `restar_dias_habiles()` / `calcular_festivos()` / `calcular_pascua()`** — Time Engine completo, usado por prácticamente todos los módulos vía inyección de parámetro.
- **`verificar_slope_4ps()`** — validación matemática de la estrategia 4PASOS.
- **`loop_v7_anticipada()` / `evaluar_v7_anticipada()` / `corregir_cierre_v7()`** — el flujo completo de evaluación de la última hora del día (3:58 PM / 4:01 PM), corregido en v8.83/v8.84 para eliminar alertas falsas.
- **`monitor_loop()` / `reporte_horario()`** — el loop principal del sistema.
- **Todas las rutas Flask** (`/activar`, `/portfolio`, `/derby/*`, `/diagnostico`, `/status`, etc.) — ~45 endpoints, ninguno movido en ningún sprint.

---

## 4. TOP 10 FUNCIONES MÁS GRANDES QUE SIGUEN EN SERVER.PY

| # | Función | Líneas |
|---|---|---|
| 1 | `evaluar_activo()` | 601 |
| 2 | `telegram_webhook()` | 191 |
| 3 | `cerrar_posicion()` | 119 |
| 4 | `home()` (landing page HTML) | 105 |
| 5 | `construir_v7_provisional()` | 78 |
| 6 | `system_status()` | 71 |
| 7 | `diagnostico()` | 71 |
| 8 | `tradier_raw()` | 70 |
| 9 | `analizar_portfolio_claude()` | 67 |
| 10 | `estado_diario_vacio()` | 63 |

**Lectura:** `evaluar_activo()` es, por sí sola, casi 5 veces más grande que la segunda función más grande del archivo. Es, sin comparación, el componente de mayor riesgo y mayor responsabilidad concentrada en todo el sistema.

---

## 5. DEPENDENCIAS ENTRE MÓDULOS

```
axis_config.py          ← sin dependencias internas (solo pytz)
axis_storage.py          ← axis_config.py
axis_tradier.py          ← axis_config.py
axis_telegram.py         ← sin dependencias internas (os, requests)
axis_orders.py           ← axis_config.py
axis_portfolio.py        ← axis_config.py
axis_channels.py         ← sin dependencias internas (recibe todo por parámetro)
axis_market.py           ← axis_config.py, axis_storage.py

server.py                ← TODOS los módulos anteriores (vía wrappers)
```

**Patrón establecido:** ningún módulo `axis_*.py` importa nada de `server.py` — todas las dependencias hacia atrás (hacia funciones que aún viven en server.py, como `es_dia_mercado`) se resuelven pasándolas como **parámetro**, nunca con import directo. Esto es intencional y evita imports circulares (lección aplicada explícitamente en AX-010).

**Riesgo de esta arquitectura:** server.py importa de 8 módulos distintos. Si alguno de ellos falla al importar (error de sintaxis, dependencia faltante), todo el sistema no arranca. Esto ya era así antes de la modularización (todo en un archivo), pero ahora el punto de falla está distribuido en 9 archivos en vez de 1.

---

## 6. RIESGOS ACTUALES

1. **`evaluar_activo()` sigue siendo un monolito de 601 líneas** — contiene 1VR, RPG, GNA, GBA, PM40, 4PASOS, CNF/RCB, y la lógica de reset diario, todo en una sola función. Ningún sprint hasta ahora la ha tocado por regla explícita — es, con mucho, el mayor riesgo arquitectónico del sistema.
2. **Duplicación controlada de credenciales:** `TRADIER_TOKEN`/`TRADIER_ACCOUNT`/`TRADIER_HEADERS` existen en server.py Y axis_tradier.py; `TRADIER_TOKEN_REAL`/`TRADIER_BASE_REAL`/`TRADIER_HEADERS_REAL` en server.py Y axis_market.py; `TELEGRAM_TOKEN`/`TELEGRAM_CHAT_ID` en server.py Y axis_telegram.py. Todas leen el mismo `os.environ`, por lo que el valor siempre es idéntico, pero es deuda técnica a resolver eventualmente.
3. **RESUELTO v8.96:** claves vestigiales TwelveData/Finnhub ya no permanecen como literales en el código; se leen únicamente desde entorno y no son parte del flujo activo.
4. **`guardar_ordenes`/`cargar_ordenes`, `guardar_portfolio`/`cargar_portfolio`, `guardar_canales`/`cargar_canales` usan ahora 3 patrones de wrapper ligeramente distintos** (parámetro simple en AX-007; tupla `(data, debe_guardar)` en AX-008; múltiples parámetros en AX-009) — funcional pero sin un único patrón unificado todavía.
5. **`archivar_señales_dia()` sigue sin mover** — depende de `estado_dia[]` (todos los activos) y `ACTIVOS`, pendiente desde AX-005.
6. **`enviar_telegram_botones()` sigue acoplada a Portfolio/Derby** en server.py — mezcla mensajería con decisión de negocio (qué botón mostrar según el estado del Derby).
7. **GLD sin canal bajista activo actualmente** (confirmado: el JSON real prevalece sobre `CANALES_DEFAULT`, sin relación con la modularización).
8. **Frontend (`axis_charts.html`) aún calcula canales PM40/4PASOS en JavaScript** — desincronizado potencialmente de cualquier cambio futuro en la lógica del backend.
9. **`evaluar_hed()` no usa la vela V7 provisional** (riesgo identificado en AX-002, Core Map — sigue sin resolverse).
10. **Ningún test automatizado existe en el repositorio** — toda la verificación de estos 10 sprints se ha hecho manualmente vía simulación de import real y curl a `/status`, sin una suite de pruebas que corra de forma repetible.

---

## 7. RECOMENDACIÓN DE PRÓXIMOS 5 SPRINTS

1. **AX-012 — Time Engine.** Mover `es_dia_mercado`, `restar_dias_habiles`, `calcular_festivos`, `calcular_pascua` a `axis_time.py`. Como ninguna de estas depende de nada que viva en módulos nuevos, este sprint NO debería necesitar el patrón de inyección de parámetro — puede ser una extracción limpia y directa. Beneficio inmediato: `axis_market.py` (y cualquier módulo futuro) podría importar `axis_time.py` directamente sin riesgo de circularidad.

2. **AX-013 — Channel Math.** Mover `calcular_techo_canal`, `calcular_piso_mitad_canal`, `ts_a_datetime`, `velas_mercado_entre` a `axis_channels.py` (o un nuevo `axis_channel_math.py`). Estas son funciones puras que dependen del dict `canal` — mismo patrón de parámetro ya usado en AX-009.

3. **AX-014 — Signals Persistence.** Mover `archivar_señales_dia()` a `axis_storage.py`, completando lo que quedó pendiente desde AX-005. Requiere el patrón de parámetro con `estado_dia` y `ACTIVOS`.

4. **AX-015 — Telegram Buttons.** Mover `enviar_telegram_botones()` a `axis_telegram.py`, usando el patrón de inyección de parámetro para la decisión del Derby (recibe el estado de `derby` en vez de leer `_portfolio` global). Esto completaría la separación de Telegram iniciada en AX-006.

5. **AX-016 — Strategy Decomposition (alto riesgo, requiere aprobación explícita y diseño extenso antes de codificar).** Comenzar a dividir `evaluar_activo()` en funciones más pequeñas por estrategia (`evaluar_1vr()`, `evaluar_rpg()`, `evaluar_gna_gba()`, `evaluar_canal_bajista()`, `evaluar_4pasos()`, `evaluar_pm40()`), todas llamadas desde `evaluar_activo()` en el mismo orden y con el mismo estado compartido. Este es el sprint de mayor riesgo y mayor valor de toda la lista — debe hacerse con extremo cuidado, probablemente en sub-sprints (uno por estrategia), nunca de una vez.

**Nota:** ningún test automatizado existe todavía. Antes o durante AX-016 específicamente, sería muy recomendable introducir al menos pruebas unitarias básicas sobre `evaluar_activo()` con datos de velas reales conocidos (por ejemplo, los casos de BA 06/24 y GOOG 06/25 ya documentados en las bitácoras), para detectar regresiones antes de que lleguen a producción.

---

*Documento generado en AX-011. No se modificó ningún código durante su creación.*
