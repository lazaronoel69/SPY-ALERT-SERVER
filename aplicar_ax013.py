import sys
import ast

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD1 = '        # Canal V1 — P2 dinamico especial: cualquier tipo de vela\n        # Si V1 rompe el techo (mecha o cuerpo, sin importar tipo de vela)\n        # y el high es menor que P1, se convierte directamente en nuevo P2.\n        # Esto aplica SOLO a V1 — V2-V7 usan su propia logica mas abajo.\n        if c["on"] and not c["apagado"] and c.get("p1") and c.get("p2_actual_high") is not None:\n            ahora_dt_v1c = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))\n            techo_v1c = calcular_techo_canal(simbolo, ahora_dt_v1c)\n            if techo_v1c and v_high > techo_v1c and v_high < c["p1"]["high"]:\n                p2_ant_v1c = c["p2_actual_high"]\n                c["p2_actual_high"] = v_high\n                c["p2"]["high"]     = v_high\n                c["p2"]["fecha"]    = ahora_dt_v1c.strftime("%Y-%m-%d")\n                c["p2"]["hora_est"] = ahora_dt_v1c.hour\n                c["p2_actual_ts"]   = ahora_dt_v1c\n                guardar_canales()\n                print(f"{simbolo} P2 dinamico (V1): ${p2_ant_v1c:.2f} -> ${v_high:.2f} ({ahora_dt_v1c.strftime(\'%Y-%m-%d\')}) silencioso")\n'

NEW1 = '        # Canal V1\n        evaluar_canal_v1(simbolo, c, vela_actual, v_high)\n'

if content.count(OLD1) != 1:
    errors.append(f'BLOQUE CANAL V1: se esperaba 1 coincidencia, se encontraron {content.count(OLD1)}')
    print('ERRORES:'); [print('  - ' + e) for e in errors]; sys.exit(1)

MARKER = 'def evaluar_activo(simbolo, velas, ahora):'

if content.count(MARKER) != 1:
    errors.append(f'MARKER: se esperaba 1 coincidencia, se encontraron {content.count(MARKER)}')
    print('ERRORES:'); [print('  - ' + e) for e in errors]; sys.exit(1)

FUNC_DEF = 'def evaluar_canal_v1(simbolo, c, vela_actual, v_high):\n    """AX-013: extraida de evaluar_activo() sin cambiar comportamiento.\n    Contiene EXACTAMENTE el bloque de Canal V1 -- P2 dinamico especial\n    (cualquier tipo de vela, aplica SOLO a V1). NO toca PM40, 4PASOS,\n    Canal V2-V7, RPG/GNA/GBA/1VR, ni Reset Diario.\n    Recibe explicitamente todas las variables necesarias."""\n    # Canal V1 — P2 dinamico especial: cualquier tipo de vela\n    # Si V1 rompe el techo (mecha o cuerpo, sin importar tipo de vela)\n    # y el high es menor que P1, se convierte directamente en nuevo P2.\n    # Esto aplica SOLO a V1 — V2-V7 usan su propia logica mas abajo.\n    if c["on"] and not c["apagado"] and c.get("p1") and c.get("p2_actual_high") is not None:\n        ahora_dt_v1c = EST.localize(datetime.strptime(vela_actual["datetime"], "%Y-%m-%d %H:%M:%S"))\n        techo_v1c = calcular_techo_canal(simbolo, ahora_dt_v1c)\n        if techo_v1c and v_high > techo_v1c and v_high < c["p1"]["high"]:\n            p2_ant_v1c = c["p2_actual_high"]\n            c["p2_actual_high"] = v_high\n            c["p2"]["high"]     = v_high\n            c["p2"]["fecha"]    = ahora_dt_v1c.strftime("%Y-%m-%d")\n            c["p2"]["hora_est"] = ahora_dt_v1c.hour\n            c["p2_actual_ts"]   = ahora_dt_v1c\n            guardar_canales()\n            print(f"{simbolo} P2 dinamico (V1): ${p2_ant_v1c:.2f} -> ${v_high:.2f} ({ahora_dt_v1c.strftime(\'%Y-%m-%d\')}) silencioso")\n\n'

nuevo_contenido = content.replace(OLD1, NEW1, 1)
nuevo_contenido = nuevo_contenido.replace(MARKER, FUNC_DEF + MARKER, 1)

try:
    ast.parse(nuevo_contenido)
    print('AST valido -- el resultado parsea correctamente')
except SyntaxError as e:
    print(f'ERROR: el resultado NO parsea -- {e}')
    print('NO SE ESCRIBIO NADA -- server.py permanece sin cambios')
    sys.exit(1)

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(nuevo_contenido)
print('server.py actualizado -- evaluar_canal_v1() extraida correctamente')
