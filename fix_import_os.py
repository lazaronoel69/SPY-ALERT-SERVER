import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD = '''import requests
import threading
import time
from datetime import datetime, timedelta, date
import pytz
from flask import Flask, jsonify, request'''

NEW = '''import os
import requests
import threading
import time
from datetime import datetime, timedelta, date
import pytz
from flask import Flask, jsonify, request'''

if OLD not in content:
    errors.append("Bloque de imports iniciales no encontrado")
else:
    content = content.replace(OLD, NEW, 1)
    print("Cambio OK: import os movido al inicio del archivo")

OLD_DUP = '''# - TRADIER SANDBOX (ordenes paper trading) --
import os
import json'''

NEW_DUP = '''# - TRADIER SANDBOX (ordenes paper trading) --
import json'''

if OLD_DUP in content:
    content = content.replace(OLD_DUP, NEW_DUP, 1)
    print("Cambio OK: import os duplicado eliminado")
else:
    OLD_DUP2 = '''import os
import json'''
    if content.count(OLD_DUP2) >= 1 and content.count("import os") >= 2:
        content = content.replace(OLD_DUP2, "import json", 1)
        print("Cambio OK: import os duplicado eliminado (variante 2)")
    else:
        print("AVISO: no se encontro import os duplicado para eliminar - puede que no exista, no es bloqueante")

content = content.replace('AXIS Breakout Sentinel v8.79', 'AXIS Breakout Sentinel v8.80')
print("Version v8.80")

if errors:
    print("ERRORES:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("server.py v8.80 guardado")
