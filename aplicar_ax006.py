import sys

with open("server.py", "r", encoding="utf-8") as f:
    content = f.read()

errors = []

OLD1 = 'def enviar_telegram(mensaje):\n    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"\n    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}\n    try:\n        r = requests.post(url, json=payload, timeout=10)\n        print(f"Telegram: {r.status_code} — {mensaje[:60]}")\n    except Exception as e:\n        print(f"Error Telegram: {e}")'

NEW1 = '# AX-006: enviar_telegram movida a axis_telegram.py. Mismo nombre,\n# mismo comportamiento, mismo parse_mode HTML, mismo timeout.\nfrom axis_telegram import enviar_telegram'

if content.count(OLD1) != 1:
    errors.append(f'Se esperaba 1 coincidencia de enviar_telegram, se encontraron {content.count(OLD1)}')
else:
    content = content.replace(OLD1, NEW1, 1)
    print('Cambio OK: enviar_telegram -> axis_telegram.py')

if errors:
    print('ERRORES:')
    for e in errors:
        print('  - ' + e)
    sys.exit(1)
else:
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('server.py actualizado -- enviar_telegram ahora en axis_telegram.py')
