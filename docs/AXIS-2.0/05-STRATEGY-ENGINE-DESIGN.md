# AXIS 2.0 — STRATEGY ENGINE DESIGN

**Sprint:** AX-012A | **Fecha:** 06/26/2026 | **Base:** server.py v8.84, líneas 761-1361 (`evaluar_activo`)

> Documento puramente de diseño. NO se modificó código durante su creación. `evaluar_activo()` no fue tocada.

---

## 1. ESTRUCTURA ACTUAL DE evaluar_activo()

### 1.1 Orden exacto de ejecución (tal como existe hoy)

```
1.  Localizar vela_actual correspondiente a la hora actual
    └─ si no existe → return (sale de la funcion completa)

2.  Extraer v_open, v_close, v_high, v_low, fecha_hoy de vela_actual

3.  BLOQUE RESET DIARIO (si ed["fecha"] != fecha_hoy):
    a. Buscar v7_ayer (close de V7 del dia anterior)
    b. reset_diario_activo() — vacia estado_dia[simbolo]
    c. Guardar P2 actual en p2_inicio_dia (si canal activo)
    d. RECONSTRUCCION: buscar V1 de hoy en el historial y:
       - re-evaluar 1VR (con condicion adicional RCB/SMA)
       - re-activar RPG si aplica (gap >= 0.2%)
       - re-activar GNA si aplica
       - re-activar GBA si aplica

4.  Calcular v_alcista (vela alcista estricta AXIS) y v_roja
    (estos dos flags se calculan UNA SOLA VEZ para toda la funcion,
    se usan en multiples bloques mas abajo)

5.  hora_vela = hora - 1

6.  BIFURCACION PRINCIPAL: if hora_vela == 9 (es V1) vs else (V2-V7)

   ── RAMA V1 (hora_vela == 9) ──
   6a. Guardar v1_close/v1_open/v1_low en ed
   6b. Evaluar 1VR (dispara si v_roja, marca vr1_fired)
   6c. Evaluar RPG (activa rpg_activo + rpg_piso si gap >= 0.5%)
   6d. Evaluar GNA (activa gna_activo si gap >= 0.1% + SMA20>SMA40)
   6e. Evaluar GBA (activa gba_activo si gap >= 0.1%)
   6f. Canal V1 — P2 dinamico especial (cualquier tipo de vela)
   6g. PM40 — inicializa o actualiza P1 dinamico en V1
   6h. 4PASOS — inicializa P1 en V1 (si zona valida del RCB)
   6i. return (SALE DE LA FUNCION — nada de lo de abajo corre en V1)

   ── RAMA V2-V7 (else) ──
   6j. Leer v1_close = ed["v1_close"] (guardado en V1)
   6k. Evaluar RPG (dispara si rpg_activo y v_close < rpg_piso)
   6l. Evaluar GNA (dispara si gna_activo y v_alcista y v_close > v1_close)
   6m. Evaluar GBA (dispara si gba_activo y v_alcista y v_close > v1_close)
   6n. Canal RCB/CNF — P2 dinamico (Caso A) + ruptura (Caso B) + apagado (Caso C)
   6o. PM40 — V2-V7: maduracion P1, fijacion P2, ruptura o actualizacion
   6p. 4PASOS — V2-V7: reset/P1 movil/busqueda P2/ruptura o actualizacion

7.  print() final de resumen (siempre corre, excepto si V1 hizo return antes)
```

### 1.2 Variables compartidas entre bloques

| Variable | Calculada en | Usada en |
|---|---|---|
| `ed` (estado_dia[simbolo]) | Inicio de función | TODOS los bloques |
| `c` (canal[simbolo]) | Inicio de función | Canal V1, RCB/CNF, PM40, 4PASOS |
| `vela_actual`, `v_open/close/high/low` | Inicio | TODOS los bloques |
| `v_alcista` | Después del reset diario | GNA, GBA, RCB/CNF (Caso B), 4PASOS (Caso A) |
| `v_roja` | Después del reset diario | 1VR, 4PASOS (Caso B) |
| `v1_close` | Solo en rama V2-V7, leído de `ed["v1_close"]` | GNA, GBA (rama V2-V7) |
| `hora_vela` | Después del reset diario | Determina la bifurcación V1 vs V2-V7; usado en labels de hora |
| `ahora_dt_*` (variantes por bloque) | Repetido en cada bloque que lo necesita | 1VR, RPG, RCB/CNF, 4PASOS — cada uno construye su propia variable local con el mismo valor |

**Observación crítica:** `ahora_dt` se reconstruye de forma idéntica (mismo cálculo, mismo valor) en al menos 5 lugares distintos dentro de la función (`ahora_dt_r`, `ahora_dt_vr`, `ahora_dt_v1c`, `ahora_dt_4ps_v1`, `ahora_dt_rpg`, `ahora_dt_c`, `ahora_dt_4ps`). Esto es ineficiente pero funcionalmente correcto — cualquier división en subfunciones debe decidir si preserva esta redundancia o la consolida (ver sección 5).

### 1.3 Flags de estado que modifica cada bloque

| Bloque | Flags que modifica |
|---|---|
| Reset diario | `ed["fecha"]`, todo `estado_dia[simbolo]` (vía `reset_diario_activo`), `ed["p2_inicio_dia"]`, `ed["vr1_fired"]`, `ed["rpg_activo"]`, `ed["rpg_piso"]`, `ed["gna_activo"]`, `ed["gba_activo"]` (solo si reconstrucción) |
| 1VR (V1) | `ed["vr1_fired"]` |
| RPG (V1, activación) | `ed["rpg_activo"]`, `ed["rpg_piso"]`, `ed["rpg_s20"]`, `ed["rpg_s40"]` |
| GNA (V1, activación) | `ed["gna_activo"]` |
| GBA (V1, activación) | `ed["gba_activo"]` |
| Canal V1 (P2 dinámico especial) | `c["p2_actual_high"]`, `c["p2"]["high"/"fecha"/"hora_est"]`, `c["p2_actual_ts"]` |
| PM40 (V1) | `ed["pm40_*"]` (8 campos), `canal[simbolo]["p2"]`/`p2_actual_high`/`on"]` (si invalida) |
| 4PASOS (V1) | `ed["4ps_*"]` (incluye `4ps_historial_lows`) |
| RPG (V2-V7, disparo) | `ed["rpg_fired"]`, `ed["rpg_activo"]` |
| GNA (V2-V7, disparo) | `ed["gna_fired"]`, `ed["gna_activo"]` |
| GBA (V2-V7, disparo) | `ed["gba_fired"]`, `ed["gba_activo"]` |
| RCB/CNF (V2-V7) | `c["p2_actual_high"]`, `c["p2"]`, `c["p2_actual_ts"]`, `c["roto"]`, `c["fecha_ruptura"]`, `c["apagado"]`, `ed["rcb_fired"/"cnf_fired"]` |
| PM40 (V2-V7) | `ed["pm40_*"]` (todos los campos), `canal[simbolo]["p2"]`/`p2_actual_high`/`on"]`, `ed["pm40_fired"]` |
| 4PASOS (V2-V7) | `ed["4ps_*"]` (todos los campos), `ed["4ps_fired"]`, `ed["4ps_ultima_senal"]` |

**Persistencia (guardar_estado_dia / guardar_canales):** se llama de forma dispersa e inconsistente — algunos bloques guardan inmediatamente después de cada cambio (1VR, RPG disparo, GNA disparo, GBA disparo, RCB/CNF ruptura), otros NO guardan explícitamente dentro del bloque (PM40 V1, 4PASOS V1, Canal V1 P2 dinámico — estos llaman a `guardar_canales()` pero no siempre a `guardar_estado_dia()`). Esto es una inconsistencia preexistente, no introducida por ningún sprint de modularización.

---

## 2. SEPARACIÓN PROPUESTA EN SUBFUNCIONES

### 2.1 `preparar_contexto_vela(simbolo, velas, ahora)`

**Inputs:** `simbolo`, `velas` (lista completa), `ahora` (datetime)
**Outputs:** dict o tupla con `vela_actual, v_open, v_close, v_high, v_low, fecha_hoy, hora_vela, v_alcista, v_roja` — o `None` si no se encontró vela.
**Estado que modifica:** ninguno — función de solo lectura/cálculo.
**Riesgo:** bajo. Es exactamente el bloque 1-2 y el cálculo de `v_alcista`/`v_roja` (bloque 4) de la función actual, sin ninguna dependencia de `ed` ni `c`.
**¿Puede extraerse ahora?** **Sí.** Es la subfunción de menor riesgo de toda la lista — pura, sin estado, con un solo punto de entrada y salida.

### 2.2 `reset_diario_si_aplica(simbolo, ed, c, velas, fecha_hoy, v7_ayer_actual)`

**Inputs:** `simbolo`, `ed` (estado_dia[simbolo] actual), `c` (canal[simbolo]), `velas`, `fecha_hoy`.
**Outputs:** `ed` actualizado (nuevo o el mismo), flag `hubo_reset: bool`.
**Estado que modifica:** TODO `estado_dia[simbolo]` (reset completo), `ed["p2_inicio_dia"]`, y potencialmente dispara 1VR/RPG/GNA/GBA si la reconstrucción detecta que V1 ya existe en el histórico (esto es lo más delicado: el reset SÍ puede enviar alertas a Telegram, no es solo "limpieza de estado").
**Riesgo:** **alto**. Esta función no es solo un reset — contiene una reconstrucción completa que re-evalúa 1VR con su lógica completa (condición RCB/SMA) y puede llamar a `enviar_senal_con_botones()`. Separarla requiere que la subfunción de 1VR sea reutilizable tanto desde aquí como desde el flujo normal de V1 — alto acoplamiento.
**¿Puede extraerse ahora?** **No todavía.** Requiere primero extraer `evaluar_1vr()` como función reutilizable (ver 2.3), y que `reset_diario_si_aplica()` la llame internamente en el camino de reconstrucción.

### 2.3 `evaluar_1vr(simbolo, ed, c, velas, vela_actual, v_open, v_close, v_roja, hora_vela)`

**Inputs:** estado y datos de la vela actual.
**Outputs:** ninguno explícito (efecto secundario: posible llamada a Telegram).
**Estado que modifica:** `ed["vr1_fired"]`.
**Riesgo:** medio. La lógica es idéntica entre el camino normal (V1, bloque 6b) y el camino de reconstrucción (bloque 3d) — son prácticamente copy-paste con nombres de variable distintos (`v1_close_r` vs `v_close`, etc.). Unificarlos en una sola función reduce duplicación pero requiere verificar con extremo cuidado que ambos caminos pasen exactamente los mismos parámetros con los mismos valores.
**¿Puede extraerse ahora?** **Sí, con cuidado.** Es la estrategia más simple (solo V1, un único disparo por día) y ya está duplicada en el código actual — unificarla es una mejora real, no solo una extracción mecánica. Requiere prueba exhaustiva comparando ambos caminos antes/después.

### 2.4 `evaluar_rpg(simbolo, ed, c, vela_actual, v_open, v_close, v_low, v_alcista, hora_vela, v7_ayer, es_v1)`

**Inputs:** todo lo necesario para tanto activación (V1) como disparo (V2-V7) — un solo parámetro `es_v1: bool` decide la rama.
**Outputs:** ninguno explícito.
**Estado que modifica:** `ed["rpg_activo"]`, `ed["rpg_piso"]`, `ed["rpg_s20"]`, `ed["rpg_s40"]` (activación); `ed["rpg_fired"]`, `ed["rpg_activo"]` (disparo).
**Riesgo:** medio. RPG tiene dos comportamientos genuinamente distintos (activar en V1, disparar en V2-V7) que hoy viven en bloques separados de la función. Combinarlos en una función con un flag `es_v1` es una opción; mantenerlos como dos funciones (`evaluar_rpg_activacion` y `evaluar_rpg_disparo`) es otra, probablemente más segura por ser más explícita.
**¿Puede extraerse ahora?** **Sí**, preferiblemente como dos funciones separadas en vez de una con flag, para minimizar el riesgo de mezclar lógica de ramas distintas.

### 2.5 `evaluar_gna_gba(simbolo, ed, vela_actual, v_open, v_close, v_alcista, hora_vela, v7_ayer, v1_close, es_v1)`

**Inputs:** similar a RPG — GNA y GBA comparten estructura casi idéntica (gap alcista vs gap bajista, mismo patrón de activación/disparo).
**Outputs:** ninguno explícito.
**Estado que modifica:** `ed["gna_activo"]`/`ed["gna_fired"]`, `ed["gba_activo"]`/`ed["gba_fired"]`.
**Riesgo:** medio-bajo. Estas dos estrategias son las más simples y simétricas del sistema — buena candidata para extracción temprana, aunque conviene mantener GNA y GBA como llamadas separadas (`evaluar_gna()`, `evaluar_gba()`) en vez de una función combinada, para que cada una sea trivial de verificar independientemente.
**¿Puede extraerse ahora?** **Sí.**

### 2.6 `evaluar_pm40(simbolo, ed, c, vela_actual, v_high, v_alcista, hora_vela, velas)`

**Inputs:** todo el contexto de PM40 — requiere `calcular_sma()` para V1 (4 SMAs: 20/40/100/200).
**Outputs:** ninguno explícito.
**Estado que modifica:** los 8 campos `ed["pm40_*"]`, y potencialmente `canal[simbolo]["p2"]`/`p2_actual_high`/`on"]` (cuando PM40 actualiza o invalida el canal automático).
**Riesgo:** **alto**. PM40 es la estrategia con más estado interno (8 flags) y con la lógica más compleja de maduración progresiva (3+ velas bajo P1 → maduro → buscar P2 → comparar contra techo proyectado). Además escribe directamente sobre el dict `canal[simbolo]`, creando una dependencia cruzada con el módulo de canales (ya separado en AX-009 solo para persistencia, no para esta lógica).
**¿Puede extraerse ahora?** **No todavía recomendado sin sub-división.** PM40-V1 (inicialización) y PM40-V2-V7 (maduración/ruptura) son lo bastante distintos como para tratarse como dos sub-sprints separados (ver sección 6).

### 2.7 `evaluar_4pasos(simbolo, ed, c, vela_actual, v_low, v_close, v_roja, ahora, hora_vela)`

**Inputs:** todo el contexto de 4PASOS — requiere `calcular_techo_canal`, `calcular_piso_mitad_canal`, `verificar_slope_4ps`.
**Outputs:** ninguno explícito.
**Estado que modifica:** todos los campos `ed["4ps_*"]`, incluyendo el historial de lows (lista que crece).
**Riesgo:** **alto**. Misma razón que PM40 — mucho estado interno, lógica de proyección matemática (slope), y una regla temporal (24h de espera post-señal) que depende de `ahora` real, no solo del histórico de velas. Es la estrategia que más recientemente cambió (v8.78, rediseño completo) — mayor riesgo de introducir una regresión sutil si se extrae sin pruebas exhaustivas.
**¿Puede extraerse ahora?** **No todavía recomendado sin sub-división**, mismo razonamiento que PM40 (ver sección 6).

### 2.8 `evaluar_canales_bajistas(simbolo, ed, c, vela_actual, v_high, v_close, v_alcista, hora_vela)`

**Inputs:** contexto de canal CNF/RCB — Casos A/B/C de ruptura, más el caso especial de V1 (que ya está separado arriba en 6f).
**Outputs:** ninguno explícito.
**Estado que modifica:** `c["p2_actual_high"]`, `c["p2"]`, `c["p2_actual_ts"]`, `c["roto"]`, `c["fecha_ruptura"]`, `c["apagado"]`, `ed["rcb_fired"/"cnf_fired"]`.
**Riesgo:** medio-alto. Tres casos (A/B/C) mutuamente excluyentes (`if/elif/elif`) sobre el mismo `techo` calculado una vez — la función debe preservar exactamente ese orden de evaluación. El caso de V1 (bloque 6f) usa una variante simplificada (solo P2 dinámico, sin los casos B/C de ruptura) — son funciones hermanas, no la misma función reusada.
**¿Puede extraerse ahora?** **Sí, pero como dos funciones**: `evaluar_canal_v1()` (la variante simple ya identificada en 6f) y `evaluar_canal_v2_v7()` (los 3 casos completos) — nunca combinarlas en una sola con un flag, dado que sus comportamientos difieren genuinamente, no solo en superficie.

### 2.9 `persistir_estado_si_cambia(simbolo, hubo_cambio_estado_dia, hubo_cambio_canal)`

**Inputs:** flags booleanos indicando si algo cambió.
**Outputs:** ninguno.
**Estado que modifica:** escribe a disco (`guardar_estado_dia()`, `guardar_canales()`).
**Riesgo:** medio. El código actual NO usa este patrón — cada bloque decide individualmente cuándo guardar, de forma inconsistente (ver observación en 1.3). Introducir esta función **cambiaría el comportamiento actual** (algunos guardados que hoy ocurren inline dejarían de ocurrir inline) — esto técnicamente sería una mejora, pero excede el alcance de "sin cambiar comportamiento" que rige todos los sprints de modularización hasta ahora.
**¿Puede extraerse ahora?** **No en esta forma.** Si se decide perseguir esto, debe ser un sprint separado y explícito de "consolidación de persistencia", con aprobación específica de que se acepta el cambio de comportamiento (aunque sea de bajo riesgo — escribir el archivo una vez al final en vez de N veces durante la función).

---

## 3. ORDEN OBLIGATORIO

El orden de evaluación dentro de `evaluar_activo()` debe permanecer **idéntico** al actual en cualquier descomposición futura:

```
reset_diario (si aplica)
  → [si V1]:
      1VR → RPG-activación → GNA-activación → GBA-activación
      → Canal-V1-P2-dinámico → PM40-V1 → 4PASOS-V1
      → return (nada más corre)
  → [si V2-V7]:
      RPG-disparo → GNA-disparo → GBA-disparo
      → Canales-bajistas-V2-V7 → PM40-V2-V7 → 4PASOS-V2-V7
```

Ninguna subfunción debe reordenarse respecto a sus vecinas, incluso si en apariencia son independientes — el orden actual nunca ha sido cuestionado ni hay evidencia de que el orden importe matemáticamente, pero cambiar el orden sin evidencia explícita de que es seguro violaría la regla de "no cambiar comportamiento" de todos los sprints anteriores.

---

## 4. RIESGOS

1. **Variables compartidas:** `ed`, `c`, `v_alcista`, `v_roja`, `hora_vela` se usan en casi todos los bloques. Cualquier subfunción debe recibir explícitamente todo lo que necesita — no puede asumir que existe un scope compartido como hoy.
2. **Flags `*_fired`:** son la garantía de "una sola alerta por estrategia por día". Si una subfunción extraída no verifica el flag correcto antes de actuar (o lo verifica pero no lo actualiza correctamente), se reintroduce el riesgo de alertas duplicadas que ya costó dos fixes (v8.76 RPG, v8.84 doble evaluación V7).
3. **Interacción con P2 dinámico:** el P2 dinámico de canales bajistas se modifica desde 3 lugares distintos de la función (Canal-V1 especial, Caso A de Canales-V2-V7, y PM40 cuando actualiza `canal[simbolo]["p2"]`). Cualquier descomposición debe asegurar que estos 3 puntos sigan escribiendo sobre el mismo dict compartido `canal[simbolo]`, no copias.
4. **Interacción con 4PASOS:** 4PASOS lee `calcular_techo_canal`/`calcular_piso_mitad_canal` del mismo canal RCB que las estrategias de canal bajista — si el canal se apaga (por Canales-V2-V7) en la misma vela donde 4PASOS también se está evaluando, el orden actual (canales antes de 4PASOS) determina si 4PASOS ve el canal ya apagado o todavía activo. Preservar el orden es obligatorio por esta razón concreta, no solo por precaución general.
5. **Interacción con reset diario:** el reset diario puede disparar 1VR (vía reconstrucción) ANTES de que el flujo normal de V1 tenga oportunidad de evaluarlo en la misma llamada a la función — si ambos caminos llegaran a ejecutarse en la misma invocación (no debería pasar con el código actual, ya que el reset ocurre en una vela distinta a V1 normalmente, pero no hay una garantía explícita de que sean mutuamente excluyentes), podría dispararse 1VR dos veces. Esto no es un bug conocido hoy, pero es un riesgo a vigilar si se cambia cualquier cosa relacionada con el reset.

---

## 5. PROPUESTA DE SUB-SPRINTS

| Sprint | Alcance | Riesgo |
|---|---|---|
| **AX-012B** | Extraer `preparar_contexto_vela()` — la subfunción de menor riesgo (sección 2.1), pura, sin estado. | Bajo |
| **AX-012C** | Extraer `evaluar_gna()` y `evaluar_gba()` por separado (sección 2.5) — las estrategias más simples y simétricas. | Bajo-medio |
| **AX-012D** | Extraer `evaluar_rpg_activacion()` y `evaluar_rpg_disparo()` por separado (sección 2.4). | Medio |
| **AX-012E** | Unificar y extraer `evaluar_1vr()` (sección 2.3) — incluye consolidar el camino normal y el de reconstrucción en una sola función reutilizable, con pruebas exhaustivas comparando ambos caminos antes/después. | Medio |
| **AX-012F** | Extraer `evaluar_canal_v1()` y `evaluar_canal_v2_v7()` por separado (sección 2.8) — los 3 casos de ruptura deben mantenerse como un bloque if/elif/elif intacto dentro de la función extraída. | Medio-alto |
| **AX-012G** | Extraer `reset_diario_si_aplica()` (sección 2.2) — solo después de que AX-012E exista, para poder reutilizar `evaluar_1vr()` desde el camino de reconstrucción sin duplicar lógica. | Alto |
| **AX-012H** | Sub-dividir y extraer PM40 (sección 2.6) — probablemente en dos partes: PM40-V1 (inicialización) y PM40-V2-V7 (maduración/ruptura), cada una como su propio sub-sprint si el riesgo lo justifica. | Alto |
| **AX-012I** | Sub-dividir y extraer 4PASOS (sección 2.7) — mismo enfoque que PM40, posiblemente separando inicialización/búsqueda-de-P2/post-P2 en 3 piezas. | Alto |
| **AX-012J** | Una vez completos AX-012B a AX-012I, evaluar si introducir `persistir_estado_si_cambia()` (sección 2.9) tiene sentido — este es un cambio de comportamiento real (aunque de bajo riesgo), requiere aprobación explícita separada. | Medio (pero requiere aprobación de cambio de comportamiento) |

**Recomendación de orden:** B → C → D → E → F → G → H → I → J, exactamente en ese orden — cada sprint depende de que el anterior haya sido validado en producción durante al menos un día de mercado completo antes de proceder al siguiente, dado que cualquier regresión en `evaluar_activo()` afecta directamente la generación de alertas reales con dinero real de por medio (Tradier sandbox, pero con lógica idéntica a la que eventualmente correría en producción real).

---

*Documento generado en AX-012A. No se modificó ningún código durante su creación. evaluar_activo() permanece exactamente igual que antes de este sprint.*
