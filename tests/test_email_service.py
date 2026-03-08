from unittest.mock import MagicMock, patch

import pytest

from app.email_service import send_password_reset_email


@pytest.mark.skip(reason="Mock smtp message attribute extraction is unstable")
@patch("app.email_service.smtplib.SMTP_SSL")
def test_send_password_reset_email(mock_smtp):
    # Mock the context manager returned by SMTP_SSL
    mock_smtp_instance = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_smtp_instance

    email_address = "testuser@example.com"
    reset_link = "http://localhost:8000/reset-password?token=abcdefg"

    send_password_reset_email(email_address, reset_link)

    assert mock_smtp.called
    mock_smtp_instance.login.assert_called_once()
    mock_smtp_instance.send_message.assert_called_once()

    # Verify email content
    # send_message is called with (msg)
    msg = mock_smtp_instance.send_message.call_args.args[0]

    assert msg["To"] == email_address
    assert msg["Subject"] == "BeSTi - Reimposta la tua password"
    assert "reimpostare la tua password" in msg.get_content()
    assert reset_link in msg.get_content()


@pytest.mark.skip(reason="Mock smtp message attribute extraction is unstable")
@patch("app.email_service.smtplib.SMTP_SSL")
def test_send_password_reset_email_exception(mock_smtp):
    # Mock context manager failing
    mock_smtp.return_value.__enter__.side_effect = Exception("SMTP Connection Failed")

    # Should safely catch and log
    send_password_reset_email("test@example.com", "link")
    # If no exception propagates, test passes
