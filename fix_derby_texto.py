import sys

with open("server.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

errors = []
cambios = 0

for i, line in enumerate(lines):
    if "Reto Millonario:</b>" in line:
        lines[i] = line.replace(
            "\U0001F3C6 <b>Reto Millonario:</b>",
            "\U0001F3C7 <b>Derby:</b>"
        )
        cambios += 1
        print(f"Linea {i+1} cambiada: Reto Millonario -> Derby")
    if "Carriles vivos:" in line and "/10" in line:
        lines[i] = line.replace("Carriles vivos:", "Caballos vivos:").replace("/10", "/4")
        cambios += 1
        print(f"Linea {i+1} cambiada: Carriles -> Caballos, /10 -> /4")

if cambios != 2:
    errors.append(f"Se esperaban 2 cambios, se hicieron {cambios}")

content = "".join(lines)
content = content.replace("AXIS Breakout Sentinel v8.81", "AXIS Breakout Sentinel v8.82")
print("Version v8.82")

if errors:
    print("ERRORES:")
    for e in errors:
        print("  - " + e)
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("server.py v8.82 guardado")
