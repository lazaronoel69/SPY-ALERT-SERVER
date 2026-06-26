# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-009 (Channels Baseline) ejecutado — `canal_vacio`, `CANALES_DEFAULT`, `guardar_canales` y `cargar_canales` movidas a `axis_channels.py`, sin cambiar estructura JSON, cálculo de techo/piso/mitad, ni lógica de P2 dinámico. Verificado con py_compile, simulación de import real, y prueba funcional de `cargar_canales()` modificando el dict global `canal` in-place.

## Funciones/datos movidos a axis_channels.py (AX-009)

1. `canal_vacio()` — función pura, sin cambios.
2. `CANALES_DEFAULT` — diccionario de canales precargados (SPY CNF, GLD RCB), sin cambios.
3. `guardar_canales(canal, ACTIVOS, CANALES_FILE)` — recibe `canal` y `ACTIVOS` como parámetros (también `CANALES_FILE`, ya que vive en `axis_config.py` pero la función necesita la ruta).
4. `cargar_canales(canal, ACTIVOS, CANALES_FILE, EST)` — recibe `canal`, `ACTIVOS`, `CANALES_FILE` y `EST` como parámetros; modifica `canal` **in-place**, igual que la versión original con los globales de server.py.

server.py mantiene wrappers `guardar_canales()` y `cargar_canales()` sin argumentos que llaman a estas funciones pasando sus propios globales (`canal`, `ACTIVOS`, `CANALES_FILE`, `EST`) — preservando exactamente el mismo efecto observable.

## Funciones NO movidas y razón (según regla explícita del sprint)

- **`calcular_techo_canal(simbolo, ahora_dt)`** — cálculo matemático del techo proyectado (slope P1→P2). Excluida explícitamente.
- **`calcular_piso_mitad_canal(simbolo, ahora_dt)`** — cálculo de piso y mitad para canales RCB. Excluida explícitamente.
- **Lógica de P2 dinámico** — vive dentro de `evaluar_activo()` (Casos A/B/C de ruptura de canal, y la lógica especial de V1). Excluida explícitamente — `evaluar_activo()` no se tocó en absoluto.

## Archivos modificados en este sprint

- **Creado:** `axis_channels.py` — estructura básica y persistencia de canales.
- **Modificado:** `server.py` — wrappers que preservan los globales `canal`, `ACTIVOS`, `CANALES_FILE`, `EST`.

## Último commit antes de este sprint

86eace0 — AX-008 Portfolio Baseline

## Rama

main

## Sprint activo

AX-009 — Channels Baseline (este sprint)

## Próximo sprint sugerido

AX-010 — mover `archivar_señales_dia` (dependencia de `estado_dia[]` y `ACTIVOS`, pendiente desde AX-005) usando el mismo patrón de parámetro+wrapper, o iniciar un sprint dedicado a documentar/extraer `calcular_techo_canal`/`calcular_piso_mitad_canal` como funciones puras en un módulo "Channel Math" separado de la persistencia (este sprint solo cubrió estructura/persistencia, no el cálculo).

## Riesgos abiertos

1. GLD sin canal bajista activo actualmente (nota: el CANALES_DEFAULT tiene GLD con `on: True` precargado — si el archivo `axis_canales.json` real en Railway ya tiene GLD desactivado, el archivo JSON real prevalece sobre el default, sin cambios en este sprint)
2. Pendiente verificar visualmente que no hay alertas duplicadas tras v8.84
3. 4PASOS solo dentro de RCB
4. Tradier limita historial de 15min a ~40 días
5. Bug cosmético: chart marca "EN FORMACIÓN" en la última vela ya cerrada
6. Frontend aún calcula canales PM40/4PASOS en JavaScript
7. TWELVEDATA_KEY y FINNHUB_KEY siguen hardcodeados en server.py (ver AX-003)
8. TRADIER_TOKEN/TRADIER_ACCOUNT/TRADIER_HEADERS duplicados en server.py y axis_tradier.py (ver AX-004)
9. archivar_señales_dia aún sin mover (ver AX-005)
10. TELEGRAM_TOKEN/TELEGRAM_CHAT_ID duplicados en server.py y axis_telegram.py (ver AX-006)
11. enviar_telegram_botones sigue acoplada a Portfolio/Derby en server.py (ver AX-006)
12. registrar_posicion/cerrar_posicion siguen en server.py (ver AX-008)
13. **NUEVO AX-009:** `guardar_canales`/`cargar_canales` ahora reciben 3-4 parámetros (más que los patrones anteriores de AX-005/AX-007/AX-008, que recibían 1) — funcional pero ligeramente más verboso. Si en un futuro sprint se decide centralizar `ACTIVOS`/`EST` de forma diferente, revisar esta firma.
14. **NUEVO AX-009:** `calcular_techo_canal` y `calcular_piso_mitad_canal` permanecen acopladas al global `canal` en server.py — son las funciones matemáticas más importantes del motor de canales y quedan como candidatas de alto valor para un futuro "Channel Math" module, separado de este "Channels Baseline" que solo cubrió persistencia.

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Nunca codificar sin autorización explícita de Noel
- Verificar sintaxis y simular orden de ejecución real después de cualquier fix (lección del crash de import os, 06/25)
- axis_channels.py no debe crecer para incluir calcular_techo_canal, calcular_piso_mitad_canal, ni lógica de P2 dinámico — solo estructura y persistencia básica, según el alcance explícito de AX-009
