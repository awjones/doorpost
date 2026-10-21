"""Sending email (Settings > Email updates).

One sending account for the whole app, over SMTP: Gmail or Google Workspace with an
app password, or any other mail service's SMTP settings. The password lives in the
settings store's secrets and is never sent back to the browser.

Demo mode never sends: each message is kept in a small outbox in memory (and written
to data/outbox-demo/ as an .eml file), so the whole flow can be tried on a laptop.
"""
from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path
from typing import Callable, Optional

PROVIDERS = {
    "gmail": {"host": "smtp.gmail.com", "port": 587, "security": "starttls"},
    "outlook": {"host": "smtp.office365.com", "port": 587, "security": "starttls"},
    "icloud": {"host": "smtp.mail.me.com", "port": 587, "security": "starttls"},
}
SECURITY = ("starttls", "ssl", "none")
TIMEOUT = 20


class MailError(Exception):
    pass


@dataclass
class Account:
    provider: str = "gmail"
    host: str = ""
    port: int = 587
    security: str = "starttls"
    user: str = ""
    password: str = ""
    from_name: str = ""
    from_address: str = ""

    @classmethod
    def from_settings(cls, cfg: dict, password: Optional[str]) -> "Account":
        cfg = cfg or {}
        provider = cfg.get("provider") if cfg.get("provider") in (*PROVIDERS, "other") else "gmail"
        preset = PROVIDERS.get(provider, {})
        try:
            port = int(cfg.get("port") or preset.get("port") or 587)
        except (TypeError, ValueError):
            port = 587
        security = cfg.get("security") if cfg.get("security") in SECURITY else preset.get("security", "starttls")
        if provider != "other":
            security = preset["security"]
            port = preset["port"]
        return cls(provider=provider, host=(preset.get("host") if provider != "other" else str(cfg.get("host") or "").strip()),
                   port=port, security=security, user=str(cfg.get("user") or "").strip(), password=password or "",
                   from_name=str(cfg.get("from_name") or "").strip()[:60],
                   from_address=str(cfg.get("from_address") or "").strip())

    @property
    def ready(self) -> bool:
        return bool(self.host and self.user and self.password)

    @property
    def sender(self) -> str:
        return self.from_address or self.user


def build(account: Account, to: str, subject: str, text: str, html: str, app_name: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = formataddr((account.from_name or app_name, account.sender))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=(account.sender.split("@")[-1] or "doorpost.local"))
    msg["Auto-Submitted"] = "auto-generated"   # so mail apps don't send vacation replies back
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    return msg


def smtp_send(account: Account, msg: EmailMessage) -> None:
    if not account.ready:
        raise MailError("The sending account isn't set up yet (Settings > Email updates).")
    try:
        if account.security == "ssl":
            with smtplib.SMTP_SSL(account.host, account.port, timeout=TIMEOUT, context=ssl.create_default_context()) as smtp:
                smtp.login(account.user, account.password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(account.host, account.port, timeout=TIMEOUT) as smtp:
                if account.security == "starttls":
                    smtp.starttls(context=ssl.create_default_context())
                smtp.login(account.user, account.password)
                smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        raise MailError("The mail service turned down the sign-in. For Gmail, use an app password "
                        "(Google Account > Security > App passwords), not your normal password.") from exc
    except (smtplib.SMTPException, OSError) as exc:
        raise MailError(f"Couldn't send: {exc}") from exc


class Mailer:
    """Sends for real, or (demo mode) keeps the messages in an outbox."""

    def __init__(self, demo: bool, outbox_dir: Path, send: Optional[Callable[[Account, EmailMessage], None]] = None):
        self.demo = demo
        self.outbox_dir = outbox_dir
        self.outbox: list[dict] = []
        self._send = send or smtp_send

    def send(self, account: Account, to: str, subject: str, text: str, html: str, app_name: str) -> None:
        msg = build(account, to, subject, text, html, app_name)
        if self.demo:
            self.outbox.insert(0, {"to": to, "subject": subject, "html": html, "text": text})
            del self.outbox[20:]
            try:
                self.outbox_dir.mkdir(parents=True, exist_ok=True)
                name = "".join(c if c.isalnum() else "-" for c in subject)[:60]
                (self.outbox_dir / f"{len(list(self.outbox_dir.glob('*.eml'))):04d}-{name}.eml").write_bytes(bytes(msg))
            except OSError:
                pass
            return
        self._send(account, msg)
