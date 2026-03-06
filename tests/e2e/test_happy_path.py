import sqlite3

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
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "admin")
    page.click('button[type="submit"]')

    # Check admin is logged in (goes to index default)
    expect(page.locator("text=Classifica Generale")).to_be_visible()

    # Navigate to admin
    page.goto(f"{live_server}/admin")
    expect(page.locator("text=Amministrazione")).to_be_visible()


def test_login_admin_sportello(page: Page, live_server: str):
    """
    Test the happy path for Admin Sportello (tech).
    """
    page.goto(f"{live_server}/login")
    page.fill('input[name="username"]', "prog")
    page.fill('input[name="password"]', "esplo")
    page.click('button[type="submit"]')

    # Check admin is logged in
    expect(page.locator("text=Classifica Generale")).to_be_visible()

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

    page.fill('input[name="email"]', "admin@bestiale2026.ch")
    page.click('button[type="submit"]')

    expect(page.locator("text=Se l'email esiste")).to_be_visible()

    # Extract token from DB
    conn = sqlite3.connect("test_uat.db")
    cursor = conn.cursor()
    cursor.execute("SELECT reset_token FROM users WHERE email='admin@bestiale2026.ch'")
    token = cursor.fetchone()[0]
    conn.close()

    assert token is not None

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

    expect(page.locator("text=Classifica Generale")).to_be_visible()
