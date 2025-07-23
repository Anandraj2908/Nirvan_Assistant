import os
import smtplib
import threading
import time
import queue
import logging
import argparse
import signal
from typing import Optional, Callable, List, Dict, Any
from email.message import EmailMessage
from jinja2 import Environment, FileSystemLoader, Template
from prometheus_client import Counter, start_http_server
from .common import get_confirmation
import logging

logger = logging.getLogger(__name__)

def speak(text: str):
    """Placeholder - speech is handled by speech_handler"""
    logger.info(f"Email action result: {text}")

def listen_for_command(timeout: int = 15) -> str:
    """Placeholder - listening is handled by speech_handler"""
    logger.info("Email action requesting user input")
    return ""
from .config import (
    EMAIL_ADDRESS,
    EMAIL_PASSWORD,
    SMTP_SERVER,
    SMTP_PORT,
    RETRY_LIMIT,
    BATCH_SIZE,
    BATCH_INTERVAL,
    TEMPLATE_DIR,
    METRICS_PORT,
)

# ——————————————————————————————————————————————————————————————————————————————
# Logger setup
# ——————————————————————————————————————————————————————————————————————————————
logger = logging.getLogger("EmailActions")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler("email_actions.log")
ch = logging.StreamHandler()
fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
fh.setFormatter(fmt)
ch.setFormatter(fmt)
logger.addHandler(fh)
logger.addHandler(ch)

# ——————————————————————————————————————————————————————————————————————————————
# Prometheus metrics
# ——————————————————————————————————————————————————————————————————————————————
EMAIL_SENT = Counter("email_sent_total", "Total emails successfully sent")
EMAIL_FAILED = Counter("email_failed_total", "Total emails failed after retries")
EMAIL_QUEUED = Counter("email_queued_total", "Total emails queued for sending")

# Start metrics HTTP endpoint
start_http_server(METRICS_PORT)

# ——————————————————————————————————————————————————————————————————————————————
# Internal queues and threading
# ——————————————————————————————————————————————————————————————————————————————
_outgoing: queue.Queue = queue.Queue()
_shutdown_event = threading.Event()
_pause_event = threading.Event()

# Pre / post send hooks
_pre_send_hooks: List[Callable[[str, EmailMessage], None]] = []
_post_send_hooks: List[Callable[[str, EmailMessage, bool], None]] = []

def register_pre_send_hook(fn: Callable[[str, EmailMessage], None]) -> None:
    _pre_send_hooks.append(fn)

def register_post_send_hook(fn: Callable[[str, EmailMessage, bool], None]) -> None:
    _post_send_hooks.append(fn)

# ——————————————————————————————————————————————————————————————————————————————
# Helper: Load Jinja2 templates
# ——————————————————————————————————————————————————————————————————————————————
_jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=True
)

def load_template(name: str) -> Template:
    """
    Load a template by filename (e.g., 'welcome.html', 'alert.txt').
    Templates live in TEMPLATE_DIR.
    """
    return _jinja_env.get_template(name)

# ——————————————————————————————————————————————————————————————————————————————
# Low‑level SMTP send with retries & back‑off
# ——————————————————————————————————————————————————————————————————————————————
def _smtp_send(msg: EmailMessage) -> bool:
    attempt = 0
    delay = 1.0
    while attempt < RETRY_LIMIT:
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.send_message(msg)
            EMAIL_SENT.inc()
            logger.info(f"Sent email to {msg['To']}")
            return True
        except Exception as e:
            attempt += 1
            logger.warning(f"[Attempt {attempt}] send to {msg['To']} failed: {e}")
            time.sleep(delay)
            delay *= 2
    EMAIL_FAILED.inc()
    logger.error(f"All {RETRY_LIMIT} attempts failed for {msg['To']}")
    return False

# ——————————————————————————————————————————————————————————————————————————————
# Worker: consume queue in batches
# ——————————————————————————————————————————————————————————————————————————————
def _worker() -> None:
    """
    Background thread that batches up to BATCH_SIZE messages every BATCH_INTERVAL seconds.
    Honors pause and shutdown events.
    """
    batch: List[EmailMessage] = []
    last_flush = time.time()

    while not _shutdown_event.is_set():
        try:
            msg: EmailMessage = _outgoing.get(timeout=1)
            batch.append(msg)
            EMAIL_QUEUED.inc()
        except queue.Empty:
            pass

        # flush on batch size or interval
        now = time.time()
        if batch and (len(batch) >= BATCH_SIZE or (now - last_flush) >= BATCH_INTERVAL):
            if _pause_event.is_set():
                logger.info("Paused: skipping batch flush")
                last_flush = now
                continue

            for msg in batch:
                for hook in _pre_send_hooks:
                    hook(msg["To"], msg)
                success = _smtp_send(msg)
                for hook in _post_send_hooks:
                    hook(msg["To"], msg, success)
            batch.clear()
            last_flush = now

    # Drain remaining on shutdown
    for msg in batch:
        _smtp_send(msg)

# Start worker thread on import
_thread = threading.Thread(target=_worker, daemon=True)
_thread.start()

# ——————————————————————————————————————————————————————————————————————————————
# Graceful shutdown / pause / resume handlers
# ——————————————————————————————————————————————————————————————————————————————
def _handle_sigint(signum, frame):
    logger.info("SIGINT received, shutting down worker...")
    _shutdown_event.set()

def _handle_sigusr1(signum, frame):
    if _pause_event.is_set():
        logger.info("Resuming email worker")
        _pause_event.clear()
    else:
        logger.info("Pausing email worker")
        _pause_event.set()

signal.signal(signal.SIGINT, _handle_sigint)
signal.signal(signal.SIGUSR1, _handle_sigusr1)

# ——————————————————————————————————————————————————————————————————————————————
# Conversational / CLI interface
# ——————————————————————————————————————————————————————————————————————————————
def _ask(prompt: str, timeout: int = 15) -> Optional[str]:
    speak(prompt).wait()
    resp = listen_for_command(timeout=timeout)
    if not resp:
        speak("Timed out.").wait()
    return resp

def send_email(
    recipient: Optional[str] = None,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    html_template: Optional[str] = None,
    plain_template: Optional[str] = None,
    template_vars: Optional[Dict[str, Any]] = None,
    attachments: Optional[List[str]] = None
) -> None:
    """
    Interactive send: queues an EmailMessage with templates & attachments.
    """
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        speak("Email not configured!").wait()
        logger.error("Missing credentials")
        return

    # 1) Recipient
    to_email = recipient or _ask("Who should I send it to?")
    if not to_email:
        return speak("Cancelled.").wait()

    # 2) Subject
    subj = subject or _ask("What is the subject?")
    if not subj:
        return speak("Cancelled.").wait()

    # 3) Body or templates
    msg = EmailMessage()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subj

    # Render body
    if html_template:
        tpl = load_template(html_template)
        html = tpl.render(**(template_vars or {}))
        msg.add_alternative(html, subtype="html")
    if plain_template:
        tpl = load_template(plain_template)
        text = tpl.render(**(template_vars or {}))
        msg.set_content(text)
    if not html_template and not plain_template:
        body_text = body or _ask("What’s the message?")
        if not body_text:
            return speak("Cancelled.").wait()
        msg.set_content(body_text)

    # 4) Attachments
    for path in attachments or []:
        try:
            with open(path, "rb") as f:
                data = f.read()
            maintype, subtype = ("application", "octet-stream")
            fname = os.path.basename(path)
            msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=fname)
            logger.info(f"Attached {fname}")
        except Exception as e:
            logger.warning(f"Failed to attach {path}: {e}")

    # 5) Confirmation
    if not get_confirmation(f"Send to {to_email}?"):
        return speak("Okay, no email sent.").wait()

    # 6) Enqueue
    _outgoing.put(msg)
    speak("Email queued for sending.").wait()

# ——————————————————————————————————————————————————————————————————————————————
# CLI entry point
# ——————————————————————————————————————————————————————————————————————————————
def main() -> None:
    parser = argparse.ArgumentParser(description="Send an email via CLI or speak")
    parser.add_argument("--to", help="Recipient email")
    parser.add_argument("--subject", help="Subject line")
    parser.add_argument("--body", help="Plain-text body")
    parser.add_argument("--html-tpl", help="HTML template filename")
    parser.add_argument("--txt-tpl", help="Plain template filename")
    parser.add_argument("--var", action="append", nargs=2, metavar=("KEY","VAL"),
                        help="Template variable (can repeat)")
    parser.add_argument("--attach", nargs="+", help="Files to attach")
    parser.add_argument("--batch-interval", type=int, default=BATCH_INTERVAL,
                        help="Seconds between batch sends")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE,
                        help="Max emails per batch")
    args = parser.parse_args()

    vars_dict = {k:v for k,v in (args.var or [])}
    send_email(
        recipient=args.to,
        subject=args.subject,
        body=args.body,
        html_template=args.html_tpl,
        plain_template=args.txt_tpl,
        template_vars=vars_dict,
        attachments=args.attach,
    )
    # Keep process alive to flush queue
    try:
        while not _shutdown_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        _shutdown_event.set()

if __name__ == "__main__":
    main()

# ——————————————————————————————————————————————————————————————————————————————
# Unit‑test stubs (using pytest)
# ——————————————————————————————————————————————————————————————————————————————
import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def dummy_msg():
    from email.message import EmailMessage
    m = EmailMessage()
    m["From"] = EMAIL_ADDRESS
    m["To"] = "test@example.com"
    m["Subject"] = "Test"
    m.set_content("Hello")
    return m

def test_smtp_send_success(monkeypatch, dummy_msg):
    called = []
    class DummySMTP:
        def __init__(*args, **kwargs): pass
        def starttls(self): pass
        def login(self, u, p): pass
        def send_message(self, msg): called.append(msg)
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): pass

    monkeypatch.setattr(smtplib, "SMTP", DummySMTP)
    assert _smtp_send(dummy_msg) is True
    assert called and called[0] == dummy_msg

def test_smtp_send_failure(monkeypatch, dummy_msg):
    def bad_init(*a, **k): raise smtplib.SMTPException("Bad")
    monkeypatch.setattr(smtplib, "SMTP", bad_init)
    assert _smtp_send(dummy_msg) is False
