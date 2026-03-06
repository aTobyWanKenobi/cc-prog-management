import logging

logger = logging.getLogger(__name__)


def _print_email(to: str, subject: str, body: str):
    """Internal helper to mock-send an email by printing to console."""
    separator = "=" * 50
    email_content = f"""
{separator}
MOCK EMAIL SERVICE
{separator}
To: {to}
Subject: {subject}

{body}
{separator}
"""
    print(email_content)
    logger.info(f"Email sent to {to}: {subject}")


def send_password_reset_email(email: str, reset_link: str):
    """Send password reset link."""
    _print_email(
        to=email,
        subject="Il tuo link per il reset della password - BeSTiale 2026",
        body=f"""Ciao,
Hai richiesto il reset della password o l'attivazione dell'account per il Punteggiometro BeSTiale 2026.

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
    _print_email(
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
    _print_email(
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
    _print_email(
        to=unit_email,
        subject=f"❌ Prenotazione rifiutata - {terrain_name}",
        body=f"""Ciao {unit_name},

Purtroppo la tua prenotazione è stata RIFIUTATA.

Terreno: {terrain_name}
Periodo: {start_time} - {end_time}

Puoi riprovare con un altro orario o un altro terreno. Per domande, contatta lo sportello.

Buon campo! ⛺""",
    )
