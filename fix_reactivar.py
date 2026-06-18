# fix_reactivar.py — Botón reactivar canal roto v1.4.1
# Solo modifica axis_charts.html
# 1. Agrega botón REACTIVAR en banner de canal desactivado
# 2. Agrega función reactivarCanal() que pre-llena el panel con valores actuales
# Corre desde: /Users/noellazaro/SPY-ALERT-SERVER/

import sys

with open("axis_charts.html", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

# ═══════════════════════════════════════════════════════
# CAMBIO 1 — Agregar botón REACTIVAR en banner rojo
# ═══════════════════════════════════════════════════════
OLD_BANNER = '''    <div id="ps-apagado-banner" style="display:none;background:rgba(248,81,73,0.12);border:1px solid #f85149;border-radius:6px;padding:6px 10px;margin-bottom:8px;font-size:11px;color:#f85149;font-family:'JetBrains Mono',monospace;letter-spacing:0.5px;">
      🔕 CANAL DESACTIVADO
    </div>'''

NEW_BANNER = '''    <div id="ps-apagado-banner" style="display:none;background:rgba(248,81,73,0.12);border:1px solid #f85149;border-radius:6px;padding:6px 10px;margin-bottom:8px;font-size:11px;color:#f85149;font-family:'JetBrains Mono',monospace;letter-spacing:0.5px;">
      🔕 CANAL DESACTIVADO
      <button onclick="reactivarCanal()" style="margin-left:10px;padding:2px 8px;font-size:10px;background:#3a1a1a;border:1px solid #f85149;border-radius:4px;color:#f85149;cursor:pointer;font-family:'JetBrains Mono',monospace;">🔄 REACTIVAR</button>
    </div>'''

if OLD_BANNER not in content:
    errors.append("CAMBIO 1: banner ps-apagado-banner no encontrado")
else:
    content = content.replace(OLD_BANNER, NEW_BANNER, 1)
    print("✅ Cambio 1: botón REACTIVAR agregado al banner")

# ═══════════════════════════════════════════════════════
# CAMBIO 2 — Agregar función reactivarCanal() antes de activarCanal()
# ═══════════════════════════════════════════════════════
OLD_ACTIVAR_FUNC = '''async function activarCanal() {'''

NEW_ACTIVAR_FUNC = '''async function reactivarCanal() {
  // Pre-llena el panel con valores del canal roto para confirmar o editar
  const estado = canalCache[activo];
  if (!estado) { showToast('⚠️ No hay datos del canal'); return; }

  // Pre-llenar P1
  if (estado.p1) {
    document.getElementById('ps-p1-high').value  = estado.p1.high ?? '';
    document.getElementById('ps-p1-fecha').value = estado.p1.fecha ?? '';
    const p1vela = Object.entries(VELA_HORA).find(([k,v]) => v === estado.p1.hora_est);
    if (p1vela) document.getElementById('ps-p1-vela').value = p1vela[0];
  }

  // Pre-llenar P2
  if (estado.p2) {
    document.getElementById('ps-p2-high').value  = estado.p2.high ?? '';
    document.getElementById('ps-p2-fecha').value = estado.p2.fecha ?? '';
    const p2vela = Object.entries(VELA_HORA).find(([k,v]) => v === estado.p2.hora_est);
    if (p2vela) document.getElementById('ps-p2-vela').value = p2vela[0];
  }

  // Pre-llenar P3 si existe
  if (estado.p3) {
    document.getElementById('ps-p3-low').value   = estado.p3.low ?? '';
    document.getElementById('ps-p3-fecha').value = estado.p3.fecha ?? '';
    const p3vela = Object.entries(VELA_HORA).find(([k,v]) => v === estado.p3.hora_est);
    if (p3vela) document.getElementById('ps-p3-vela').value = p3vela[0];
  }

  showToast('✏️ Confirma o edita los valores y presiona ACTIVAR CANAL');
}

async function activarCanal() {'''

if OLD_ACTIVAR_FUNC not in content:
    errors.append("CAMBIO 2: función activarCanal() no encontrada")
else:
    content = content.replace(OLD_ACTIVAR_FUNC, NEW_ACTIVAR_FUNC, 1)
    print("✅ Cambio 2: función reactivarCanal() agregada")

# ═══════════════════════════════════════════════════════
# CAMBIO 3 — Version axis_charts.html v1.4.1
# ═══════════════════════════════════════════════════════
content = content.replace('axis_charts.html | v1.4.0', 'axis_charts.html | v1.4.1')
print("✅ Cambio 3: versión axis_charts.html v1.4.1")

# ═══════════════════════════════════════════════════════
# VERIFICACION
# ═══════════════════════════════════════════════════════
if errors:
    print("\n❌ ERRORES:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    with open("axis_charts.html", "w", encoding="utf-8") as f:
        f.write(content)
    print("\n✅ axis_charts.html v1.4.1 guardado — botón REACTIVAR implementado")
    print("   git add axis_charts.html && git commit -m 'feat: boton reactivar canal roto v1.4.1' && git push origin main")

