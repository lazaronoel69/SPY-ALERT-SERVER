#!/usr/bin/env python3
"""AXIS weekly reconciliation delivery — AX-TRACK-NOTIFY-001.

Detects the newest committed reconciliation report, sends one concise summary
to the configured Telegram chat, and persists the delivered report name under
/data so Railway restarts cannot duplicate the notification.
"""

import html
import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from axis_config import DATA_DIR


REPORTS_DIR = Path(__file__).resolve().parent / "docs" / "AXIS-2.0" / "reconciliations"
STATE_FILE = Path(DATA_DIR) / "axis_reconciliation_notify.json"
GITHUB_REPORT_BASE = (
    "https://github.com/lazaronoel69/SPY-ALERT-SERVER/blob/main/"
    "docs/AXIS-2.0/reconciliations"
)

_lock = threading.RLock()


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_state(state_file=STATE_FILE):
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"AX-TRACK-NOTIFY: error leyendo estado: {e}")
        return {}


def _save_state(state, state_file=STATE_FILE):
    state_file = Path(state_file)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = state_file.with_suffix(f"{state_file.suffix}.tmp")
    with open(temporary, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(temporary, state_file)


def latest_report(reports_dir=REPORTS_DIR):
    reports_dir = Path(reports_dir)
    reports = list(reports_dir.glob("*-AX-TRACK-AUDIT-*.md"))
    return max(reports, key=lambda path: path.name) if reports else None


def _table_rows(markdown):
    rows = {}
    for label, value in re.findall(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", markdown, re.M):
        label = label.strip().replace("`", "")
        value = value.strip().replace("**", "")
        if label.lower() not in {"control", "---", ":---"} and not set(label) <= {"-", ":"}:
            rows[label] = value
    return rows


def parse_report(report_path):
    markdown = Path(report_path).read_text(encoding="utf-8")
    audit_match = re.search(r"^#\s+(AX-TRACK-AUDIT-\d+)", markdown, re.M)
    cutoff_match = re.search(r"\*\*Fecha de corte(?: técnico)?:\*\*\s*(.+)", markdown)
    sessions_match = re.search(r"\*\*Sesiones de mercado incluidas:\*\*\s*(.+)", markdown)
    if not sessions_match:
        sessions_match = re.search(
            r"\*\*(?:Período|Período completo de alertas):\*\*\s*(.+)", markdown
        )
    result_match = re.search(
        r"##\s+Resultado ejecutivo\s+\*\*(.+?)\*\*", markdown, re.S
    )
    rows = _table_rows(markdown)

    def row(prefix, default="No disponible"):
        for label, value in rows.items():
            if label.lower().startswith(prefix.lower()):
                return value
        return default

    alerts_total = row("Alertas acumuladas", row("Alertas registradas"))
    alerts_new = row("Alertas generadas", row("Alertas nuevas"))
    states = row("Alertas ACTIVE / CLOSED / CANCELLED", None)
    if states is None:
        active = row("Alertas activas", "?")
        closed = row("Cerradas acumuladas", row("Alertas cerradas", "?"))
        cancelled = row("Canceladas acumuladas", row("Alertas canceladas", "?"))
        states = f"{active} / {closed} / {cancelled}"

    return {
        "audit_id": audit_match.group(1) if audit_match else Path(report_path).stem,
        "cutoff": cutoff_match.group(1).strip() if cutoff_match else "No disponible",
        "sessions": sessions_match.group(1).strip() if sessions_match else "No disponible",
        "result": result_match.group(1).strip() if result_match else "REVISAR REPORTE",
        "alerts_total": alerts_total,
        "alerts_new": alerts_new,
        "states": states,
        "terminal_new": row("Resultados terminales nuevos", row("Nuevos cierres")),
        "positions_open": row("Posiciones abiertas"),
        "orphans": row(
            "Posiciones abiertas sin alert_id",
            row("Posiciones sin alert_id", row("Posiciones sin alerta")),
        ),
    }


def build_message(report_path):
    data = parse_report(report_path)
    report_name = Path(report_path).name
    report_url = f"{GITHUB_REPORT_BASE}/{report_name}"

    esc = lambda value: html.escape(str(value), quote=True)
    return (
        f"📊 <b>AXIS — Reconciliación semanal</b>\n"
        f"<b>{esc(data['audit_id'])}</b>\n\n"
        f"📅 Sesiones: {esc(data['sessions'])}\n"
        f"⏱ Corte: {esc(data['cutoff'])}\n\n"
        f"• Alertas acumuladas: <b>{esc(data['alerts_total'])}</b>\n"
        f"• Alertas nuevas: <b>{esc(data['alerts_new'])}</b>\n"
        f"• ACTIVE / CLOSED / CANCELLED: <b>{esc(data['states'])}</b>\n"
        f"• Resultados terminales nuevos: <b>{esc(data['terminal_new'])}</b>\n"
        f"• Posiciones abiertas: <b>{esc(data['positions_open'])}</b>\n"
        f"• Posiciones sin alert_id: <b>{esc(data['orphans'])}</b>\n\n"
        f"<b>Resultado:</b> {esc(data['result'])}\n"
        f"🔗 <a href=\"{report_url}\">Ver reporte completo</a>"
    )


def _send_telegram(message):
    token = os.environ.get("TELEGRAM_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        raise RuntimeError("credenciales de Telegram no disponibles")

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
    except requests.RequestException:
        raise RuntimeError("fallo de red con Telegram") from None
    if not response.ok:
        raise RuntimeError(f"Telegram respondió HTTP {response.status_code}")
    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError("respuesta inválida de Telegram") from None
    if not payload.get("ok"):
        raise RuntimeError("Telegram rechazó el mensaje")
    return payload.get("result", {}).get("message_id")


def notify_latest_once(reports_dir=REPORTS_DIR, state_file=STATE_FILE, sender=None):
    """Sends the latest report at most once. Safe to call after every deploy."""
    sender = sender or _send_telegram
    report = latest_report(reports_dir)
    if report is None:
        return {"status": "NO_REPORT", "report": None}

    with _lock:
        state = _load_state(state_file)
        if state.get("last_sent_report") == report.name:
            return {"status": "ALREADY_SENT", "report": report.name}

        state.update({
            "status": "SENDING",
            "last_attempt_report": report.name,
            "last_attempt_at": _now_iso(),
            "last_error": None,
        })
        _save_state(state, state_file)

        try:
            message_id = sender(build_message(report))
        except Exception as e:
            error = str(e)[:160] if isinstance(e, RuntimeError) else "fallo interno de entrega"
            state.update({"status": "FAILED", "last_error": error})
            _save_state(state, state_file)
            print(f"AX-TRACK-NOTIFY: fallo enviando {report.name}: {error}")
            return {"status": "FAILED", "report": report.name, "error": error}

        state.update({
            "status": "SENT",
            "last_sent_report": report.name,
            "last_sent_at": _now_iso(),
            "telegram_message_id": message_id,
            "last_error": None,
        })
        _save_state(state, state_file)
        print(f"AX-TRACK-NOTIFY: {report.name} enviado por Telegram")
        return {"status": "SENT", "report": report.name}


def notification_status(reports_dir=REPORTS_DIR, state_file=STATE_FILE):
    state = _load_state(state_file)
    report = latest_report(reports_dir)
    latest_name = report.name if report else None
    if latest_name is None:
        status = "NO_REPORT"
    elif state.get("last_sent_report") == latest_name:
        status = "SENT"
    elif state.get("last_attempt_report") == latest_name:
        status = state.get("status", "PENDING")
    else:
        status = "PENDING"
    return {
        "feature": "AX-TRACK-NOTIFY-001",
        "latest_report": latest_name,
        "status": status,
        "last_sent_report": state.get("last_sent_report"),
        "last_sent_at": state.get("last_sent_at"),
        "telegram_message_id": state.get("telegram_message_id"),
        "last_attempt_at": state.get("last_attempt_at"),
        "last_error": state.get("last_error"),
    }


def reconciliation_notification_loop(retry_seconds=300, max_attempts=None):
    """Retries every five minutes until delivery; max_attempts is test-only."""
    attempt = 0
    while max_attempts is None or attempt < max_attempts:
        attempt += 1
        result = notify_latest_once()
        if result["status"] in {"SENT", "ALREADY_SENT", "NO_REPORT"}:
            return
        if max_attempts is None or attempt < max_attempts:
            time.sleep(retry_seconds)
