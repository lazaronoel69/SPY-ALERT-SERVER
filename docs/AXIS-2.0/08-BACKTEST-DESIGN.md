# AXIS 2.0 — Backtest Engine Design

**Fecha:** 2026-06-30
**Sprint:** BT-001
**Estado:** DISEÑO COMPLETADO. Implementación en `backtest.py` — BT-001 → BT-011 COMPLETE.

> Backtest v1 STATUS: COMPLETE. Ver `10-HANDOFF.md` para resultados y métricas.

---

## Principio fundamental

Un solo motor. `evaluar_activo()` es la única fuente de verdad.
El backtest no tiene lógica propia. No existe `evaluar_activo_backtest()`.

---

## 1. ¿Cómo reutilizar `evaluar_activo()` sin duplicar lógica?

`evaluar_activo(simbolo, velas, ahora)` ya recibe sus dos variables por parámetro:

- `velas` — lista de velas AXIS (V1..V7). Puede ser histórica.
- `ahora` — `datetime`. Puede ser sintético.

La función no sabe si está en producción o en backtest. No hay nada que cambiar en ella.

El backtest solo necesita:
1. Construir `velas` a partir del historial guardado.
2. Construir `ahora` con el timestamp de la vela que se está evaluando.
3. Llamar `evaluar_activo()` exactamente igual que el monitor de producción.

**Cero duplicación de lógica.**

---

## 2. ¿Qué dependencias deben desacoplarse?

### Telegram
`enviar_senal_con_botones()` — dispara mensaje a Telegram y llama a Tradier para obtener precio
en vivo y seleccionar opción. En backtest: no se quiere enviar nada, solo registrar que la señal
se habría disparado.

### Tradier
`get_precio_tradier()` y `get_opcion_tradier()` — llamadas HTTP durante `enviar_senal_con_botones`.
En backtest: el precio del subyacente está en la vela histórica. No se necesita Tradier.

### Persistencia
`guardar_estado_dia()`, `guardar_canales()`, `guardar_ordenes()`, `guardar_portfolio()` — escriben
JSON a disco en cada mutación. En backtest: el estado es efímero (en memoria), no debe persistirse.

### Hora actual
`ahora` ya es parámetro de `evaluar_activo()` — no hay problema. Si alguna función interna llama
`datetime.now()` directamente, esa llamada debe ser reemplazada durante el backtest.

### Logs
`print()` dispersos en las estrategias. En backtest: opcionales. Se pueden dejar; no rompen nada.

---

## 3. ¿Cuál es la forma MÁS SIMPLE de desacoplarlas?

**Monkey-patch en el módulo `server` justo antes de correr el backtest.**

```
import server

server.enviar_senal_con_botones = <interceptor>
server.guardar_estado_dia       = <no-op>
server.guardar_canales          = <no-op>
server.guardar_ordenes          = <no-op>
server.guardar_portfolio        = <no-op>
```

El interceptor de `enviar_senal_con_botones` recibe los mismos argumentos que la versión real pero,
en lugar de llamar a Telegram y Tradier, agrega la señal a una lista en memoria.

**Sin capas. Sin interfaces. Sin clases. Sin inyección de dependencias.**
Son 5 asignaciones de función. Eso es todo.

El precio del subyacente en el momento de la señal se obtiene de la vela histórica actual
(el `close` de la vela que disparó la señal), sin llamar a Tradier.

---

## 4. ¿Qué entrada necesita?

### Velas históricas
`axis_velas_<SYMBOL>.json` — ya existe en el volumen de Railway. Contiene barras de 15 minutos
por símbolo desde que se empezaron a guardar. `cargar_velas_local(simbolo)` ya sabe leerlos.
`get_velas()` ya sabe bucketearlos en V1..V7 por día.

Para correr el backtest localmente: copiar los archivos del volumen Railway a `/data` local.
No requiere ningún cambio en las funciones de lectura.

### Configuración
- Lista de símbolos (los mismos de producción).
- `fecha_inicio`, `fecha_fin` — rango de días a simular.

### Capital inicial
- Monto de partida para construir la equity curve.

---

## 5. ¿Qué salida produce?

> **Alcance de v1:** Esta primera versión NO calcula P&L real de opciones.
> Mide el movimiento del subyacente como proxy direccional.
> Los resultados no deben interpretarse como ganancias o pérdidas reales de contratos.
> El P&L real de opciones requiere una fase posterior (v2) con historial de bid/ask
> o reconstrucción aproximada de precios de opciones.

### Por señal (v1 — métricas direccionales)
Cada vez que el interceptor captura una señal:
- Fecha y hora (vela que la disparó)
- Símbolo
- Estrategia (1VR, RPG, GNA, GBA, RCB/CNF, PM40, 4PASOS)
- Tipo (call / put)
- Precio del subyacente en la vela de entrada

El resultado se mide comparando el precio del subyacente en las barras posteriores:
- **Acierto** — ¿el subyacente se movió en la dirección esperada antes de moverse en contra?
- **Movimiento favorable máximo** — % de movimiento máximo a favor desde la señal hasta N velas después
- **Movimiento adverso máximo** — % de movimiento máximo en contra (proxy de drawdown por señal)

No se usan precios de opciones. No se calcula P&L en dólares de contratos.

### Métricas agregadas (v1 — proxy direccional)
- **Tasa de acierto** — señales con movimiento favorable / total señales
- **Movimiento favorable promedio** — % promedio de movimiento a favor cuando acierta
- **Movimiento adverso promedio** — % promedio de movimiento en contra cuando falla
- **Profit factor proxy** — (tasa_acierto × mov_favorable_avg) / (tasa_fallo × mov_adverso_avg)
- **Expectancy proxy** — (tasa_acierto × mov_favorable_avg) − (tasa_fallo × mov_adverso_avg)
- **Drawdown proxy** — caída acumulada máxima asumiendo capital fijo por señal
- **Estadísticas por estrategia** — tasa de acierto, movimiento promedio, cantidad de señales
- **Estadísticas por activo** — mismas métricas agrupadas por símbolo

### Fase posterior (v2 — P&L real de opciones)
Para calcular P&L real se necesita uno de los siguientes:
- Historial de bid/ask de opciones en las fechas simuladas (no disponible actualmente en Railway)
- Reconstrucción aproximada usando Black-Scholes con volatilidad implícita histórica
- Datos de opciones históricos de un proveedor externo (e.g. CBOE, OptionsDX)

Esta fase no es parte de BT-001.

---

## 6. ¿Cómo garantizar resultados idénticos en Producción, Backtest y Paper Trading?

**La garantía es estructural, no contractual.**

Existe un solo `evaluar_activo()`. El backtest no tiene una copia. Si la función cambia en
producción, el backtest cambia automáticamente porque importa el mismo módulo.

Lo único que varía entre los tres modos es el **handler de señal**:

| Modo | Handler de señal |
|---|---|
| Producción | `enviar_senal_con_botones()` real → Telegram + Tradier sandbox |
| Paper Trading | Igual que producción (ya es paper) |
| Backtest | Interceptor → registra en lista, no llama a nada externo |

La lógica de cuándo y cómo se dispara una señal es idéntica en los tres casos.

---

## 7. ¿Qué piezas del Core NO deben modificarse?

Las siguientes funciones deben quedar intactas. Ningún cambio, ningún parámetro nuevo,
ninguna bandera de modo:

- `evaluar_activo()` — el orquestador
- `evaluar_1vr_normal()`
- `evaluar_rpg_activacion()` / `evaluar_rpg_disparo()`
- `evaluar_gna()`
- `evaluar_gba()`
- `evaluar_canal_v1()` / `evaluar_canal_v2_v7()`
- `evaluar_pm40_v1()` / `evaluar_pm40_v2_v7()`
- `evaluar_4pasos_v1()` / `evaluar_4pasos_v2_v7()`
- `preparar_contexto_vela()`
- `reset_diario_si_aplica()`
- `calcular_techo_canal()` / `calcular_piso_mitad_canal()`
- `velas_mercado_entre()`
- `verificar_slope_4ps()`
- `get_velas()` / `cargar_velas_local()`

**Ninguna de estas funciones debe saber que existe un backtest.**

---

## 8. ¿Qué cambios mínimos son necesarios? (ordenados por prioridad)

### Prioridad 1 — No tocar nada en server.py
Cero cambios. El motor ya está listo.

### Prioridad 2 — Crear `backtest.py` en la raíz del repo
Un solo archivo. No es un módulo. No es un framework. Hace exactamente esto:
1. Aplica los 5 monkey-patches.
2. Carga velas históricas por símbolo y fecha.
3. Por cada día, por cada vela V1..V7, llama `evaluar_activo()` con timestamp sintético.
4. Recolecta las señales interceptadas.
5. Calcula resultados comparando con barras posteriores.
6. Imprime métricas a stdout (JSON).

Estimado: ~150 líneas.

### Prioridad 3 — Copiar datos de Railway a local
`scp` o `railway volume download` de los archivos `axis_velas_<SYMBOL>.json` al directorio
`/data` local. Sin esto no hay historial que reproducir. No requiere cambio de código.

### Prioridad 4 — (Opcional) Variable global `BT_MODE`
Si los `print()` de las estrategias generan ruido, agregar `BT_MODE = False` en `axis_config.py`
y condicionarlo en los prints. No es necesario para que el backtest funcione — es calidad de vida.

---

## Resumen

El Backtest Engine es un arnés de 150 líneas alrededor del motor existente.
No duplica lógica. No modifica producción. No requiere refactor.
La única infraestructura nueva son 5 monkey-patches y un loop de replay de fechas.
