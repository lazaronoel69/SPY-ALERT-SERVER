import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD_REGISTRAR = """def registrar_senal_disparada(simbolo, estrategia):
    ed = estado_dia.get(simbolo)
    if ed is None:
        return
    if "señales_disparadas" not in ed:
        ed["señales_disparadas"] = []
    if estrategia not in ed["señales_disparadas"]:
        ed["señales_disparadas"].append(estrategia)
    s = estrategia.upper()
    if "1VR"    in s: ed["vr1_fired"]  = True
    if "RPG"    in s: ed["rpg_fired"]  = True
    if "GNA"    in s: ed["gna_fired"]  = True
    if "GBA"    in s: ed["gba_fired"]  = True
    if "PM40"   in s: ed["pm40_fired"] = True
    if "4PS"    in s or "4PASOS" in s: ed["4ps_fired"] = True
    if "HED"    in s: ed["hed_fired"]  = True
    if "CNF"    in s: ed["cnf_fired"]  = True
    if "RCB"    in s: ed["rcb_fired"]  = True
    guardar_estado_dia()"""

NEW_REGISTRAR = """def registrar_senal_disparada(simbolo, estrategia, hora_label=None):
    ed = estado_dia.get(simbolo)
    if ed is None:
        return
    if "señales_disparadas" not in ed:
        ed["señales_disparadas"] = []
    if estrategia not in ed["señales_disparadas"]:
        ed["señales_disparadas"].append(estrategia)
    if "señales_detalle" not in ed:
        ed["señales_detalle"] = []
    s = estrategia.upper()
    tipo_corto = None
    if "1VR"    in s: ed["vr1_fired"]  = True; tipo_corto = "1VR"
    if "RPG"    in s: ed["rpg_fired"]  = True; tipo_corto = "RPG"
    if "GNA"    in s: ed["gna_fired"]  = True; tipo_corto = "GNA"
    if "GBA"    in s: ed["gba_fired"]  = True; tipo_corto = "GBA"
    if "PM40"   in s: ed["pm40_fired"] = True; tipo_corto = "PM40"
    if "4PS"    in s or "4PASOS" in s: ed["4ps_fired"] = True; tipo_corto = "4PS"
    if "HED"    in s: ed["hed_fired"]  = True; tipo_corto = "HED"
    if "CNF"    in s: ed["cnf_fired"]  = True; tipo_corto = "CNF"
    if "RCB"    in s: ed["rcb_fired"]  = True; tipo_corto = "RCB"
    if tipo_corto and hora_label:
        try:
            hora_num = int(hora_label.split(":")[0])
            mapa_vela = {10:"V1",11:"V2",12:"V3",13:"V4",14:"V5",15:"V6",16:"V7"}
            vela_calc = mapa_vela.get(hora_num)
        except Exception:
            vela_calc = None
        ed["señales_detalle"].append({"tipo": tipo_corto, "vela": vela_calc, "hora": hora_label})
    guardar_estado_dia()"""

if OLD_REGISTRAR not in content:
    errors.append("CAMBIO 1: funcion registrar_senal_disparada no encontrada")
else:
    content = content.replace(OLD_REGISTRAR, NEW_REGISTRAR, 1)
    print("Cambio 1 OK")

OLD_ENVIAR_SIG = """def enviar_senal_con_botones(simbolo, estrategia, hora_label, precio_vela, tipo_opcion, extra=""):
    registrar_senal_disparada(simbolo, estrategia)"""

NEW_ENVIAR_SIG = """def enviar_senal_con_botones(simbolo, estrategia, hora_label, precio_vela, tipo_opcion, extra=""):
    registrar_senal_disparada(simbolo, estrategia, hora_label=hora_label)"""

if OLD_ENVIAR_SIG not in content:
    errors.append("CAMBIO 2: firma enviar_senal_con_botones no encontrada")
else:
    content = content.replace(OLD_ENVIAR_SIG, NEW_ENVIAR_SIG, 1)
    print("Cambio 2 OK")

OLD_VELAS_SENALES = """    senales_hoy = []
    fecha_hoy = datetime.now(EST).strftime("%Y-%m-%d")
    if ed.get("fecha") == fecha_hoy:
        if ed.get("vr1_fired"):  senales_hoy.append({"tipo": "1VR",  "fecha": fecha_hoy})
        if ed.get("rpg_fired"):  senales_hoy.append({"tipo": "RPG",  "fecha": fecha_hoy})
        if ed.get("gna_fired"):  senales_hoy.append({"tipo": "GNA",  "fecha": fecha_hoy})
        if ed.get("gba_fired"):  senales_hoy.append({"tipo": "GBA",  "fecha": fecha_hoy})
        if ed.get("pm40_fired"): senales_hoy.append({"tipo": "PM40", "fecha": fecha_hoy})
        if ed.get("4ps_fired"):  senales_hoy.append({"tipo": "4PS",  "fecha": fecha_hoy})"""

NEW_VELAS_SENALES = """    senales_hoy = []
    fecha_hoy = datetime.now(EST).strftime("%Y-%m-%d")
    if ed.get("fecha") == fecha_hoy:
        detalle = ed.get("señales_detalle", [])
        if detalle:
            for d in detalle:
                senales_hoy.append({"tipo": d["tipo"], "fecha": fecha_hoy, "vela": d.get("vela"), "hora": d.get("hora")})
        else:
            if ed.get("vr1_fired"):  senales_hoy.append({"tipo": "1VR",  "fecha": fecha_hoy, "vela": "V1", "hora": None})
            if ed.get("rpg_fired"):  senales_hoy.append({"tipo": "RPG",  "fecha": fecha_hoy, "vela": None, "hora": None})
            if ed.get("gna_fired"):  senales_hoy.append({"tipo": "GNA",  "fecha": fecha_hoy, "vela": None, "hora": None})
            if ed.get("gba_fired"):  senales_hoy.append({"tipo": "GBA",  "fecha": fecha_hoy, "vela": None, "hora": None})
            if ed.get("pm40_fired"): senales_hoy.append({"tipo": "PM40", "fecha": fecha_hoy, "vela": None, "hora": None})
            if ed.get("4ps_fired"):  senales_hoy.append({"tipo": "4PS",  "fecha": fecha_hoy, "vela": None, "hora": None})"""

if OLD_VELAS_SENALES not in content:
    errors.append("CAMBIO 3: bloque senales_hoy en /velas no encontrado")
else:
    content = content.replace(OLD_VELAS_SENALES, NEW_VELAS_SENALES, 1)
    print("Cambio 3 OK")

content = content.replace("AXIS Breakout Sentinel v8.80", "AXIS Breakout Sentinel v8.81")
print("Version v8.81")

if errors:
    print("ERRORES:")
    for e in errors:
        print("  - " + e)
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("server.py v8.81 guardado")
