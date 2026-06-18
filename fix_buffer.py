# fix_buffer.py — Cambia buffer de 17min a 1min v8.67
# Corre desde: /Users/noellazaro/SPY-ALERT-SERVER/
# Uso: python3 fix_buffer.py

import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

# Reemplazar los 3 lugares donde dice timedelta(minutes=17) por timedelta(minutes=1)
count = content.count("timedelta(minutes=17)")
if count != 3:
    errors.append(f"Se esperaban 3 ocurrencias de timedelta(minutes=17), se encontraron {count}")
else:
    content = content.replace("timedelta(minutes=17)", "timedelta(minutes=1)")
    print(f"✅ Buffer cambiado de 17min a 1min en {count} lugares")

# Version v8.67
content = content.replace('AXIS Breakout Sentinel v8.66', 'AXIS Breakout Sentinel v8.67')
content = content.replace('"sistema": "AXIS Breakout Sentinel v8.66"', '"sistema": "AXIS Breakout Sentinel v8.67"')
content = content.replace('print("AXIS Breakout Sentinel v8.66 iniciado...")', 'print("AXIS Breakout Sentinel v8.67 iniciado...")')
print("✅ Versión v8.67")

if errors:
    print("\n❌ ERRORES:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("\n✅ server.py v8.67 guardado — buffer 1min")
    print("   Corre: git add server.py && git commit -m 'fix: buffer barras 1min v8.67' && git push origin main")

