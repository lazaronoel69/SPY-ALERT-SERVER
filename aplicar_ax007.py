import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD1 = 'def guardar_ordenes():\n    """Persiste ordenes_pendientes en /data para sobrevivir reinicios."""\n    try:\n        data = {}\n        for oid, d in ordenes_pendientes.items():\n            data[oid] = {\n                "opcion":         d["opcion"],\n                "estrategia":     d.get("estrategia", "AXIS"),\n                "ts":             d["ts"].isoformat() if hasattr(d["ts"], "isoformat") else str(d["ts"]),\n                "message_id":     d["message_id"],\n                "chat_id":        d["chat_id"],\n                "texto_original": d.get("texto_original", ""),\n            }\n        with open(ORDENES_FILE, "w") as f:\n            json.dump(data, f, indent=2)\n    except Exception as e:\n        print(f"Error guardando ordenes: {e}")\n\ndef cargar_ordenes():\n    """Carga ordenes_pendientes desde /data al arrancar."""\n    global ordenes_pendientes\n    try:\n        if not os.path.exists(ORDENES_FILE):\n            return\n        with open(ORDENES_FILE, "r") as f:\n            data = json.load(f)\n        ahora = datetime.now(pytz.utc)\n        recuperadas = 0\n        for oid, d in data.items():\n            try:\n                ts = datetime.fromisoformat(d["ts"])\n                if ts.tzinfo is None:\n                    ts = pytz.utc.localize(ts)\n                # Descartar órdenes ya expiradas\n                if (ahora - ts).total_seconds() > ORDEN_TIMEOUT_MIN * 60:\n                    continue\n                ordenes_pendientes[oid] = {\n                    "opcion":         d["opcion"],\n                    "estrategia":     d.get("estrategia", "AXIS"),\n                    "ts":             ts,\n                    "message_id":     d["message_id"],\n                    "chat_id":        d["chat_id"],\n                    "texto_original": d.get("texto_original", ""),\n                }\n                recuperadas += 1\n            except Exception as e:\n                print(f"Error recuperando orden {oid}: {e}")\n        if recuperadas:\n            print(f"Ordenes pendientes recuperadas: {recuperadas}")\n        # Limpiar archivo dejando solo las vigentes\n        guardar_ordenes()\n    except Exception as e:\n        print(f"Error cargando ordenes: {e}")'

NEW1 = '# AX-007: logica movida a axis_orders.py (recibe ordenes_pendientes como\n# parametro en vez de leerlo/escribirlo como global propio del modulo).\n# Wrappers mantienen los nombres y firmas originales sin argumentos para\n# no romper ninguna llamada existente en server.py.\nimport axis_orders as _axis_orders\n\ndef guardar_ordenes():\n    _axis_orders.guardar_ordenes(ordenes_pendientes)\n\ndef cargar_ordenes():\n    _axis_orders.cargar_ordenes(ordenes_pendientes)'

if content.count(OLD1) != 1:
    errors.append(f'Se esperaba 1 coincidencia, se encontraron {content.count(OLD1)}')
else:
    content = content.replace(OLD1, NEW1, 1)
    print('Cambio OK: guardar_ordenes/cargar_ordenes -> axis_orders.py (con wrappers)')

if errors:
    print('ERRORES:')
    for e in errors:
        print('  - ' + e)
    sys.exit(1)
else:
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('server.py actualizado -- guardar_ordenes/cargar_ordenes ahora wrappers de axis_orders.py')
