# fix_linea_canal.py — Linea del canal RCB/CNF no debe cortarse en fecha_ruptura
# si el canal esta actualmente activo (on=true). Solo se debe respetar el corte
# si el canal sigue inactivo. v1.4.2
# Corre desde: /Users/noellazaro/SPY-ALERT-SERVER/

import sys

with open("axis_charts.html", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD = '''        // Dibujar desde P1 hasta la última vela visible
        const startAbs = p1Idx;
        // Si canal roto → dibujar solo hasta la fecha de ruptura
        let endAbs = allVelas.length - 1;
        if (c.roto && c.fecha_ruptura) {
          for (let i = allVelas.length - 1; i >= 0; i--) {
            if ((allVelas[i].datetime||'').startsWith(c.fecha_ruptura)) {
              endAbs = i; break;
            }
          }
        }'''

NEW = '''        // Dibujar desde P1 hasta la última vela visible.
        // El corte por fecha_ruptura SOLO aplica si el canal sigue inactivo (on=false).
        // Si el canal esta activo (on=true), la linea se extiende hasta hoy
        // aunque haya tenido una ruptura en el pasado (canal reactivado).
        const startAbs = p1Idx;
        let endAbs = allVelas.length - 1;
        if (!c.on && c.roto && c.fecha_ruptura) {
          for (let i = allVelas.length - 1; i >= 0; i--) {
            if ((allVelas[i].datetime||'').startsWith(c.fecha_ruptura)) {
              endAbs = i; break;
            }
          }
        }'''

if OLD not in content:
    errors.append("Bloque de corte por fecha_ruptura no encontrado")
else:
    content = content.replace(OLD, NEW, 1)
    print("✅ Linea del canal ahora se extiende hasta hoy si el canal esta activo (on=true)")
    print("✅ El corte por fecha_ruptura solo aplica si el canal sigue inactivo")

content = content.replace('CHARTS v1.4.1', 'CHARTS v1.4.2')
print("✅ Versión axis_charts.html v1.4.2")

if errors:
    print("\n❌ ERRORES:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    with open("axis_charts.html", "w", encoding="utf-8") as f:
        f.write(content)
    print("\n✅ axis_charts.html v1.4.2 guardado")
    print("   git add axis_charts.html && git commit -m 'fix: linea canal no se corta si esta activo v1.4.2' && git push origin main")
