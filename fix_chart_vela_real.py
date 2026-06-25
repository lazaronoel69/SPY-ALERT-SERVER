import sys

with open("axis_charts.html", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

# Cambio: usar la vela real (d.vela) que ahora viene del backend
# en vez de anclar siempre a V1
OLD_DIBUJO_HOY = """  (window.senalesHoy || []).forEach(s => {
    // Buscar la vela V1 de hoy para anclar la etiqueta
    for (let i = zoomStart; i <= zoomEnd; i++) {
      const v = allVelas[i];
      const fv = new Date(v.x).toLocaleDateString(\'en-US\',{timeZone:\'America/New_York\'});
      if (fv === fechaHoyNY && v.vela === \'V1\') {
        const visIdx = i - zoomStart;
        const x = xOf(visIdx);
        const y = yOf(v.h);
        const color     = s.tipo === \'1VR\' ? \'#f85149\' :
                          s.tipo === \'RPG\' ? \'#9c27b0\' :
                          s.tipo === \'GNA\' ? \'#00bcd4\' :
                          s.tipo === \'GBA\' ? \'#f0b429\' :
                          s.tipo === \'PM40\'? \'#3fb950\' :
                          s.tipo === \'4PS\' ? \'#e74c3c\' : \'#ffffff\';
        const textColor = [\'GBA\',\'PM40\'].includes(s.tipo) ? \'#000\' : \'#fff\';
        dibujarSeñal(ctx, x, y, s.tipo, color, textColor, true);
        break;
      }
    }
  });"""

NEW_DIBUJO_HOY = """  (window.senalesHoy || []).forEach(s => {
    // Usar la vela REAL donde Railway disparo la senal (viene del backend desde v8.81).
    // Si por compatibilidad no viene vela (senales viejas), usar V1 como fallback.
    const velaObjetivo = s.vela || \'V1\';
    for (let i = zoomStart; i <= zoomEnd; i++) {
      const v = allVelas[i];
      const fv = new Date(v.x).toLocaleDateString(\'en-US\',{timeZone:\'America/New_York\'});
      if (fv === fechaHoyNY && v.vela === velaObjetivo) {
        const visIdx = i - zoomStart;
        const x = xOf(visIdx);
        const y = yOf(v.h);
        const color     = s.tipo === \'1VR\' ? \'#f85149\' :
                          s.tipo === \'RPG\' ? \'#9c27b0\' :
                          s.tipo === \'GNA\' ? \'#00bcd4\' :
                          s.tipo === \'GBA\' ? \'#f0b429\' :
                          s.tipo === \'PM40\'? \'#3fb950\' :
                          s.tipo === \'4PS\' ? \'#e74c3c\' : \'#ffffff\';
        const textColor = [\'GBA\',\'PM40\'].includes(s.tipo) ? \'#000\' : \'#fff\';
        dibujarSeñal(ctx, x, y, s.tipo, color, textColor, true);
        break;
      }
    }
  });"""

if OLD_DIBUJO_HOY not in content:
    errors.append("Bloque de dibujo senalesHoy no encontrado exacto")
else:
    content = content.replace(OLD_DIBUJO_HOY, NEW_DIBUJO_HOY, 1)
    print("Cambio OK: senales de hoy se dibujan en la vela REAL, no siempre V1")

content = content.replace("CHARTS v1.4.2", "CHARTS v1.4.3")
print("Version axis_charts.html v1.4.3")

if errors:
    print("ERRORES:")
    for e in errors:
        print("  - " + e)
    sys.exit(1)
else:
    with open("axis_charts.html", "w", encoding="utf-8") as f:
        f.write(content)
    print("axis_charts.html v1.4.3 guardado")
