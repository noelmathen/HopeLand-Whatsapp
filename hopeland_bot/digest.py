import logging, time, os
from .sheets import get_rows_since, spreadsheet_url
from .emailer import send_email

def _render_html(rows):
    if not rows: return "<p>No enquiries in this window.</p>"
    head = ["Timestamp Local","WA Number","WA Name","Category","Unit ID","Title","Reviewed"]
    th = "".join(f"<th style='text-align:left;padding:6px;border-bottom:1px solid #ccc'>{h}</th>" for h in head)
    trs=[]
    for r in rows:
        tds="".join(f"<td style='padding:6px;border-bottom:1px solid #eee'>{r.get(k,'')}</td>" for k in head)
        trs.append("<tr>"+tds+"</tr>")
    return f"<table cellspacing='0' cellpadding='0'><tr>{th}</tr>{''.join(trs)}</table>"

def _render_text(rows):
    if not rows: return "No enquiries in this window."
    return "\n".join(f"{r.get('Timestamp Local','')} | {r.get('WA Number','')} | {r.get('Unit ID','')} | {r.get('Title','')}" for r in rows)

def send_digest_once():
    rows = get_rows_since(6) or []
    url  = spreadsheet_url() or "(sheet not available)"
    subject = f"HOPELAND WhatsApp enquiries — last 6 hours ({len(rows)})"
    html = f"<p>Here are the enquiries from the last 6 hours.</p><p>Sheet: <a href='{url}'>{url}</a></p>{_render_html(rows)}"
    text = f"Sheet: {url}\n\n{_render_text(rows)}"
    ok = send_email(subject, text, html)
    if ok: logging.info("6h digest sent (%d rows).", len(rows))
    else:  logging.warning("6h digest failed or SMTP not configured.")

def loop_every_6h():
    while True:
        try: send_digest_once()
        except Exception as e: logging.exception("Digest loop error: %s", e)
        time.sleep(6*60*60)
