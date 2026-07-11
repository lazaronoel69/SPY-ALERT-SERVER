# AX-TRACK-001 — Alert Lifecycle Foundation

## Objetivo único

Registrar de forma persistente el 100% de las alertas reales generadas por
AXIS y conservar un vínculo único desde su nacimiento hasta su decisión,
posición y cierre, sin modificar condiciones ni parámetros de estrategias.

## Persistencia

AXIS conserva su arquitectura existente: JSON bajo el volumen `/data`.
El nuevo archivo es `/data/axis_alertas.json`. No se introduce base de datos.

## Identidad

Cada alerta recibe un identificador inmutable:

`A-YYYYMMDD-XXXXXXXX`

El identificador se copia a la orden pendiente y, si se ejecuta, a la
posición. Nunca se reutiliza.

## Estados

| Estado | Significado |
|---|---|
| `GENERATED` | La estrategia produjo la señal y AXIS creó su expediente. |
| `NOTIFIED` | La alerta fue publicada para decisión manual o notificada. |
| `ACTIVE` | La operación fue ejecutada y existe una posición vinculada. |
| `CLOSED` | La posición vinculada terminó y tiene resultado final. |
| `CANCELLED` | Fue ignorada, expiró o no pudo convertirse en operación. |

## Reglas permanentes del sprint

1. El expediente se crea antes de intentar obtener la opción o notificar.
2. Las alertas sin datos de opción también quedan registradas.
3. Ignorar o dejar expirar una alerta produce `CANCELLED`, no pérdida de datos.
4. Una ejecución copia `alert_id` a la posición.
5. El cierre copia P&L, precio, duración y motivo al expediente.
6. HED usa el mismo expediente aunque su ejecución sea automática.
7. Ningún punto de este sprint cambia condiciones de disparo de estrategias.

## Consulta verificable

`GET /alerts/data` permite filtrar por `alert_id`, `fecha`, `simbolo`,
`estrategia` y `estado`. Es una ruta de solo lectura.

## Criterios de aceptación

- Toda llamada productiva de señal crea un `alert_id` persistente.
- El ID sobrevive a reinicios porque vive en `/data`.
- La decisión de Telegram actualiza el mismo expediente.
- Una posición ejecutada contiene el mismo ID.
- El cierre actualiza ese expediente a `CLOSED` con resultado.
- El flujo HED queda cubierto.
- El motor de estrategias y sus condiciones permanecen sin cambios.
