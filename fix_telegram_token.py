import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD = '''TELEGRAM_TOKEN   = "8668514895:AAGWRxFmA9c8tZKIe-5i9tJ31RQtzi1-NYs"
TELEGRAM_CHAT_ID = "-5010153427"'''

NEW = '''TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-5010153427")'''

if OLD not in content:
    errors.append("Bloque TELEGRAM_TOKEN original no encontrado")
else:
    content = content.replace(OLD, NEW, 1)
    print("Cambio OK: TELEGRAM_TOKEN ahora se lee de variable de entorno")

content = content.replace('AXIS Breakout Sentinel v8.78', 'AXIS Breakout Sentinel v8.79')
print("Version v8.79")

if errors:
    print("ERRORES:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("server.py v8.79 guardado")
    print("IMPORTANTE: agregar TELEGRAM_TOKEN como variable de entorno en Railway ANTES de hacer push")
