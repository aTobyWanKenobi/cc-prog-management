import logging

logger = logging.getLogger(__name__)

def send_password_reset_email(email: str, reset_link: str):
    """
    Mock email service that logs the password reset link to the console.
    In a production environment, this would integrate with an SMTP server or email API.
    """
    separator = "=" * 50
    email_content = f"""
{separator}
MOCK EMAIL SERVICE - PASSWORD RESET
{separator}
To: {email}
Subject: Il tuo link per il reset della password - BeSTiale 2026

Ciao,
Hai richiesto il reset della password o l'attivazione dell'account per il Punteggiometro BeSTiale 2026.

Clicca sul seguente link per impostare una nuova password:
{reset_link}

Il link scadrà tra 2 ore. Se non hai richiesto questo reset, ignora questa email.
{separator}
"""
    print(email_content)
    # Also log it just in case
    logger.info(f"Password reset email sent to {email}")
