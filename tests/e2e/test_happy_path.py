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
