import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD1 = 'DERBY_CABALLOS = [\n    {"id": 1, "nombre": "Noel"},\n    {"id": 2, "nombre": "Paula"},\n    {"id": 3, "nombre": "Noel Andres"},\n    {"id": 4, "nombre": "Emilia"},\n]\n\ndef portfolio_vacio():\n    return {\n        "posiciones":  [],\n        "historial":   [],\n        "derby": {\n            "nombre":          "REAL LAZARO-PALMA",\n            "activo":          False,\n            "turno_actual":    1,\n            "ganador":         None,\n            "esperando_cierre": False,\n            "caballos": [\n                {\n                    "id":              c["id"],\n                    "nombre":          c["nombre"],\n                    "capital":         0,\n                    "capital_inicial": 0,\n                    "ronda":           0,\n                    "posicion":        None,\n                    "eliminado":       False,\n                    "historial":       []\n                }\n                for c in DERBY_CABALLOS\n            ]\n        }\n    }\n\n_portfolio = None\n\ndef cargar_portfolio():\n    global _portfolio\n    try:\n        if os.path.exists(PORTFOLIO_FILE):\n            with open(PORTFOLIO_FILE, \'r\') as f:\n                _portfolio = json.load(f)\n            # Migrar reto→derby si viene de versión anterior\n            if "reto" in _portfolio and "derby" not in _portfolio:\n                vacio = portfolio_vacio()\n                _portfolio["derby"] = vacio["derby"]\n                print("Migración: reto→derby completada")\n                guardar_portfolio()\n            elif "derby" not in _portfolio:\n                vacio = portfolio_vacio()\n                _portfolio["derby"] = vacio["derby"]\n                guardar_portfolio()\n            print(f"Portfolio cargado — {len(_portfolio[\'posiciones\'])} posiciones abiertas")\n        else:\n            _portfolio = portfolio_vacio()\n            guardar_portfolio()\n            print("Portfolio nuevo creado")\n    except Exception as e:\n        print(f"Error cargando portfolio: {e}")\n        _portfolio = portfolio_vacio()\n\ndef guardar_portfolio():\n    try:\n        with open(PORTFOLIO_FILE, \'w\') as f:\n            json.dump(_portfolio, f, indent=2, default=str)\n    except Exception as e:\n        print(f"Error guardando portfolio: {e}")'

NEW1 = '# AX-008: DERBY_CABALLOS, portfolio_vacio, cargar_portfolio y\n# guardar_portfolio movidas a axis_portfolio.py. cargar_portfolio/\n# guardar_portfolio ahora reciben/devuelven datos en vez de depender\n# del global _portfolio. Wrappers mantienen los nombres y firmas\n# originales sin argumentos, preservando el mismo efecto observable\n# (incluyendo el guardado automatico en los 3 casos de migracion).\nfrom axis_portfolio import DERBY_CABALLOS, portfolio_vacio\nimport axis_portfolio as _axis_portfolio\n\n_portfolio = None\n\ndef cargar_portfolio():\n    global _portfolio\n    _portfolio, _debe_guardar = _axis_portfolio.cargar_portfolio()\n    if _debe_guardar:\n        guardar_portfolio()\n\ndef guardar_portfolio():\n    _axis_portfolio.guardar_portfolio(_portfolio)'

if content.count(OLD1) != 1:
    errors.append(f'Se esperaba 1 coincidencia, se encontraron {content.count(OLD1)}')
else:
    content = content.replace(OLD1, NEW1, 1)
    print('Cambio OK: DERBY_CABALLOS/portfolio_vacio/cargar_portfolio/guardar_portfolio -> axis_portfolio.py')

if errors:
    print('ERRORES:')
    for e in errors:
        print('  - ' + e)
    sys.exit(1)
else:
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('server.py actualizado -- portfolio basico ahora wrappers de axis_portfolio.py')
