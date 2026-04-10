import logging
import os
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def _get_smtp_config() -> dict:
    """Read SMTP configuration from environment variables at call time."""
    return {
        "host": os.getenv("SMTP_HOST", "smtp-relay.brevo.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from_addr": os.getenv("SMTP_FROM", "noreply@bestiale2026.ch"),
    }


def _send_email(to: str, subject: str, body: str):
    """Send an email via SMTP if configured, otherwise print to console."""
    config = _get_smtp_config()

    if not config["password"]:
        # Mock mode: no SMTP password set, just print
        separator = "=" * 50
        print(f"\n{separator}\nMOCK EMAIL (no SMTP_PASSWORD set)\n{separator}")
        print(f"To: {to}\nSubject: {subject}\n\n{body}\n{separator}\n")
        logger.info(f"Mock email to {to}: {subject}")
        return

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = config["from_addr"]
    msg["To"] = to

    try:
        with smtplib.SMTP(config["host"], config["port"], timeout=10) as server:
            server.starttls()
            server.login(config["user"], config["password"])
            server.sendmail(config["from_addr"], [to], msg.as_string())
        logger.info(f"Email sent to {to}: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        raise


def send_password_reset_email(email: str | None, reset_link: str):
    """Send password reset link."""
    if not email:  # pragma: no cover
        logger.warning("No email provided for password reset, skipping")
        return
    _send_email(
        to=email,
        subject="Il tuo link per il reset della password - BeSTiapp",
        body=f"""Ciao,
Hai richiesto il reset della password o l'attivazione dell'account per BeSTiapp.

Clicca sul seguente link per impostare una nuova password:
{reset_link}

Il link scadrà tra 2 ore. Se non hai richiesto questo reset, ignora questa email.""",
    )


def send_reservation_requested_email(
    unit_email: str | None,
    unit_name: str,
    terrain_name: str,
    start_time: str,
    end_time: str,
):
    """Notify the unit that their reservation request has been submitted."""
    if not unit_email:
        logger.warning(f"No email for unit {unit_name}, skipping notification")
        return
    _send_email(
        to=unit_email,
        subject=f"Richiesta prenotazione inviata - {terrain_name}",
        body=f"""Ciao {unit_name},

La tua richiesta di prenotazione è stata inviata con successo!

Terreno: {terrain_name}
Periodo: {start_time} - {end_time}

La richiesta è in attesa di approvazione da parte dello staff. Riceverai un'email quando verrà processata.

Buon campo! ⛺""",
    )


def send_reservation_approved_email(
    unit_email: str | None,
    unit_name: str,
    terrain_name: str,
    start_time: str,
    end_time: str,
):
    """Notify the unit that their reservation was approved."""
    if not unit_email:
        logger.warning(f"No email for unit {unit_name}, skipping notification")
        return
    _send_email(
        to=unit_email,
        subject=f"✅ Prenotazione approvata - {terrain_name}",
        body=f"""Ciao {unit_name},

La tua prenotazione è stata APPROVATA! 🎉

Terreno: {terrain_name}
Periodo: {start_time} - {end_time}

Il terreno è riservato per voi. Buona attività! ⛺""",
    )


def send_reservation_rejected_email(
    unit_email: str | None,
    unit_name: str,
    terrain_name: str,
    start_time: str,
    end_time: str,
):
    """Notify the unit that their reservation was rejected."""
    if not unit_email:
        logger.warning(f"No email for unit {unit_name}, skipping notification")
        return
    _send_email(
        to=unit_email,
        subject=f"❌ Prenotazione rifiutata - {terrain_name}",
        body=f"""Ciao {unit_name},

Purtroppo la tua prenotazione è stata RIFIUTATA.

Terreno: {terrain_name}
Periodo: {start_time} - {end_time}

Puoi riprovare con un altro orario o un altro terreno. Per domande, contatta lo sportello.

Buon campo! ⛺""",
    )


def get_support_emails(db) -> list[str]:
    """Read support email addresses from AppSetting table."""
    from app.models import AppSetting

    setting = db.query(AppSetting).filter(AppSetting.key == "support_emails").first()
    if setting and setting.value.strip():
        return [e.strip() for e in setting.value.split(",") if e.strip()]
    return []


def send_support_email(
    user_email: str | None, user_name: str, subject: str, message: str, role: str, recipients: list[str] | None = None
):
    """Send a support request email to the configured support team."""
    if not recipients:
        recipients = ["tech@bestiale2026.ch"]  # fallback

    user_contact = user_email if user_email else "Nessuna email fornita"

    for admin_email in recipients:
        _send_email(
            to=admin_email,
            subject=f"[SUPPORTO] {subject} - {user_name}",
            body=f"""Nuova richiesta di supporto dall'applicazione BeSTiapp.

UTENTE: {user_name} (Ruolo: {role})
EMAIL DI CONTATTO: {user_contact}

OGGETTO: {subject}

MESSAGGIO:
{message}
""",
        )
