"""
MeetCore — Brevo Email Service
Dispatches dynamic meeting briefings via Brevo REST API.
"""
import httpx
from app.core.config import get_settings

settings = get_settings()

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def build_dynamic_email_html(
    subject_title: str,
    summary: str | None = None,
    tasks: list[dict] | None = None,
    decisions: list[dict] | None = None,
) -> str:
    sections = []

    if summary and summary.strip():
        sections.append(f"""
        <div style="margin-bottom: 28px;">
            <h3 style="margin: 0 0 10px; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: #4338ca; font-weight: 700;">Meeting Summary</h3>
            <p style="margin: 0; font-size: 14px; line-height: 1.7; color: #334155;">{summary}</p>
        </div>
        """)

    if tasks:
        tasks_html = "".join(
            f"<li style='margin-bottom: 10px; color: #334155; font-size: 14px;'>"
            f"<strong>{t.get('description', '')}</strong>"
            f"<div style='font-size: 12px; color: #64748b; margin-top: 2px;'>"
            f"Owner: {t.get('owner') or 'Unassigned'} &nbsp;·&nbsp; Due: {t.get('deadline') or 'TBD'}"
            f"</div></li>"
            for t in tasks
        )
        sections.append(f"""
        <div style="margin-bottom: 28px;">
            <h3 style="margin: 0 0 12px; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: #4338ca; font-weight: 700;">Action Items & Tasks</h3>
            <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
                {tasks_html}
            </ul>
        </div>
        """)

    if decisions:
        decisions_html = "".join(
            f"<li style='margin-bottom: 8px; color: #334155; font-size: 14px;'>"
            f"{d.get('decision', '')}"
            f"<span style='font-size: 12px; color: #64748b;'> (by {d.get('made_by') or 'Team'})</span>"
            f"</li>"
            for d in decisions
        )
        sections.append(f"""
        <div style="margin-bottom: 28px;">
            <h3 style="margin: 0 0 12px; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: #4338ca; font-weight: 700;">Key Decisions</h3>
            <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
                {decisions_html}
            </ul>
        </div>
        """)

    content_body = "\n".join(sections) if sections else "<p style='color: #64748b; font-size: 14px;'>No details requested.</p>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 16px; padding: 32px; border: 1px solid #e2e8f0; box-shadow: 0 4px 20px rgba(0,0,0,0.03);">
            <div style="border-bottom: 1px solid #f1f5f9; padding-bottom: 20px; margin-bottom: 24px;">
                <h1 style="margin: 0; font-size: 22px; font-weight: 700; color: #4338ca; letter-spacing: -0.02em;">meetcore</h1>
                <p style="margin: 4px 0 0; font-size: 13px; color: #64748b;">{subject_title} · Delivered by Nio</p>
            </div>

            {content_body}

            <div style="border-top: 1px solid #f1f5f9; padding-top: 18px; margin-top: 32px; font-size: 12px; color: #94a3b8;">
                Sent directly by your meeting assistant Nio via MeetCore.
            </div>
        </div>
    </body>
    </html>
    """


async def send_meeting_email_brevo(
    to_email: str | None,
    subject: str,
    summary: str | None = None,
    tasks: list[dict] | None = None,
    decisions: list[dict] | None = None,
) -> bool:
    recipient = to_email or settings.DEFAULT_RECIPIENT_EMAIL
    if not recipient or not settings.BREVO_API_KEY:
        print("[Brevo] Missing BREVO_API_KEY or recipient email.", flush=True)
        return False

    html_content = build_dynamic_email_html(
        subject_title=subject,
        summary=summary,
        tasks=tasks,
        decisions=decisions,
    )

    payload = {
        "sender": {
            "name": settings.BREVO_SENDER_NAME,
            "email": settings.BREVO_SENDER_EMAIL,
        },
        "to": [{"email": recipient}],
        "subject": f"MeetCore: {subject}",
        "htmlContent": html_content,
    }

    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(BREVO_URL, json=payload, headers=headers)
            if res.status_code in (200, 201):
                print(f"[Brevo] Email successfully sent to {recipient}", flush=True)
                return True
            else:
                print(f"[Brevo] Send failed ({res.status_code}): {res.text}", flush=True)
                return False
    except Exception as e:
        print(f"[Brevo] Exception sending email: {e}", flush=True)
        return False