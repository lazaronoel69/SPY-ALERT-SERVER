# AX-TRACK-AUDIT-002 — Segunda reconciliación

**Fecha de corte técnico:** 2026-08-05 09:37 EST

**Período completo de alertas:** 2026-07-27 → 2026-08-04

**Producción:** AXIS v8.94, commit `0e2e1cb`

**Alcance:** actualización incremental desde AX-TRACK-AUDIT-001. La sesión del
5 de agosto estaba abierta y no se incluye como día estadístico completo.

## Resultado ejecutivo

**RECONCILIACIÓN APROBADA CON DOS EXCEPCIONES P1**

| Control | Resultado |
|---|---:|
| Alertas acumuladas | 146 |
| Alertas nuevas del período | 65 |
| Cerradas acumuladas | 64 |
| Nuevos cierres desde AUDIT-001 | 39 |
| Alertas activas | 25 |
| Posiciones abiertas | 27 |
| Canceladas acumuladas | 57 |
| Alertas ACTIVE sin posición | 0 |
| Posiciones con alerta ACTIVE | 25 |
| Posiciones sin `alert_id` | 2 |
| Cierres sin resultado completo | 0 |
| Posiciones activas sin MFE/MAE | 0 |
| Posiciones vencidas aún activas | 0 |

## Excepciones P1

El 2026-08-03 se crearon dos posiciones internas sin `alert_id`, órdenes de
Tradier ni GTC:

| Position ID | Símbolo | Estrategia | Resultado de la alerta relacionada |
|---|---|---|---|
| `7bdc1646` | AAPL | 1VR | `CANCELLED — TRADIER_EXECUTION_FAILED` |
| `f910c02a` | GLD | 1VR | `CANCELLED — TRADIER_EXECUTION_FAILED` |

La causa está confirmada en el flujo actual: `registrar_posicion()` se ejecuta
aunque Tradier devuelva error; después la alerta se cancela y la posición queda
sin vínculo. Estas dos posiciones deben excluirse del tuning y corregirse o
cerrarse mediante un sprint autorizado. Este reporte no modifica producción.

## Nuevos cierres por estrategia

| Estrategia | Cierres | W-L | P&L medio | MFE medio | MAE medio |
|---|---:|---:|---:|---:|---:|
| 1VR | 30 | 17-13 | +45.41% | +107.15% | -59.84% |
| GBA+2 | 3 | 0-3 | -99.61% | +10.14% | -99.61% |
| RPG | 2 | 1-1 | +32.98% | +116.89% | -59.47% |
| GNA | 2 | 1-1 | +13.05% | +82.67% | -49.85% |
| CNF | 1 | 1-0 | +100.48% | +105.04% | -71.94% |
| GBA | 1 | 1-0 | +100.67% | +101.56% | -20.00% |

De los 39 nuevos cierres, 21 terminaron por GTC y 18 por vencimiento.

## Acumulado útil para análisis

| Estrategia | Cerradas | W-L | P&L medio cerrado |
|---|---:|---:|---:|
| 1VR | 44 | 29-15 | +56.22% |
| GBA+2 | 7 | 1-6 | -70.78% |
| RPG | 4 | 3-1 | +73.17% |
| GNA | 2 | 1-1 | +13.05% |
| GNA+2 | 2 | 0-2 | -99.70% |
| RPG+ | 2 | 1-1 | +5.88% |
| GBA | 2 | 2-0 | +100.34% |
| CNF | 1 | 1-0 | +100.48% |

## Lectura preliminar

- 1VR ya tiene 44 cierres y permite análisis exploratorio por activo, horario,
  MFE, MAE y duración.
- Su 65.9% de cierres ganadores es prometedor, pero el MAE medio de -56.60%
  confirma riesgo intraposición elevado.
- Los resultados son muy binarios: muchas posiciones alcanzan el GTC cercano
  a +100% y muchas vencen cerca de -100%. La política de salida influye tanto
  como la entrada y debe analizarse por separado antes del tuning.
- GBA+2 presenta una señal negativa consistente, pero siete cierres siguen
  siendo una muestra pequeña para modificar la estrategia.
- Las demás estrategias todavía no tienen muestra suficiente.

## Decisión

1. Conservar este reporte como segunda línea base incremental.
2. Excluir las dos posiciones huérfanas de cualquier estadística de tuning.
3. Proponer un sprint separado para impedir posiciones cuando Tradier falle y
   reconciliar las dos posiciones existentes.
4. Iniciar análisis profundo de 1VR sin cambiar todavía sus reglas.
5. Continuar reconciliaciones semanales después del cierre de cada semana.

## Evidencia

Dataset incremental de los 39 nuevos resultados terminales:
[`data/2026-08-05-AX-TRACK-AUDIT-002.csv`](data/2026-08-05-AX-TRACK-AUDIT-002.csv)
