# hopeland_bot/scheduler.py
import os
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler

from .sheets import get_rows_since, spreadsheet_url
from .emailer import send_email

def _render_html(rows):
    if not rows:
        return "<p>No enquiries in this window.</p>"
    # simple table
    head = ["Timestamp Local", "WA Number", "WA Name", "Category", "Unit ID", "Title", "Reviewed"]
    th = "".join(f"<th style='text-align:left;padding:6px;border-bottom:1px solid #ccc'>{h}</th>" for h in head)
    trs = []
    for r in rows:
        tds = []
        for k in head:
            tds.append(f"<td style='padding:6px;border-bottom:1px solid #eee'>{r.get(k, '')}</td>")
        trs.append("<tr>" + "".join(tds) + "</tr>")
    table = f"<table cellspacing='0' cellpadding='0'>{'<tr>'+th+'</tr>'}{''.join(trs)}</table>"
    return table

def _render_text(rows):
    if not rows:
        return "No enquiries in this window."
    lines = []
    for r in rows:
        lines.append(f"{r.get('Timestamp Local','')} | {r.get('WA Number','')} | {r.get('Unit ID','')} | {r.get('Title','')}")
    return "\n".join(lines)

def send_6h_digest():
    try:
        rows = get_rows_since(6) or []
        url = spreadsheet_url() or "(sheet not available)"
        subject = f"HOPELAND WhatsApp enquiries — last 6 hours ({len(rows)})"
        html = f"<p>Here are the enquiries from the last 6 hours.</p><p>Sheet: <a href='{url}'>{url}</a></p>{_render_html(rows)}"
        text = f"Sheet: {url}\n\n{_render_text(rows)}"
        ok = send_email(subject, text, html)
        if ok:
            logging.info("6h digest sent to owners (%d rows).", len(rows))
        else:
            logging.warning("6h digest not sent (SMTP not configured or failed).")
    except Exception as e:
        logging.exception("Digest job failed: %s", e)

def start_scheduler():
    if os.environ.get("ENABLE_DIGEST", "0") != "1":
        logging.info("Digest scheduler disabled (ENABLE_DIGEST!=1).")
        return None
    try:
        sched = BackgroundScheduler(timezone=timezone.utc)
        # Run every 6 hours, first run in ~6 hours. If you want immediate test, call send_6h_digest() manually.
        sched.add_job(send_6h_digest, "interval", hours=6, id="hopeland_digest", replace_existing=True)
        sched.start()
        logging.info("Digest scheduler started (6h interval).")
        return sched
    except Exception as e:
        logging.exception("Failed to start scheduler: %s", e)
        return None
