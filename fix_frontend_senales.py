import sys

with open("axis_charts.html", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

# CAMBIO 1 -- eliminar dibujo de senales recalculadas en JS (todasSeñales)
OLD1 = '  // Dibujar etiquetas de señales recalculadas (históricas)\n  todasSeñales.forEach(s => {\n    const visIdx = s.idx - zoomStart;\n    if (visIdx < 0 || visIdx >= visible.length) return;\n    const v  = visible[visIdx];\n    const x  = xOf(visIdx);\n    const y  = s.arriba ? yOf(v.h) : yOf(v.l);\n    dibujarSeñal(ctx, x, y, s.tipo, s.color, s.textColor, s.arriba);\n  });'

NEW1 = '  // v1.4.4: ELIMINADO el dibujo de señales recalculadas en JS (todasSeñales).\n  // Esa logica duplicaba y desincronizaba las etiquetas del backend real\n  // (causaba 1VR/GBA/RPG apareciendo en velas o dias equivocados, y\n  // estrategias disparando "2 veces" visualmente cuando el backend solo\n  // disparo una vez). Ahora el chart SOLO dibuja lo que Railway evaluo:\n  // - señalesHoy (dia actual, con vela real desde v8.81)\n  // - señalesHistoricas (dias pasados, con vela real desde v8.84)\n  // Los canales (PM40/4PASOS) siguen calculandose en JS por ahora --\n  // son lineas/zonas, no etiquetas de senal, y no tienen el mismo bug.'

if OLD1 not in content:
    errors.append("CAMBIO 1: bloque dibujo todasSeñales no encontrado")
else:
    content = content.replace(OLD1, NEW1, 1)
    print("Cambio 1 OK: eliminado dibujo de señales recalculadas en JS")

# CAMBIO 2 -- senales historicas usan vela real + deduplican por tipo/dia
OLD2 = "  Object.entries(señalesHistoricas).forEach(([fecha, estrategias]) => {\n    // Filtrar estrategias visibles según toggles\n    const visibles = estrategias.filter(e => stratState[e] !== false);\n    if (!visibles.length) return;\n    // Buscar V1 de esa fecha en visible\n    for (let i = zoomStart; i <= zoomEnd; i++) {\n      const v  = allVelas[i];\n      const fv = (v.datetime||'').slice(0,10);\n      if (fv === fecha && v.vela === 'V1') {\n        const visIdx = i - zoomStart;\n        const x = xOf(visIdx);\n        let yOffset = 0;\n        visibles.forEach(strat => {\n          const [color, textColor] = STRAT_COLORS[strat] || ['#fff','#000'];\n          const y = yOf(v.h) - yOffset;\n          dibujarSeñal(ctx, x, y, strat, color, textColor, true);\n          yOffset += 18;\n        });\n        break;\n      }\n    }\n  });"

NEW2 = "  // v1.4.4: usa la VELA REAL guardada por el backend (desde v8.84) para\n  // cada senal historica, en vez de anclar siempre a V1. Tambien aplica\n  // deduplicacion: si el backend ya garantiza 1 senal por tipo por dia,\n  // el frontend nunca debe dibujar mas de 1 etiqueta del mismo tipo el\n  // mismo dia (evita el bug GBA en V2 + GBA+2 en V7 el mismo dia).\n  Object.entries(señalesHistoricas).forEach(([fecha, señales]) => {\n    // señales ahora es: [{tipo, vela, hora}, ...] desde v8.84.\n    // Compatibilidad: si vienen como strings simples (datos viejos pre-v8.84),\n    // se tratan igual que antes, ancladas a V1.\n    const lista = señales.map(s => (typeof s === 'string') ? { tipo: s, vela: 'V1', hora: null } : s);\n    const vistos = new Set();\n    const visibles = lista.filter(s => {\n      if (stratState[s.tipo] === false) return false;\n      if (vistos.has(s.tipo)) return false;  // solo 1 etiqueta por tipo por dia\n      vistos.add(s.tipo);\n      return true;\n    });\n    if (!visibles.length) return;\n\n    visibles.forEach(s => {\n      const velaObjetivo = s.vela || 'V1';\n      for (let i = zoomStart; i <= zoomEnd; i++) {\n        const v  = allVelas[i];\n        const fv = (v.datetime||'').slice(0,10);\n        if (fv === fecha && v.vela === velaObjetivo) {\n          const visIdx = i - zoomStart;\n          const x = xOf(visIdx);\n          const [color, textColor] = STRAT_COLORS[s.tipo] || ['#fff','#000'];\n          dibujarSeñal(ctx, x, yOf(v.h), s.tipo, color, textColor, true);\n          break;\n        }\n      }\n    });\n  });"

if OLD2 not in content:
    errors.append("CAMBIO 2: bloque señalesHistoricas no encontrado")
else:
    content = content.replace(OLD2, NEW2, 1)
    print("Cambio 2 OK: señales historicas usan vela real, deduplicadas por tipo/dia")

content = content.replace("CHARTS v1.4.3", "CHARTS v1.4.4")
print("Version axis_charts.html v1.4.4")

if errors:
    print("ERRORES:")
    for e in errors:
        print("  - " + e)
    sys.exit(1)
else:
    with open("axis_charts.html", "w", encoding="utf-8") as f:
        f.write(content)
    print("axis_charts.html v1.4.4 guardado")
