# fix_4pasos.py - 4PASOS reglas nuevas P1/P2 con proyeccion v8.78
# Cambios:
# 1. Antes de tener P2: se traza proyeccion imaginaria P1->vela_actual y se verifica
#    si alguna vela INTERMEDIA rompe esa proyeccion hacia abajo -> reinicia P1
# 2. Eliminada tolerancia de "2 lows cortados" en verificar_slope_4ps -> ahora 0 tolerancia
# 3. P2 nunca puede ser <= P1 (control adicional explicito)
# 4. Bloque despues de P2 (P2 dinamico, senal) queda intacto, ya estaba correcto
# Corre desde: /Users/noellazaro/SPY-ALERT-SERVER/

import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD_VERIFICAR = '''def verificar_slope_4ps(p1_low, p1_idx, p2_low_cand, p2_idx_cand, historial_lows):
    """
    Verifica que el slope P1->P2_candidato no corte mas de 2 lows intermedios.
    historial_lows: lista de (idx, low) de velas entre P1 y P2 candidato.
    Retorna True si es valido (0, 1 o 2 lows cortados).
    """
    if p2_idx_cand <= p1_idx:
        return False
    slope = (p2_low_cand - p1_low) / (p2_idx_cand - p1_idx)
    lows_cortados = 0
    for idx, low in historial_lows:
        if idx <= p1_idx or idx >= p2_idx_cand:
            continue
        proyeccion = p1_low + slope * (idx - p1_idx)
        if low < proyeccion:
            lows_cortados += 1
    return lows_cortados <= 2'''

NEW_VERIFICAR = '''def verificar_slope_4ps(p1_low, p1_idx, p2_low_cand, p2_idx_cand, historial_lows):
    """
    Verifica que el slope P1->P2_candidato no corte NINGUN low intermedio (0 tolerancia).
    historial_lows: lista de (idx, low) de velas entre P1 y P2 candidato.
    Tambien rechaza si P2 candidato es <= P1 (P2 siempre debe ser mayor que P1).
    Retorna True solo si es completamente valido (0 lows cortados).
    """
    if p2_idx_cand <= p1_idx:
        return False
    if p2_low_cand <= p1_low:
        return False
    slope = (p2_low_cand - p1_low) / (p2_idx_cand - p1_idx)
    for idx, low in historial_lows:
        if idx <= p1_idx or idx >= p2_idx_cand:
            continue
        proyeccion = p1_low + slope * (idx - p1_idx)
        if low < proyeccion:
            return False
    return True'''

if OLD_VERIFICAR not in content:
    errors.append("CAMBIO 1: funcion verificar_slope_4ps original no encontrada")
else:
    content = content.replace(OLD_VERIFICAR, NEW_VERIFICAR, 1)
    print("Cambio 1 OK: verificar_slope_4ps sin tolerancia + P2 nunca <= P1")

OLD_ANTES_P2 = '''        # P1 se mueve si aparece low menor (solo durante formacion — antes de tener P2)
        elif v_low <= ed["4ps_p1_low"] and ed["4ps_p2_idx"] is None:
            ed["4ps_p1_low"]         = v_low
            ed["4ps_p1_idx"]         = idx_4ps
            ed["4ps_p2_low"]         = None
            ed["4ps_p2_idx"]         = None
            ed["4ps_historial_lows"] = [(idx_4ps, v_low)]

        else:
            distancia_4ps = idx_4ps - ed["4ps_p1_idx"]
            historial_lows = ed.get("4ps_historial_lows", [])

            # ── Sin P2 aun: buscar primer candidato valido (min 6 velas desde P1) ──
            if ed["4ps_p2_idx"] is None and distancia_4ps >= 6:
                if verificar_slope_4ps(ed["4ps_p1_low"], ed["4ps_p1_idx"], v_low, idx_4ps, historial_lows):
                    ed["4ps_p2_low"] = v_low
                    ed["4ps_p2_idx"] = idx_4ps
                    print(f"{simbolo} 4PASOS P2 fijado: ${v_low:.2f} idx={idx_4ps}")'''

NEW_ANTES_P2 = '''        # P1 se mueve si aparece low menor o igual (solo durante formacion - antes de tener P2)
        elif v_low <= ed["4ps_p1_low"] and ed["4ps_p2_idx"] is None:
            ed["4ps_p1_low"]         = v_low
            ed["4ps_p1_idx"]         = idx_4ps
            ed["4ps_p2_low"]         = None
            ed["4ps_p2_idx"]         = None
            ed["4ps_historial_lows"] = [(idx_4ps, v_low)]

        elif ed["4ps_p2_idx"] is None:
            distancia_4ps = idx_4ps - ed["4ps_p1_idx"]
            historial_lows = ed.get("4ps_historial_lows", [])

            proyeccion_rota = False
            if distancia_4ps > 0:
                slope_proyectado = (v_low - ed["4ps_p1_low"]) / distancia_4ps
                for idx_h, low_h in historial_lows:
                    if idx_h <= ed["4ps_p1_idx"] or idx_h >= idx_4ps:
                        continue
                    proy = ed["4ps_p1_low"] + slope_proyectado * (idx_h - ed["4ps_p1_idx"])
                    if low_h < proy:
                        proyeccion_rota = True
                        break

            if proyeccion_rota:
                ed["4ps_p1_low"]         = v_low
                ed["4ps_p1_idx"]         = idx_4ps
                ed["4ps_p2_low"]         = None
                ed["4ps_p2_idx"]         = None
                ed["4ps_historial_lows"] = [(idx_4ps, v_low)]
                print(f"{simbolo} 4PASOS P1 reiniciado por ruptura de proyeccion: ${v_low:.2f} idx={idx_4ps}")
            elif distancia_4ps >= 6:
                if verificar_slope_4ps(ed["4ps_p1_low"], ed["4ps_p1_idx"], v_low, idx_4ps, historial_lows):
                    ed["4ps_p2_low"] = v_low
                    ed["4ps_p2_idx"] = idx_4ps
                    print(f"{simbolo} 4PASOS P2 fijado: ${v_low:.2f} idx={idx_4ps}")'''

if OLD_ANTES_P2 not in content:
    errors.append("CAMBIO 2: bloque V2-V7 antes de P2 no encontrado")
else:
    content = content.replace(OLD_ANTES_P2, NEW_ANTES_P2, 1)
    print("Cambio 2 OK: verificacion de ruptura de proyeccion antes de tener P2")

OLD_CON_P2_HEADER = '''            # ── Con P2: evaluar ruptura o actualizacion ──
            elif ed["4ps_p2_idx"] is not None:'''

NEW_CON_P2_HEADER = '''        # Con P2: evaluar ruptura o actualizacion
        elif ed["4ps_p2_idx"] is not None:'''

if OLD_CON_P2_HEADER not in content:
    errors.append("CAMBIO 3: header bloque Con P2 no encontrado")
else:
    content = content.replace(OLD_CON_P2_HEADER, NEW_CON_P2_HEADER, 1)
    print("Cambio 3 OK: indentacion corregida del bloque Con P2")

content = content.replace('AXIS Breakout Sentinel v8.77', 'AXIS Breakout Sentinel v8.78')
print("Cambio 4 OK: version v8.78")

if errors:
    print("ERRORES:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("server.py v8.78 guardado")
    print("git add server.py && git commit -m 'fix: 4PASOS P1/P2 con proyeccion y sin tolerancia v8.78' && git push origin main")
