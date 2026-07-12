# AXIS 2.0 — CORE MAP

**Versión documentada:** server.py v8.84
**Commit base:** 79f6e0a (con fixes adicionales del mismo día: 03-BACKLOG/HORAS_REPORTE)
**Generado:** AX-002

> Este documento describe el flujo REAL de ejecución tal como existe en el código, sin modificarlo. No es una propuesta de diseño — es un mapa de lo que ya hace el sistema.

---

## FLUJO PRINCIPAL — DESDE monitor_loop() HASTA TELEGRAM/TRADIER

```
1. monitor_loop()
   ↓
2. reporte_horario()
   ↓
3. get_velas()
   ↓
4. evaluar_activo()
   ↓
5. funciones internas llamadas por evaluar_activo()
   ↓
6. enviar_senal_con_botones()
   ↓
7. Telegram (enviar_telegram_botones)
   ↓
8. Tradier (get_opcion_tradier, luego ejecutar_orden_tradier_contratos vía webhook)
```

Existe un SEGUNDO camino paralelo, fuera de `monitor_loop`, exclusivo para la última hora del día (V7): `loop_v7_anticipada()`. Se documenta en la sección 9.

---

## 1. monitor_loop()

**Propósito:** thread principal que decide cuándo correr el reporte horario, alineándose al minuto `:01` de cada hora.

**Quién la llama:** se lanza como thread daemon desde `arrancar_monitor()` al iniciar el proceso.

**Qué recibe:** nada (sin parámetros).

**Qué devuelve:** nunca retorna — es un `while True` infinito.

**Qué estado modifica:** ninguno directamente. Solo controla el timing de llamada a `reporte_horario()`.

**Archivos JSON que usa:** ninguno directamente.

**Depende de:**
- `es_dia_mercado(ahora)` — para decidir si hoy se evalúa
- `HORAS_REPORTE` — lista `[10, 11, 12, 13, 14, 15]` (NO incluye 16 desde v8.84 — ver sección 9.3)
- `reporte_horario()` — la función que realmente dispara el trabajo

**Lógica de timing:** duerme hasta el minuto `:01` de la próxima hora, luego verifica si la hora actual está en `HORAS_REPORTE` antes de llamar a `reporte_horario()`.

---

## 2. reporte_horario()

**Propósito:** iterar sobre los activos configurados en `ACTIVOS` y evaluar cada uno con los datos más recientes de velas (10 activos desde AX-ASSET-001).

**Quién la llama:** `monitor_loop()` (automático) y la ruta `/reporte` (manual, vía Flask).

**Qué recibe:** nada.

**Qué devuelve:** nada (`None` implícito).

**Qué estado modifica:** indirectamente, todo lo que modifica `evaluar_activo()` (ver sección 4).

**Archivos JSON que usa:** ninguno directamente — delega a `get_velas()` y `evaluar_activo()`.

**Depende de:**
- `get_velas(simbolo, outputsize=50)` — para cada uno de los 8 `ACTIVOS`
- `evaluar_activo(simbolo, velas, ahora)` — la evaluación real
- Reintenta una vez (espera 2 minutos) si `get_velas()` devuelve `None`
- Si falla 2 veces, envía alerta de error vía `enviar_telegram()` y continúa con el siguiente activo

---

## 3. get_velas(simbolo, outputsize=280)

**Propósito:** construir las velas AXIS (V1-V7) agrupando barras de 15 minutos de Tradier, aplicando la regla de que una vela no existe hasta el `:01` después de su hora de cierre.

**Quién la llama:** `reporte_horario()`, `evaluar_v7_anticipada()` (indirectamente, vía la llamada interna), `corregir_cierre_v7()`, `evaluar_hed()`, y las rutas `/velas`, `/canal_lineas`.

**Qué recibe:** `simbolo` (string), `outputsize` (int, default 280 — límite de velas a devolver).

**Qué devuelve:** lista de dicts, cada uno con `datetime, open, high, low, close, vela, bars, bars_expected, completa` — o `None` si no hay datos.

**Qué estado modifica:** indirectamente, llama a `actualizar_velas_local()` que sí escribe en disco.

**Archivos JSON que usa:** lee/escribe `axis_velas_{simbolo}.json` (vía `cargar_velas_local`/`guardar_velas_local`, llamadas dentro de `actualizar_velas_local`).

**Depende de:**
- `actualizar_velas_local(simbolo)` — trae barras nuevas de Tradier si faltan
- `cargar_velas_local(simbolo)` — lee el archivo JSON local
- La regla de cierre: `vela_cierre_hora = {"V1":10,...,"V7":16}` — compara contra `datetime.now(EST)` y descarta velas aún no cerradas

**Nota importante (v8.69, sin cambios desde entonces):** esta regla aplica a la construcción NORMAL de velas. La vela V7 evaluada a las 3:58 PM usa un camino DIFERENTE (`construir_v7_provisional()`, sección 9.2) que no pasa por `get_velas()` para V7 — pasa por encima de esa restricción de forma controlada.

---

## 4. evaluar_activo(simbolo, velas, ahora)

**Propósito:** función central de evaluación. Determina qué vela corresponde a `ahora`, detecta si es un día nuevo (reset), y evalúa todas las estrategias activas para esa vela.

**Quién la llama:** `reporte_horario()` y `evaluar_v7_anticipada()` (con una lista de velas modificada, ver sección 9.2).

**Qué recibe:** `simbolo` (string), `velas` (lista de dicts de `get_velas()` o una lista modificada con vela V7 provisional), `ahora` (datetime EST).

**Qué devuelve:** nada (`None` implícito) — efectos secundarios únicamente.

**Qué estado modifica:**
- `estado_dia[simbolo]` — el diccionario completo de estado diario (flags `*_fired`, `*_activo`, P1/P2 de PM40 y 4PASOS, etc.)
- `canal[simbolo]` — P2 dinámico de canales bajistas (CNF/RCB/PM40)

**Archivos JSON que usa:** escribe `axis_estado_dia.json` (vía `guardar_estado_dia()`) y `axis_canales.json` (vía `guardar_canales()`) cada vez que algo cambia.

**Depende de (llamadas internas, ver sección 5):**
`reset_diario_activo`, `calcular_techo_canal`, `calcular_piso_mitad_canal`, `calcular_sma`, `verificar_slope_4ps`, `enviar_senal_con_botones`, `enviar_telegram`, `guardar_estado_dia`, `guardar_canales`.

---

## 5. Funciones llamadas por evaluar_activo() — detalle

### 5.1 reset_diario_activo(simbolo, fecha_hoy, v7_ayer_close)
- **Propósito:** reinicia `estado_dia[simbolo]` a un diccionario vacío cuando cambia la fecha.
- **Modifica:** `estado_dia[simbolo]` completo.
- **JSON:** ninguno directamente (lo guarda quien lo llama).

### 5.2 calcular_techo_canal(simbolo, ahora_dt)
- **Propósito:** calcula el valor proyectado del techo de un canal bajista (CNF/RCB/PM40) en un instante dado, usando la pendiente P1→P2.
- **Recibe:** símbolo, datetime.
- **Devuelve:** float (precio) o `None` si el canal no está activo o no tiene P1/P2.
- **Depende de:** `ts_a_datetime`, `velas_mercado_entre`.
- **No modifica estado** — es de solo lectura sobre `canal[simbolo]`.

### 5.3 calcular_piso_mitad_canal(simbolo, ahora_dt)
- **Propósito:** calcula piso y mitad de un canal RCB (requiere P3).
- **Devuelve:** tupla `(piso, mitad)` o `(None, None)`.
- **Depende de:** `calcular_techo_canal` (dos veces — en P3 y en el instante actual).

### 5.4 calcular_sma(velas, periodo)
- **Propósito:** media móvil simple sobre los `close` de las primeras `periodo` velas de la lista.
- **Nota:** asume que `velas[0]` es la más reciente (orden descendente) — coherente con cómo `get_velas()` ordena su resultado.

### 5.5 verificar_slope_4ps(p1_low, p1_idx, p2_low_cand, p2_idx_cand, historial_lows)
- **Propósito:** valida si un candidato a P2 de la estrategia 4PASOS es válido — sin tolerancia, cualquier low intermedio por debajo de la proyección invalida el candidato. También rechaza si P2 ≤ P1.
- **Pura función, sin efectos secundarios.**

### 5.6 enviar_senal_con_botones(simbolo, estrategia, hora_label, precio_vela, tipo_opcion, extra="")
- Ver sección 6 — es el puente hacia Telegram/Tradier.

### 5.7 guardar_estado_dia() / guardar_canales()
- Persisten `estado_dia` y `canal` completos a sus respectivos JSON.

---

## 6. enviar_senal_con_botones(simbolo, estrategia, hora_label, precio_vela, tipo_opcion, extra="")

**Propósito:** punto único de entrada para cualquier señal disparada — registra la señal, obtiene precio y opción de Tradier, y construye/envía el mensaje de Telegram con botones.

**Quién la llama:** `evaluar_activo()` (todas las estrategias: 1VR, RPG, GNA, GBA, PM40, 4PASOS, CNF, RCB) y `evaluar_hed()` indirectamente (HED llama a `registrar_senal_disparada` directo, no a esta función — ver nota en 9.4).

**Qué recibe:** símbolo, nombre/label de la estrategia, hora en texto (`"11:00 EST"`), precio de la vela, tipo de opción (`"PUT"`/`"CALL"`), texto extra opcional para el mensaje.

**Qué devuelve:** nada.

**Qué estado modifica:**
- Llama a `registrar_senal_disparada()` (modifica `estado_dia[simbolo]["señales_disparadas"]` y `señales_detalle`)
- Agrega entrada a `ordenes_pendientes` (dict en memoria)

**Archivos JSON que usa:** escribe `axis_ordenes.json` (vía `guardar_ordenes()`), y transitivamente `axis_estado_dia.json` (vía `registrar_senal_disparada` → `guardar_estado_dia`).

**Depende de:**
- `registrar_senal_disparada(simbolo, estrategia, hora_label)`
- `get_precio_tradier(simbolo)` — precio actual real
- `get_opcion_tradier(simbolo, tipo, precio)` — busca el contrato de opción
- `enviar_telegram_botones(msg, orden_id)`
- `guardar_ordenes()`

---

## 7. Telegram

### 7.1 enviar_telegram_botones(mensaje, orden_id)
- **Propósito:** envía el mensaje a Telegram con los botones `[x1][x2-10][DERBY]` (el botón DERBY solo aparece si hay un derby activo con caballo disponible).
- **Devuelve:** `(message_id, chat_id)` del mensaje enviado, o `(None, None)` si falla.
- **Depende de:** `_portfolio["derby"]` para decidir si mostrar el botón DERBY.

### 7.2 telegram_webhook() (ruta Flask `/telegram_webhook`)
- **Propósito:** recibe los `callback_query` cuando el usuario presiona un botón. Acciones: `exec_multi` (muestra submenú 2-10), `exec_c` (ejecuta N contratos), `exec` (ejecuta 1, ruta legacy), `reto` (asigna al derby), `skip`.
- **Modifica:** `ordenes_pendientes` (lo saca del dict), `_portfolio` (registra la posición vía `registrar_posicion`).

---

## 8. Tradier

### 8.1 get_opcion_tradier(simbolo, tipo, precio_actual)
- **Propósito:** busca el contrato de opción más cercano al strike objetivo (calculado con `get_pct_otm`), con vencimiento ≥7 días.
- **Devuelve:** dict con `symbol, strike, expiration, tipo, ask, bid, subyacente, pct_otm` o `None`.

### 8.2 ejecutar_orden_tradier_contratos(opcion, contratos)
- **Propósito:** envía la orden de compra (`buy_to_open`, market) y la orden GTC de venta (`sell_to_close`, limit al doble del ask) a Tradier sandbox.
- **Quién la llama:** el webhook, tras que el usuario presiona un botón de ejecución.
- **Devuelve:** dict con `ok, id, status, venta_id, precio_venta`.

---

## 9. CAMINO PARALELO — loop_v7_anticipada() (V7, último de cada día)

Este flujo es independiente de `monitor_loop()` y corre en su propio thread.

### 9.1 loop_v7_anticipada()
- A las **3:58 PM EST** (todos los activos por igual desde v8.83 — sin excepción para SPY): llama a `evaluar_v7_anticipada(simbolo)` y `evaluar_hed(simbolo)`.
- A las **4:01 PM EST**: llama a `corregir_cierre_v7(simbolo)` para cada activo, y UNA SOLA VEZ ejecuta el bloque "resumen" (`agregar_barra_diaria`, `guardar_snapshot_precios`, `archivar_señales_dia`, `enviar_resumen_diario`).
- **v8.84:** ya NO evalúa estrategias a las 4:01 PM — esa evaluación fue eliminada para evitar duplicados (ver Riesgos).

### 9.2 evaluar_v7_anticipada(simbolo)
- Llama a `construir_v7_provisional(simbolo, ahora)` para obtener una V7 con datos reales pero incompletos (3 barras de 15min + barras de 1min hasta el momento).
- Reemplaza cualquier V7 de hoy en la lista de velas de `get_velas()` con esta provisional, e invoca `evaluar_activo()` con esa lista modificada.
- **La vela provisional nunca se persiste** — vive solo en la variable local `velas_con_provisional`.

### 9.3 construir_v7_provisional(simbolo, ahora)
- Pide a Tradier directamente (sin pasar por `get_velas()`/la base local): 3 barras de 15min (15:00-15:45) + barras de 1min (15:45 hasta `ahora`).
- Construye un dict de vela con `open` de la primera barra, `high`/`low` máximo/mínimo de todas, `close` de la última, y `completa: False`.

### 9.4 evaluar_hed(simbolo)
- Evalúa la estrategia HED (shooting star diaria) usando la última vela de `get_velas(simbolo, outputsize=2)` — **nota:** esta función NO usa la vela provisional, usa `get_velas()` normal, por lo que a las 3:58 PM podría estar leyendo la V7 de AYER si la de HOY aún no está disponible según la regla del `:01`. Esto no se modificó en este sprint — queda registrado como observación, no como bug confirmado.
- Si dispara, llama a `ejecutar_orden_tradier(opcion)` directamente (no pasa por `enviar_senal_con_botones`, por lo tanto no genera botones — HED es automática).

### 9.5 corregir_cierre_v7(simbolo)
- A las 4:01 PM, lee la V7 ya cerrada y real (vía `get_velas()` normal, que ya la deja pasar el filtro del `:01`) y actualiza `estado_dia[simbolo]["v7_ayer_close"]` — el valor que usará el reset del día siguiente.

---

## DEPENDENCIAS CRÍTICAS

1. **`estado_dia` y `canal` son diccionarios globales en memoria**, persistidos a JSON después de cada cambio. Si el proceso se reinicia (deploy, crash), se recuperan desde `axis_estado_dia.json` y `axis_canales.json` SOLO si la fecha guardada coincide con hoy (`cargar_estado_dia`); de lo contrario, dependen de la reconstrucción desde velas históricas dentro de `evaluar_activo()`.
2. **`get_velas()` es el único punto de verdad para la construcción de velas normales** — toda evaluación que no sea V7-provisional pasa por aquí, y aquí vive la regla del `:01` después del cierre.
3. **`enviar_senal_con_botones()` es el único punto de entrada hacia Telegram/Tradier para señales con confirmación manual** — cualquier estrategia nueva que se agregue debe pasar por aquí para mantener consistencia (excepción actual: HED, que ejecuta automático).
4. **`ordenes_pendientes` es un diccionario en memoria**, persistido a `axis_ordenes.json` pero reconstruido al arrancar solo si no han expirado (`ORDEN_TIMEOUT_MIN = 15` minutos).
5. **El Derby (`_portfolio["derby"]`) y el Portfolio normal comparten la misma lista de posiciones** (`_portfolio["posiciones"]`), diferenciadas por el flag `es_reto` y `carril_id`.

---

## RIESGOS

1. **`evaluar_hed()` no usa la vela V7 provisional** — a las 3:58 PM podría estar evaluando con datos de un día anterior si la V7 de hoy aún no pasa el filtro de `get_velas()`. No confirmado como bug activo, pero es una asimetría real con `evaluar_v7_anticipada()`.
2. **Si `loop_v7_anticipada()` falla un día** (error de red, excepción no capturada antes del `except` general) **no hay ningún respaldo evaluando V7** — desde v8.84, `monitor_loop` ya no la evalúa a las 4:01 PM. El único respaldo es el `except Exception` genérico al final del `while True` del propio loop, que solo evita que el thread muera, pero no reintenta esa evaluación específica perdida.
3. **`HORAS_REPORTE` y `ACTIVOS_V7_ANTICIPADA` son dos mecanismos de scheduling distintos y paralelos** — cualquier cambio futuro en uno sin considerar el otro puede reintroducir el bug de doble evaluación que ya se corrigió en v8.84.
4. **El frontend (`axis_charts.html`) aún calcula los canales PM40/4PASOS de forma independiente en JavaScript** — no documentado en este sprint porque pertenece al frontend, pero es una dependencia cruzada real: si la lógica de PM40/4PASOS cambia en `server.py`, el frontend no se actualiza automáticamente.
5. **Las funciones de canal (`calcular_techo_canal`, `calcular_piso_mitad_canal`) dependen de `canal[simbolo]["p2_actual_ts"]`**, que se guarda/carga como string ISO y se re-localiza a EST al cargar — un error de formato en el JSON (manual o por un bug futuro) rompería silenciosamente el cálculo del techo (devuelve `None`, no excepción visible).

---

## FUNCIONES MÁS IMPORTANTES

| Función | Por qué es crítica |
|---|---|
| `evaluar_activo()` | Es el cerebro de todo el sistema — toda estrategia vive aquí |
| `get_velas()` | Única fuente de verdad de las velas AXIS; contiene la regla del `:01` |
| `enviar_senal_con_botones()` | Único puente hacia Telegram/Tradier para señales confirmables |
| `construir_v7_provisional()` | Resuelve el problema de evaluar V7 antes de su cierre real, sin usar datos falsos |
| `calcular_techo_canal()` | Base matemática de todos los canales bajistas (CNF/RCB/PM40) y por extensión de 4PASOS |
| `registrar_senal_disparada()` | Único punto donde se guarda la vela/hora real de cada señal — clave para que el frontend dibuje correctamente |
| `loop_v7_anticipada()` | Controla el único punto de evaluación de la última hora del día, crítico para no duplicar alertas |

---

*Documento generado en AX-002. No se modificó ningún código durante su creación.*
