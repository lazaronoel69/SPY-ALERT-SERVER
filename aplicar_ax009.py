import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

# BLOQUE 1 -- canal_vacio
OLD1 = 'def canal_vacio():\n    return {\n        "on":             False,\n        "p1":             None,\n        "p2":             None,\n        "p3":             None,\n        "p2_actual_high": None,\n        "p2_actual_ts":   None,\n        "v1_candidato":   None,\n        "apagado":        False,\n        "roto":           False,\n        "fecha_ruptura":  None,\n    }'

NEW1 = '# AX-009: canal_vacio movida a axis_channels.py.\nfrom axis_channels import canal_vacio'

if content.count(OLD1) != 1:
    errors.append(f'BLOQUE 1: se esperaba 1 coincidencia, se encontraron {content.count(OLD1)}')
else:
    content = content.replace(OLD1, NEW1, 1)
    print('Bloque 1 OK: canal_vacio -> axis_channels.py')

# BLOQUE 2 -- CANALES_DEFAULT, guardar_canales, cargar_canales
OLD2 = 'CANALES_DEFAULT = {\n    "SPY":  {"on": False, "apagado": False, "p1": None, "p2": None, "p3": None,\n             "p2_actual_high": None, "p2_actual_ts": None, "v1_candidato": None},\n    "GLD":  {\n        "on": True, "apagado": False, "v1_candidato": None,\n        "p1": {"fecha": "2026-04-17", "hora_est": 10, "high": 448.70},\n        "p2": {"fecha": "2026-05-07", "hora_est": 11, "high": 437.42},\n        "p2_actual_high": 437.42,\n        "p2_actual_ts": "2026-05-07T11:00:00",\n        "p3": {"fecha": "2026-04-29", "hora_est": 9, "low": 415.27},\n    },\n    "AAPL": {"on": False, "apagado": False, "p1": None, "p2": None, "p3": None,\n             "p2_actual_high": None, "p2_actual_ts": None, "v1_candidato": None},\n    "BA":   {"on": False, "apagado": False, "p1": None, "p2": None, "p3": None,\n             "p2_actual_high": None, "p2_actual_ts": None, "v1_candidato": None},\n    "NVDA": {"on": False, "apagado": False, "p1": None, "p2": None, "p3": None,\n             "p2_actual_high": None, "p2_actual_ts": None, "v1_candidato": None},\n    "AMZN": {"on": False, "apagado": False, "p1": None, "p2": None, "p3": None,\n             "p2_actual_high": None, "p2_actual_ts": None, "v1_candidato": None},\n    "GOOG": {"on": False, "apagado": False, "p1": None, "p2": None, "p3": None,\n             "p2_actual_high": None, "p2_actual_ts": None, "v1_candidato": None},\n    "META": {"on": False, "apagado": False, "p1": None, "p2": None, "p3": None,\n             "p2_actual_high": None, "p2_actual_ts": None, "v1_candidato": None},\n}\n\ndef guardar_canales():\n    try:\n        data = {}\n        for a in ACTIVOS:\n            c = canal[a]\n            ts = c["p2_actual_ts"]\n            data[a] = {\n                "on":             c["on"],\n                "apagado":        c["apagado"],\n                "roto":           c.get("roto", False),\n                "fecha_ruptura":  c.get("fecha_ruptura", None),\n                "p1":             c["p1"],\n                "p2":             c["p2"],\n                "p3":             c["p3"],\n                "p2_actual_high": c["p2_actual_high"],\n                "p2_actual_ts":   ts.isoformat() if hasattr(ts, \'isoformat\') else ts,\n                "v1_candidato":   None,\n            }\n        with open(CANALES_FILE, \'w\') as f:\n            json.dump(data, f, indent=2)\n        print(f"Canales guardados → {CANALES_FILE}")\n    except Exception as e:\n        print(f"Error guardando canales: {e}")\n\ndef cargar_canales():\n    try:\n        if os.path.exists(CANALES_FILE):\n            with open(CANALES_FILE, \'r\') as f:\n                data = json.load(f)\n            print(f"Canales cargados desde {CANALES_FILE}")\n        else:\n            data = CANALES_DEFAULT\n            print("Primer arranque — cargando canales por defecto (SPY CNF + GLD RCB)")\n        for a in ACTIVOS:\n            if a not in data:\n                continue\n            d = data[a]\n            canal[a]["on"]             = d.get("on", False)\n            canal[a]["apagado"]        = d.get("apagado", False)\n            canal[a]["roto"]           = d.get("roto", False)\n            canal[a]["fecha_ruptura"]  = d.get("fecha_ruptura", None)\n            canal[a]["p1"]             = d.get("p1")\n            canal[a]["p2"]             = d.get("p2")\n            canal[a]["p3"]             = d.get("p3")\n            canal[a]["p2_actual_high"] = d.get("p2_actual_high")\n            ts_str = d.get("p2_actual_ts")\n            if ts_str and isinstance(ts_str, str):\n                try:\n                    from datetime import datetime as _dt\n                    canal[a]["p2_actual_ts"] = EST.localize(_dt.fromisoformat(ts_str))\n                except:\n                    canal[a]["p2_actual_ts"] = None\n            canal[a]["v1_candidato"] = None\n        for a in ACTIVOS:\n            if canal[a]["on"]:\n                tipo = "RCB" if canal[a]["p3"] else "CNF"\n                p1h  = canal[a]["p1"]["high"] if canal[a]["p1"] else "?"\n                print(f"  {a}: {tipo} activo — P1={p1h}")\n    except Exception as e:\n        print(f"Error cargando canales: {e}")'

NEW2 = '# AX-009: CANALES_DEFAULT, guardar_canales y cargar_canales movidas a\n# axis_channels.py. guardar_canales/cargar_canales reciben canal y ACTIVOS\n# como parametros (modifican canal in-place). Wrappers mantienen los\n# nombres y firmas originales sin argumentos para no romper ninguna\n# llamada existente en server.py.\nfrom axis_channels import CANALES_DEFAULT\nimport axis_channels as _axis_channels\n\ndef guardar_canales():\n    _axis_channels.guardar_canales(canal, ACTIVOS, CANALES_FILE)\n\ndef cargar_canales():\n    _axis_channels.cargar_canales(canal, ACTIVOS, CANALES_FILE, EST)'

if content.count(OLD2) != 1:
    errors.append(f'BLOQUE 2: se esperaba 1 coincidencia, se encontraron {content.count(OLD2)}')
else:
    content = content.replace(OLD2, NEW2, 1)
    print('Bloque 2 OK: CANALES_DEFAULT/guardar_canales/cargar_canales -> axis_channels.py')

if errors:
    print('ERRORES:')
    for e in errors:
        print('  - ' + e)
    sys.exit(1)
else:
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('server.py actualizado -- canales basicos ahora wrappers de axis_channels.py')
