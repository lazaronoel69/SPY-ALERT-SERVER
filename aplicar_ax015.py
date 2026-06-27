import sys
import ast

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD1 = '        # PM40 — P1 dinámico en V1\n        if not c["on"] and not ed["pm40_fired"]:\n            sma20  = calcular_sma(velas, 20)\n            sma40  = calcular_sma(velas, 40)\n            sma100 = calcular_sma(velas, 100)\n            sma200 = calcular_sma(velas, 200)\n            smas_ok = sma20 and sma40 and sma100 and sma200 and sma20 > sma40 > sma100 > sma200\n            ed["pm40_vela_idx"] = 1\n            if smas_ok:\n                if not ed["pm40_activo"]:\n                    ed["pm40_activo"]         = True\n                    ed["pm40_p1_high"]        = v_high\n                    ed["pm40_p1_idx"]         = 1\n                    ed["pm40_p2_high"]        = None\n                    ed["pm40_p2_idx"]         = None\n                    ed["pm40_velas_bajo_p1"]  = 0\n                    ed["pm40_p1_maduro"]      = False\n                elif v_high >= ed["pm40_p1_high"]:\n                    ed["pm40_p1_high"]        = v_high\n                    ed["pm40_p1_idx"]         = 1\n                    ed["pm40_p2_high"]        = None\n                    ed["pm40_p2_idx"]         = None\n                    ed["pm40_velas_bajo_p1"]  = 0\n                    ed["pm40_p1_maduro"]      = False\n                else:\n                    ed["pm40_velas_bajo_p1"] += 1\n                    if ed["pm40_velas_bajo_p1"] >= 3:\n                        ed["pm40_p1_maduro"] = True\n                    if ed["pm40_p2_high"] is not None and v_high > ed["pm40_p2_high"]:\n                        ed["pm40_p2_high"] = v_high\n                        ed["pm40_p2_idx"]  = ed["pm40_vela_idx"]\n                        canal[simbolo]["p2"]["high"]      = v_high\n                        canal[simbolo]["p2_actual_high"]  = v_high\n                        if ed["pm40_p2_high"] >= ed["pm40_p1_high"]:\n                            ed["pm40_activo"] = False; ed["pm40_p1_high"] = None\n                            ed["pm40_p1_idx"] = None; ed["pm40_p2_high"] = None\n                            ed["pm40_p2_idx"] = None; ed["pm40_velas_bajo_p1"] = 0\n                            ed["pm40_p1_maduro"] = False; canal[simbolo]["on"] = False\n                            guardar_canales()\n                        else:\n                            guardar_canales()\n'

NEW1 = '        # PM40\n        evaluar_pm40_v1(simbolo, ed, c, velas, v_high)\n'

if content.count(OLD1) != 1:
    errors.append(f'BLOQUE PM40 V1: se esperaba 1 coincidencia, se encontraron {content.count(OLD1)}')
    print('ERRORES:'); [print('  - ' + e) for e in errors]; sys.exit(1)

MARKER = 'def evaluar_activo(simbolo, velas, ahora):'

if content.count(MARKER) != 1:
    errors.append(f'MARKER: se esperaba 1 coincidencia, se encontraron {content.count(MARKER)}')
    print('ERRORES:'); [print('  - ' + e) for e in errors]; sys.exit(1)

FUNC_DEF = 'def evaluar_pm40_v1(simbolo, ed, c, velas, v_high):\n    """AX-015: extraida de evaluar_activo() sin cambiar comportamiento.\n    Contiene EXACTAMENTE el bloque de PM40 en la rama V1 (P1 dinamico:\n    inicializacion, actualizacion de P1 si rompe, maduracion tras 3 velas\n    bajo P1, y fijacion/actualizacion de P2 con invalidacion si P2>=P1).\n    NO toca PM40 V2-V7, 4PASOS, Canal V2-V7, 1VR/RPG/GNA/GBA, ni Reset Diario.\n    Recibe explicitamente todas las variables necesarias."""\n    # PM40 — P1 dinámico en V1\n    if not c["on"] and not ed["pm40_fired"]:\n        sma20  = calcular_sma(velas, 20)\n        sma40  = calcular_sma(velas, 40)\n        sma100 = calcular_sma(velas, 100)\n        sma200 = calcular_sma(velas, 200)\n        smas_ok = sma20 and sma40 and sma100 and sma200 and sma20 > sma40 > sma100 > sma200\n        ed["pm40_vela_idx"] = 1\n        if smas_ok:\n            if not ed["pm40_activo"]:\n                ed["pm40_activo"]         = True\n                ed["pm40_p1_high"]        = v_high\n                ed["pm40_p1_idx"]         = 1\n                ed["pm40_p2_high"]        = None\n                ed["pm40_p2_idx"]         = None\n                ed["pm40_velas_bajo_p1"]  = 0\n                ed["pm40_p1_maduro"]      = False\n            elif v_high >= ed["pm40_p1_high"]:\n                ed["pm40_p1_high"]        = v_high\n                ed["pm40_p1_idx"]         = 1\n                ed["pm40_p2_high"]        = None\n                ed["pm40_p2_idx"]         = None\n                ed["pm40_velas_bajo_p1"]  = 0\n                ed["pm40_p1_maduro"]      = False\n            else:\n                ed["pm40_velas_bajo_p1"] += 1\n                if ed["pm40_velas_bajo_p1"] >= 3:\n                    ed["pm40_p1_maduro"] = True\n                if ed["pm40_p2_high"] is not None and v_high > ed["pm40_p2_high"]:\n                    ed["pm40_p2_high"] = v_high\n                    ed["pm40_p2_idx"]  = ed["pm40_vela_idx"]\n                    canal[simbolo]["p2"]["high"]      = v_high\n                    canal[simbolo]["p2_actual_high"]  = v_high\n                    if ed["pm40_p2_high"] >= ed["pm40_p1_high"]:\n                        ed["pm40_activo"] = False; ed["pm40_p1_high"] = None\n                        ed["pm40_p1_idx"] = None; ed["pm40_p2_high"] = None\n                        ed["pm40_p2_idx"] = None; ed["pm40_velas_bajo_p1"] = 0\n                        ed["pm40_p1_maduro"] = False; canal[simbolo]["on"] = False\n                        guardar_canales()\n                    else:\n                        guardar_canales()\n\n'

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
print('server.py actualizado -- evaluar_pm40_v1() extraida correctamente')
