import sys
import ast

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD1 = '        # ── 1VR — Primera Vela Roja ──\n        if VR1_ON and v_roja and not ed["vr1_fired"]:\n            ahora_dt_vr = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))\n            techo_vr    = calcular_techo_canal(simbolo, ahora_dt_vr)\n            _, mitad_vr = calcular_piso_mitad_canal(simbolo, ahora_dt_vr)\n            c_vr        = canal[simbolo]\n            sma20_vr    = calcular_sma(velas, 20)\n            sma40_vr    = calcular_sma(velas, 40)\n\n            zona_30 = None\n            if techo_vr and mitad_vr:\n                zona_30 = techo_vr - (techo_vr - mitad_vr) * 0.30\n            en_rcb_30 = (\n                c_vr["on"] and not c_vr["apagado"] and c_vr["p3"] is not None\n                and techo_vr is not None and zona_30 is not None\n                and zona_30 <= v_close <= techo_vr\n            )\n\n            sma40_gt_sma20 = sma40_vr and sma20_vr and sma40_vr > sma20_vr\n\n            # 1VR dispara siempre que V1 cierre roja\n            # Condición adicional solo cambia el label (1VR vs 1VR+)\n            ed["vr1_fired"] = True\n            guardar_estado_dia()\n            label_vr = "1VR+" if en_rcb_30 else "1VR"\n            if en_rcb_30:\n                extra_vr = f"<b>Canal RCB:</b> Techo ${techo_vr:.2f} | Zona 30%: ${zona_30:.2f}\\n"\n            elif sma40_gt_sma20:\n                extra_vr = f"<b>SMA40:</b> ${sma40_vr:.2f} > <b>SMA20:</b> ${sma20_vr:.2f}\\n"\n            else:\n                extra_vr = ""\n            enviar_senal_con_botones(\n                simbolo, f"{label_vr} — PRIMERA VELA ROJA",\n                "10:00 EST", v_close, "PUT",\n                f"<b>Open:</b> ${v_open:.2f} | <b>Close:</b> ${v_close:.2f}\\n{extra_vr}"\n            )\n'

NEW1 = '        # 1VR\n        evaluar_1vr_normal(simbolo, ed, velas, vela_actual, v_open, v_close, v_roja)\n'

if content.count(OLD1) != 1:
    errors.append(f'BLOQUE 1VR: se esperaba 1 coincidencia, se encontraron {content.count(OLD1)}')
    print('ERRORES:'); [print('  - ' + e) for e in errors]; sys.exit(1)

MARKER = 'def evaluar_activo(simbolo, velas, ahora):'

if content.count(MARKER) != 1:
    errors.append(f'MARKER: se esperaba 1 coincidencia, se encontraron {content.count(MARKER)}')
    print('ERRORES:'); [print('  - ' + e) for e in errors]; sys.exit(1)

FUNC_DEF = 'def evaluar_1vr_normal(simbolo, ed, velas, vela_actual, v_open, v_close, v_roja):\n    """AX-012G: extraida de evaluar_activo() sin cambiar comportamiento.\n    Contiene EXACTAMENTE el bloque de 1VR en la rama V1 normal (no la\n    reconstruccion del reset diario, que permanece intacta dentro de\n    reset_diario_si_aplica() segun regla explicita de este sprint).\n    Recibe explicitamente todas las variables necesarias."""\n    # ── 1VR — Primera Vela Roja ──\n    if VR1_ON and v_roja and not ed["vr1_fired"]:\n        ahora_dt_vr = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))\n        techo_vr    = calcular_techo_canal(simbolo, ahora_dt_vr)\n        _, mitad_vr = calcular_piso_mitad_canal(simbolo, ahora_dt_vr)\n        c_vr        = canal[simbolo]\n        sma20_vr    = calcular_sma(velas, 20)\n        sma40_vr    = calcular_sma(velas, 40)\n\n        zona_30 = None\n        if techo_vr and mitad_vr:\n            zona_30 = techo_vr - (techo_vr - mitad_vr) * 0.30\n        en_rcb_30 = (\n            c_vr["on"] and not c_vr["apagado"] and c_vr["p3"] is not None\n            and techo_vr is not None and zona_30 is not None\n            and zona_30 <= v_close <= techo_vr\n        )\n\n        sma40_gt_sma20 = sma40_vr and sma20_vr and sma40_vr > sma20_vr\n\n        # 1VR dispara siempre que V1 cierre roja\n        # Condición adicional solo cambia el label (1VR vs 1VR+)\n        ed["vr1_fired"] = True\n        guardar_estado_dia()\n        label_vr = "1VR+" if en_rcb_30 else "1VR"\n        if en_rcb_30:\n            extra_vr = f"<b>Canal RCB:</b> Techo ${techo_vr:.2f} | Zona 30%: ${zona_30:.2f}\\n"\n        elif sma40_gt_sma20:\n            extra_vr = f"<b>SMA40:</b> ${sma40_vr:.2f} > <b>SMA20:</b> ${sma20_vr:.2f}\\n"\n        else:\n            extra_vr = ""\n        enviar_senal_con_botones(\n            simbolo, f"{label_vr} — PRIMERA VELA ROJA",\n            "10:00 EST", v_close, "PUT",\n            f"<b>Open:</b> ${v_open:.2f} | <b>Close:</b> ${v_close:.2f}\\n{extra_vr}"\n        )\n\n'

# Aplicar ambos cambios sobre una copia en memoria (patron AX-012F)
# evaluar_1vr_normal() se inserta justo antes de evaluar_activo(), que es
# exactamente 'inmediatamente despues de reset_diario_si_aplica()' porque
# esa funcion ya fue insertada ahi mismo en AX-012F.
nuevo_contenido = content.replace(OLD1, NEW1, 1)
nuevo_contenido = nuevo_contenido.replace(MARKER, FUNC_DEF + MARKER, 1)

# Verificar que el resultado es Python valido ANTES de escribir nada
try:
    ast.parse(nuevo_contenido)
    print('AST valido -- el resultado parsea correctamente')
except SyntaxError as e:
    print(f'ERROR: el resultado NO parsea -- {e}')
    print('NO SE ESCRIBIO NADA -- server.py permanece sin cambios')
    sys.exit(1)

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(nuevo_contenido)
print('server.py actualizado -- evaluar_1vr_normal() extraida correctamente')
