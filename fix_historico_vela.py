import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD = 'def archivar_señales_dia(fecha):\n    historial = cargar_señales_historicas()\n    historial[fecha] = {}\n    for simbolo in ACTIVOS:\n        ed = estado_dia.get(simbolo, {})\n        if ed.get("fecha") == fecha:\n            disparadas = ed.get("señales_disparadas", [])\n            cortos = []\n            for s in disparadas:\n                if "1VR"    in s: cortos.append("1VR")\n                elif "RPG"  in s: cortos.append("RPG")\n                elif "GNA"  in s: cortos.append("GNA")\n                elif "GBA"  in s: cortos.append("GBA")\n                elif "HED"  in s: cortos.append("HED")\n                elif "PM40" in s: cortos.append("PM40")\n                elif "CNF"  in s: cortos.append("CNF")\n                elif "RCB"  in s: cortos.append("RCB")\n                elif "4PS"  in s or "4PASOS" in s: cortos.append("4PS")\n            historial[fecha][simbolo] = cortos\n        else:\n            historial[fecha][simbolo] = []\n    guardar_señales_historicas(historial)\n    print(f"Señales archivadas para {fecha}: {historial[fecha]}")'

NEW = 'def archivar_señales_dia(fecha):\n    """v8.84: ahora guarda tambien vela y hora exacta de cada senal (no solo\n    el tipo), usando señales_detalle que ya tiene esta info desde v8.81.\n    Mantiene compatibilidad: si una senal no tiene detalle (senales viejas\n    antes de v8.81), guarda solo el tipo sin vela/hora."""\n    historial = cargar_señales_historicas()\n    historial[fecha] = {}\n    for simbolo in ACTIVOS:\n        ed = estado_dia.get(simbolo, {})\n        if ed.get("fecha") == fecha:\n            detalle = ed.get("señales_detalle", [])\n            if detalle:\n                historial[fecha][simbolo] = [\n                    {"tipo": d["tipo"], "vela": d.get("vela"), "hora": d.get("hora")}\n                    for d in detalle\n                ]\n            else:\n                disparadas = ed.get("señales_disparadas", [])\n                cortos = []\n                for s in disparadas:\n                    if "1VR"    in s: cortos.append({"tipo": "1VR", "vela": None, "hora": None})\n                    elif "RPG"  in s: cortos.append({"tipo": "RPG", "vela": None, "hora": None})\n                    elif "GNA"  in s: cortos.append({"tipo": "GNA", "vela": None, "hora": None})\n                    elif "GBA"  in s: cortos.append({"tipo": "GBA", "vela": None, "hora": None})\n                    elif "HED"  in s: cortos.append({"tipo": "HED", "vela": None, "hora": None})\n                    elif "PM40" in s: cortos.append({"tipo": "PM40", "vela": None, "hora": None})\n                    elif "CNF"  in s: cortos.append({"tipo": "CNF", "vela": None, "hora": None})\n                    elif "RCB"  in s: cortos.append({"tipo": "RCB", "vela": None, "hora": None})\n                    elif "4PS"  in s or "4PASOS" in s: cortos.append({"tipo": "4PS", "vela": None, "hora": None})\n                historial[fecha][simbolo] = cortos\n        else:\n            historial[fecha][simbolo] = []\n    guardar_señales_historicas(historial)\n    print(f"Señales archivadas para {fecha}: {historial[fecha]}")'

if OLD not in content:
    errors.append("Funcion archivar_señales_dia original no encontrada")
else:
    content = content.replace(OLD, NEW, 1)
    print("Cambio OK: archivar_señales_dia ahora guarda vela y hora en el historico")

content = content.replace("AXIS Breakout Sentinel v8.83", "AXIS Breakout Sentinel v8.84")
print("Version v8.84")

if errors:
    print("ERRORES:")
    for e in errors:
        print("  - " + e)
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("server.py v8.84 guardado")
