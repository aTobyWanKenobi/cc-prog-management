import os
import sqlite3
import time

from playwright.sync_api import Page, expect


def test_login_esplo_unit(page: Page, live_server: str):
    """
    Test the happy path for an Esploratori unit.
    """
    page.goto(f"{live_server}/login")
    page.fill('input[name="username"]', "faido")
    page.fill('input[name="password"]', "scout")
    page.click('button[type="submit"]')

    # Wait until it redirects and some content is visible
    expect(page.locator("text=Classifica Generale")).to_be_visible()


def test_login_admin_db(page: Page, live_server: str):
    """
    Test the happy path for Admin DB.
    """
    page.goto(f"{live_server}/login")
    page.click("button:has-text('Admin')")
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "admin")
    page.click('button[type="submit"]')

    # Check admin is logged in (goes to /prenotazioni)
    expect(page.locator("text=Tutte le Prenotazioni")).to_be_visible()

    # Navigate to admin
    page.goto(f"{live_server}/admin")
    expect(page.locator("text=Amministrazione")).to_be_visible()


def test_login_admin_sportello(page: Page, live_server: str):
    """
    Test the happy path for Admin Sportello (tech).
    """
    page.goto(f"{live_server}/login")
    page.click("button:has-text('Staff')")
    page.fill('input[name="username"]', "prog")
    page.fill('input[name="password"]', "esplo")
    page.click('button[type="submit"]')

    # Check admin is logged in (goes to /prenotazioni)
    expect(page.locator("text=Tutte le Prenotazioni")).to_be_visible()

    # Navigate to input
    page.goto(f"{live_server}/input")
    expect(page.locator("text=Registra Completamento")).to_be_visible()


def test_password_reset(page: Page, live_server: str):
    """
    Test the password reset flow using token extraction from the test database.
    """
    page.goto(f"{live_server}/login")
    page.click("text=Hai dimenticato la password")

    expect(page.locator("text=Setup o Recupero")).to_be_visible()

    email = "admin@bestiale2026.ch"
    page.fill('input[name="email"]', email)
    page.click('button[type="submit"]')

    expect(page.locator("text=Se l'email esiste")).to_be_visible()

    # Extract token from DB using the same URL as the server
    db_url = os.environ.get("DATABASE_URL", "sqlite:///./test_uat.db")
    db_path = db_url.replace("sqlite:///", "")
    if db_path.startswith("./"):
        db_path = db_path[2:]

    time.sleep(2)  # Wait for commit

    token = None
    # Try multiple times to handle any SQLite locking or delay
    for _ in range(5):
        if not os.path.exists(db_path):
            time.sleep(1)
            continue

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT reset_token FROM users WHERE email=?", (email,))
            row = cursor.fetchone()
            if row and row[0]:
                token = row[0]
                break
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()
        time.sleep(1)

    assert token is not None, f"Token not found for {email} in {db_path} (URL: {db_url})"

    # Visit reset link
    page.goto(f"{live_server}/reset-password?token={token}")
    expect(page.locator("text=Scegli la Nuova Password")).to_be_visible()

    page.fill('input[name="new_password"]', "new_admin_pass")
    page.click('button[type="submit"]')

    # Should be redirected to login with success message
    expect(page.locator("text=Password aggiornata con successo")).to_be_visible()

    # Wait for role tabs to be visible and click the Admin tab
    page.click("text=Admin")

    # Login with new password
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "new_admin_pass")
    page.click('button[type="submit"]')

    expect(page.locator("text=Tutte le Prenotazioni")).to_be_visible()


def test_submit_support_ticket(page: Page, live_server: str):
    """
    Test the support ticket submission flow.
    """
    page.goto(f"{live_server}/login")
    page.fill('input[name="username"]', "faido")
    page.fill('input[name="password"]', "scout")
    page.click('button[type="submit"]')

    expect(page.locator("text=Classifica Generale")).to_be_visible()

    # Desktop nav link for Supporto
    page.click("text=Supporto")
    expect(page.locator("text=Contatta il Supporto")).to_be_visible()

    page.fill('input[name="subject"]', "Test Subject E2E")
    page.fill('textarea[name="message"]', "This is a test message from Playwright.")
    page.click('button[type="submit"]')

    expect(page.locator("text=inviata con successo")).to_be_visible()
