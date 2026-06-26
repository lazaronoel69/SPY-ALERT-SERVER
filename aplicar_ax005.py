import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

# BLOQUE 1 -- cargar_señales_historicas, guardar_señales_historicas
OLD1 = 'def cargar_señales_historicas():\n    if not os.path.exists(SEÑALES_FILE):\n        return {}\n    try:\n        with open(SEÑALES_FILE, "r") as f:\n            return json.load(f)\n    except Exception as e:\n        print(f"Error cargando señales históricas: {e}")\n        return {}\n\ndef guardar_señales_historicas(data):\n    try:\n        with open(SEÑALES_FILE, "w") as f:\n            json.dump(data, f, indent=2)\n    except Exception as e:\n        print(f"Error guardando señales históricas: {e}")'

NEW1 = '# AX-005: cargar_señales_historicas, guardar_señales_historicas movidas a axis_storage.py\nfrom axis_storage import cargar_señales_historicas, guardar_señales_historicas'

if content.count(OLD1) != 1:
    errors.append(f'BLOQUE 1: se esperaba 1 coincidencia, se encontraron {content.count(OLD1)}')
else:
    content = content.replace(OLD1, NEW1, 1)
    print('Bloque 1 OK: cargar/guardar_señales_historicas -> axis_storage.py')

# BLOQUE 2 -- guardar_estado_dia (con wrapper)
OLD2 = 'def guardar_estado_dia():\n    try:\n        with open(ESTADO_FILE, "w") as f:\n            json.dump(estado_dia, f, indent=2)\n    except Exception as e:\n        print(f"Error guardando estado_dia: {e}")'

NEW2 = '# AX-005: logica movida a axis_storage.py (acepta estado_dia como parametro\n# en vez de leerlo como global). Wrapper mantiene el nombre y firma original\n# sin argumentos para no romper ninguna llamada existente en server.py.\nfrom axis_storage import guardar_estado_dia as _guardar_estado_dia_storage\n\ndef guardar_estado_dia():\n    _guardar_estado_dia_storage(estado_dia)'

if content.count(OLD2) != 1:
    errors.append(f'BLOQUE 2: se esperaba 1 coincidencia, se encontraron {content.count(OLD2)}')
else:
    content = content.replace(OLD2, NEW2, 1)
    print('Bloque 2 OK: guardar_estado_dia -> axis_storage.py (con wrapper en server.py)')

# BLOQUE 3 -- ruta_velas_local, cargar_velas_local, guardar_velas_local
OLD3 = 'def ruta_velas_local(simbolo):\n    return f"{DATA_DIR}/axis_velas_{simbolo}.json"\n\ndef cargar_velas_local(simbolo):\n    ruta = ruta_velas_local(simbolo)\n    if not os.path.exists(ruta):\n        return {"simbolo": simbolo, "ultima_barra": None, "barras": []}\n    try:\n        with open(ruta) as f:\n            return json.load(f)\n    except Exception as e:\n        print(f"Error cargando velas locales {simbolo}: {e}")\n        return {"simbolo": simbolo, "ultima_barra": None, "barras": []}\n\ndef guardar_velas_local(simbolo, data):\n    try:\n        with open(ruta_velas_local(simbolo), "w") as f:\n            json.dump(data, f)\n    except Exception as e:\n        print(f"Error guardando velas locales {simbolo}: {e}")'

NEW3 = '# AX-005: ruta_velas_local, cargar_velas_local, guardar_velas_local movidas\n# a axis_storage.py. Mismos nombres, mismo comportamiento, mismo formato JSON.\nfrom axis_storage import ruta_velas_local, cargar_velas_local, guardar_velas_local'

if content.count(OLD3) != 1:
    errors.append(f'BLOQUE 3: se esperaba 1 coincidencia, se encontraron {content.count(OLD3)}')
else:
    content = content.replace(OLD3, NEW3, 1)
    print('Bloque 3 OK: ruta/cargar/guardar_velas_local -> axis_storage.py')

if errors:
    print('ERRORES:')
    for e in errors:
        print('  - ' + e)
    sys.exit(1)
else:
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('server.py actualizado -- funciones de storage ahora en axis_storage.py')
