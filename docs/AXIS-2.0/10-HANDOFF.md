# AXIS 2.0 — HANDOFF

## Estado actual

Sistema en producción, estable, v8.84. AX-INF-001 (Tools Automation) ejecutado — 3 scripts de automatización creados en `tools/`, sin tocar server.py, lógica, ni producción. Probados en un repositorio git de prueba aislado (con git real y mocks de `pbcopy`/`curl`) antes de entregarse.

## Scripts creados en este sprint

1. **`tools/pre_sprint.sh`** — `git pull` + `git status` + `git log -3` + `py_compile` de `server.py` y todos los `axis_*.py` presentes (detecta automáticamente cuáles existen, sin fallar si no hay ninguno). Copia todo a clipboard con `pbcopy`.
2. **`tools/doc_summary.sh <ruta>`** — recibe la ruta de un documento como argumento. Si no se pasa argumento o el archivo no existe, imprime un mensaje claro y termina sin error silencioso. Ejecuta `git status` + `git log -1` + `head -80` + `tail -80` del documento. Copia todo a clipboard.
3. **`tools/chatgpt_report.sh`** — reporte completo: `git status`, `git log -3`, `py_compile` de `server.py` y todos los `axis_*.py`, `curl` a `/status` de Railway, `git show --stat --oneline HEAD`, y el diff del último commit específicamente para `server.py` y `docs/AXIS-2.0/10-HANDOFF.md`. Copia todo a clipboard.

Los 3 scripts terminan con `REPORT COPIED TO CLIPBOARD — paste with ⌘+V` y usan un archivo temporal (`mktemp`) para construir la salida antes de copiarla, evitando truncar la salida o tener problemas con `pbcopy` en pipes.

## Verificación realizada

Probados en un repositorio git real (aislado, en `/tmp`), no solo simulación de texto:
- `pre_sprint.sh`: detectó correctamente `server.py` + 2 archivos `axis_*.py` de prueba, los compiló, generó el reporte.
- `doc_summary.sh`: probado con documento real (100 líneas, confirma head/tail correctos), archivo inexistente (mensaje de error claro), y sin argumento (mensaje de uso).
- `chatgpt_report.sh`: probado con `curl` y `pbcopy` mockeados (sin red real ni clipboard real disponible en el entorno de prueba), confirmando que las 7 secciones aparecen en el orden correcto y con el contenido esperado.

## Archivos modificados en este sprint

- **Creados:** `tools/pre_sprint.sh`, `tools/doc_summary.sh`, `tools/chatgpt_report.sh` (los 3 con permisos de ejecución `+x`).
- **Modificado:** `docs/AXIS-2.0/10-HANDOFF.md` (este archivo).
- **Sin cambios en código de producción** (server.py ni ningún axis_*.py).

## Último commit antes de este sprint

(commit de AX-012D, ver historial de git)

## Rama

main

## Sprint activo

AX-INF-001 — Tools Automation (este sprint)

## Próximo sprint sugerido

Continuar con **AX-012E** (según el orden de `05-STRATEGY-ENGINE-DESIGN.md`): extraer `evaluar_rpg_activacion()` y `evaluar_rpg_disparo()` por separado. Los nuevos scripts de `tools/` pueden usarse desde aquí en adelante para acelerar la verificación inicial y los reportes de cada sub-sprint.

## Riesgos abiertos

(Ver lista completa en `04-ARCHITECTURE-AUDIT.md` sección 6 y `05-STRATEGY-ENGINE-DESIGN.md` sección 4. Sin riesgos nuevos de este sprint — es infraestructura de tooling, no afecta el comportamiento del sistema.)

## Notas para quien continúe

- Leer siempre el AXIS_MASTER más reciente antes de cualquier cambio
- Leer `05-STRATEGY-ENGINE-DESIGN.md` antes de cualquier sub-sprint de extracción de evaluar_activo()
- Nunca codificar sin autorización explícita de Noel
- Usar `tools/pre_sprint.sh` al inicio de cada sprint nuevo en vez de escribir el comando de verificación a mano cada vez
- Usar `tools/chatgpt_report.sh` cuando se necesite compartir el estado completo del sistema con un asistente de IA externo (ChatGPT u otro)
- `tools/doc_summary.sh` es útil para revisar rápidamente cualquier documento largo de `docs/AXIS-2.0/` sin tener que abrirlo completo
