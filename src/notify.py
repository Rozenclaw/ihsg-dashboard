"""Notifications (Phase 3): daily digest via Telegram and/or email.

No-ops gracefully when unconfigured (so the daily job never fails on this).
Config via env vars or .streamlit/secrets.toml:
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, EMAIL_TO
"""
from __future__ import annotations

import os
from typing import Optional


def _secret(key: str) -> Optional[str]:
    v = os.environ.get(key)
    if v:
        return v
    try:
        import streamlit as st  # noqa
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return None


def format_digest(recs, paper_summary: dict | None = None) -> str:
    """Build a compact text digest from recommendations + paper summary."""
    buys = [r for r in recs if r.action == "BUY"]
    sells = [r for r in recs if r.action == "SELL"]
    lines = ["📊 IHSG Daily Digest", ""]
    if buys:
        lines.append(f"🟢 BUY ({len(buys)}):")
        for r in buys[:10]:
            lines.append(f"  • {r.symbol}  score {r.composite:.0f}  "
                         f"entry {r.entry:,.0f}  tgt {r.target:,.0f}  stop {r.stop:,.0f}"
                         if r.entry else f"  • {r.symbol}  score {r.composite:.0f}")
    else:
        lines.append("🟢 BUY: none today")
    if sells:
        lines.append("")
        lines.append(f"🔴 SELL ({len(sells)}): " + ", ".join(r.symbol for r in sells[:10]))
    if paper_summary:
        lines += ["", "💼 Paper portfolio:",
                  f"  equity {paper_summary['equity']:,.0f} IDR "
                  f"({paper_summary['total_return_pct']:+.1f}%)",
                  f"  cash {paper_summary['cash']:,.0f} · "
                  f"{paper_summary['positions']} positions"]
        if paper_summary.get("actions"):
            lines.append("  today: " + "; ".join(paper_summary["actions"][:8]))
    lines += ["", "⚠️ Not financial advice. Verify before trading."]
    return "\n".join(lines)


def send_telegram(text: str) -> tuple[bool, str]:
    token = _secret("TELEGRAM_BOT_TOKEN")
    chat = _secret("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False, "telegram not configured"
    try:
        import requests
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json={"chat_id": chat, "text": text}, timeout=10)
        r.raise_for_status()
        return True, "sent"
    except Exception as e:
        return False, f"telegram error: {e}"


def send_email(subject: str, body: str) -> tuple[bool, str]:
    host = _secret("SMTP_HOST")
    to = _secret("EMAIL_TO")
    if not host or not to:
        return False, "email not configured"
    try:
        import smtplib
        from email.mime.text import MIMEText
        port = int(_secret("SMTP_PORT") or 587)
        user = _secret("SMTP_USER")
        pwd = _secret("SMTP_PASS")
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = user or "ihsg-bot"
        msg["To"] = to
        with smtplib.SMTP(host, port, timeout=15) as s:
            s.starttls()
            if user and pwd:
                s.login(user, pwd)
            s.sendmail(msg["From"], [to], msg.as_string())
        return True, "sent"
    except Exception as e:
        return False, f"email error: {e}"


def notify(text: str, subject: str = "IHSG Daily Digest") -> dict:
    tg_ok, tg_msg = send_telegram(text)
    em_ok, em_msg = send_email(subject, text)
    return {"telegram": tg_msg, "email": em_msg, "any_sent": tg_ok or em_ok}
