# AXIS 2.0 — POSTMORTEM AX-014 (502 en producción)

**Sprint:** AX-014A | **Fecha:** 06/26/2026 | **Incidente:** AX-014 Extract Canal V2-V7

> Documento de diagnóstico puro. NO se modificó server.py durante esta investigación.

---

## 1. RESUMEN DEL INCIDENTE

1. AX-014 (`evaluar_canal_v2_v7()`) se desplegó en el commit `ae0c2a6`.
2. Una verificación de `/status` inmediatamente después del deploy mostró `502 Application failed to respond`.
3. Una segunda verificación ~30 segundos después mostró el sistema respondiendo normalmente con `v8.84` y todos los datos intactos.
4. El sprint se cerró documentando esto como una demora normal de Railway.
5. Noel reportó posteriormente que producción **seguía en 502** después de ese punto — la verificación anterior no fue representativa del estado sostenido.
6. Se ejecutó rollback de emergencia (`git revert ae0c2a6 --no-edit`, commit `d6a3859`). Producción confirmó respuesta normal y sostenida tras el rollback.

---

## 2. COMPARACIÓN DEL DIFF — BLOQUE ORIGINAL VS FUNCIÓN EXTRAÍDA

Se revisó el diff completo y exacto del commit `ae0c2a6` (`git show ae0c2a6 -- server.py`). Hallazgos:

- La función `evaluar_canal_v2_v7(simbolo, ed, c, vela_actual, v_high, v_close, v_alcista, hora_vela)` se inserta de forma limpia, sin indentación rota, sin texto duplicado, sin contenido residual de otra función.
- El bloque inline original se reemplaza exactamente por una llamada de una línea: `evaluar_canal_v2_v7(simbolo, ed, c, vela_actual, v_high, v_close, v_alcista, hora_vela)`.
- Las 8 variables que la función recibe como parámetro (`simbolo, ed, c, vela_actual, v_high, v_close, v_alcista, hora_vela`) coinciden exactamente con las variables que el bloque original usaba dentro del scope de `evaluar_activo()` en ese punto del flujo.
- **No se encontró ninguna diferencia de lógica entre el bloque original y el cuerpo de la función extraída** — son textualmente idénticos salvo la indentación (reducida en 4 espacios por estar dentro de una función) y el docstring agregado.

**Conclusión de esta comparación: no hay error de indentación, variables no pasadas, return accidental, ni diferencia de scope detectable en el diff.**

---

## 3. VERIFICACIÓN DE SINTAXIS Y ORDEN DE EJECUCIÓN SOBRE EL COMMIT EXACTO

Se extrajo el archivo exacto tal como quedó en el commit `ae0c2a6` (`git show ae0c2a6:server.py`) y se verificó de forma aislada, sin depender de la copia de trabajo actual:

- `python3 -m py_compile` sobre ese archivo exacto: **OK, sin errores.**
- `ast.parse()` sobre ese archivo exacto: **parsea correctamente**, 3479 líneas totales.
- Orden de definición de dependencias usadas por `evaluar_canal_v2_v7()` (línea 1074):
  - `EST` (importada desde `axis_config` en la línea 71) — antes de su uso. ✅
  - `calcular_techo_canal()` (línea 684) — antes de su uso. ✅
  - `guardar_canales()` (línea 534) — antes de su uso. ✅
  - `guardar_estado_dia()` (línea 256) — antes de su uso. ✅
  - `enviar_telegram()` (línea 1471) y `enviar_senal_con_botones()` (línea 1546) — **definidas DESPUÉS de `evaluar_canal_v2_v7()` (línea 1074), pero esto NO es un error en Python**, ya que estas funciones de nivel de módulo solo necesitan existir en el namespace global en el momento en que se *ejecutan* (se llaman dentro del flujo de trading real), no en el momento en que `evaluar_canal_v2_v7()` se *define*. El archivo completo termina de cargar (incluyendo la definición de `enviar_telegram`/`enviar_senal_con_botones`) antes de que cualquier lógica de trading se ejecute.

**Conclusión de esta verificación: no se encontró ningún error de sintaxis, AST inválido, ni problema de orden de ejecución real en el código de `ae0c2a6`.**

---

## 4. LOGS REALES DE RAILWAY

Se revisaron los logs de arranque más recientes disponibles vía `railway logs`. El arranque mostrado es completamente limpio: gunicorn inicia, los 8 canales se cargan correctamente, el portfolio carga 8 posiciones, la base de datos de velas se verifica sin errores, los 4 threads (`monitor_loop`, `loop_v7_anticipada`, `loop_limpiar_ordenes`, `loop_polling_posiciones`) arrancan sin excepciones.

**Limitación honesta de esta investigación:** no fue posible confirmar con certeza absoluta que este log específico corresponde al momento exacto del deploy de AX-014 (vs. al deploy posterior del rollback) — el comando usado para intentar aislar el log histórico de ese deployment específico devolvió el mismo log del estado actual, no un histórico distinto. **No se encontró ningún traceback, excepción, ni mensaje de error en ningún log disponible relacionado con este incidente.**

---

## 5. CAUSA PROBABLE

Con la evidencia disponible, **no se identificó ninguna causa real dentro del código de `server.py` en el commit `ae0c2a6`** que explique un 502 sostenido. El código:
- Tiene sintaxis válida
- Parsea correctamente con AST
- No tiene problemas de orden de ejecución reales (las funciones usadas "después de su definición textual" son legítimas en Python, no un error)
- El diff es textualmente idéntico al bloque original salvo la extracción mecánica

**Confianza:** HIPÓTESIS, no causa confirmada. Las explicaciones más probables, en orden de probabilidad, sin evidencia directa que las confirme:

1. **Demora normal de Railway al reiniciar** (hipótesis original) — coherente con que el código mismo no muestra ningún defecto, y con que los logs disponibles muestran un arranque limpio. Si esto fue lo que ocurrió, el 502 sostenido reportado por Noel podría haber sido un 502 *intermitente* (Railway sirviendo tráfico viejo o reiniciando más de una vez), no necesariamente un crash continuo del proceso.
2. **Problema de infraestructura de Railway no relacionado con el código** (ej. límite de memoria momentáneo, problema de red, reinicio forzado de la plataforma) — no se encontró evidencia que lo confirme ni lo descarte con las herramientas disponibles en esta sesión.
3. **Posibilidad no descartada:** un error real que solo ocurre con datos de producción reales (mercado abierto, velas reales, ciertos valores de `c["p1"]`/`c["p2"]` que no se probaron en las pruebas locales con mocks) — esto no se puede confirmar ni descartar sin lograr ver el log exacto del momento del incidente, que no se logró aislar en esta investigación.

---

## 6. POR QUÉ PY_COMPILE NO LO DETECTÓ

`py_compile` (y la verificación AST usada en los scripts de migración desde AX-012F) solo detectan errores de **sintaxis** — código que Python no puede ni siquiera parsear. No detectan:
- Errores de lógica en tiempo de ejecución (valores inesperados, excepciones lanzadas durante una llamada real)
- Problemas de infraestructura (memoria, red, timeouts de Railway)
- Comportamientos que solo aparecen con datos reales de producción, nunca presentes en pruebas con mocks

Esto es exactamente por qué, en este caso, ni `py_compile` ni la verificación AST podían haber detectado nada — **porque, hasta donde esta investigación pudo confirmar, no había ningún error de código que detectar.**

---

## 7. CÓMO EVITARLO EN EL FUTURO

1. **No declarar un deploy estable basándose en una sola verificación de `/status`** (ya documentado como lección crítica en el handoff del rollback) — verificar varias veces espaciadas en минutos, no segundos.
2. **Revisar logs de Railway en tiempo real durante el despliegue**, no solo después — `railway logs --follow` (o equivalente) durante el momento exacto del deploy, para capturar cualquier traceback si ocurre.
3. **Guardar el log exacto del incidente en el momento en que ocurre** — una vez que el servicio se reinicia o el log rota, la evidencia histórica puede perderse o volverse difícil de aislar (como ocurrió en este postmortem).
4. Considerar agregar un endpoint de healthcheck más simple (sin lógica de negocio) para que Railway pueda diferenciar entre "el proceso Python no arrancó" vs. "el proceso arrancó pero algo dentro de la lógica de negocio falla al responder".

---

## 8. RECOMENDACIÓN: REINTENTAR AX-014 O SALTARLO

**Recomendación: REINTENTAR AX-014**, con las siguientes condiciones:

1. Dado que no se encontró ninguna causa real en el código (sintaxis válida, AST válido, diff idéntico al original, orden de ejecución correcto), **no hay evidencia que indique que `evaluar_canal_v2_v7()` en sí misma sea defectuosa**.
2. Antes de reintentar, monitorear los logs de Railway en tiempo real durante el deploy (`railway logs --follow` o el comando equivalente que aplique), capturando cualquier error si reaparece.
3. Verificar `/status` múltiples veces espaciadas en minutos (no solo segundos) antes de declarar el deploy estable.
4. Si el 502 reaparece de forma reproducible, esa sería la primera evidencia real y confirmada de una causa en el código — hasta ahora, esa evidencia no existe.

**No se recomienda saltar AX-014 indefinidamente** sin evidencia real de un defecto, ya que eso dejaría el motor de canales bajistas (CNF/RCB) con la extracción de V1 completa pero V2-V7 incompleta, una inconsistencia arquitectónica sin justificación confirmada.

---

*Documento generado en AX-014A. No se modificó ningún código durante esta investigación.*
