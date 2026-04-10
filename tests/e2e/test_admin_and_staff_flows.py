import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.skip(reason="Needs proper DB seeding and async port binding")
def test_admin_flow_user_crud(page: Page, base_url):
    # Setup login
    page.goto(f"{base_url}/login")
    page.fill("input[name='username']", "direzione")
    page.fill("input[name='password']", "password")
    page.click("button[type='submit']")

    page.goto(f"{base_url}/admin/users")

    # Wait for the page to load correctly
    expect(page.locator("h1")).to_have_text(re.compile(r"Amministrazione"))

    # Create a new user
    page.fill("input[name='username']", "e2e_scout")
    page.fill("input[name='email']", "e2e@example.com")
    page.select_option("select[name='role']", "unit")
    page.get_by_text("Crea Utente").click()

    # Verify the creation and the one-time password alert
    expect(page.locator(".bg-yellow-50")).to_be_visible()
    expect(page.locator(".bg-yellow-50")).to_contain_text("e2e_scout")
    expect(page.locator(".bg-yellow-50")).to_contain_text("Password generata:")

    # Find the new user in the table and delete them
    row = page.locator("tr", has_text="e2e_scout")
    expect(row).to_be_visible()

    page.on("dialog", lambda dialog: dialog.accept())
    row.locator("button[type='submit']", has_text="❌").click()

    # Verify deletion
    expect(page.locator("tr", has_text="e2e_scout")).not_to_be_visible()


@pytest.mark.skip(reason="Needs proper DB seeding and async port binding")
def test_tech_flow_gestione_terreni(page: Page, base_url):
    # Setup login
    page.goto(f"{base_url}/login")
    page.fill("input[name='username']", "staff")
    page.fill("input[name='password']", "password")
    page.click("button[type='submit']")

    page.goto(f"{base_url}/gestione-terreni")

    expect(page.locator("h1")).to_have_text(re.compile(r"Gestione Prenotazioni Terreni"))

    # Verify filter dropdown exists
    dropdown = page.locator("select[name='terreno_id']")
    expect(dropdown).to_be_visible()

    # Assuming there's at least one terrain (seeded by conftest or DB)
    options = dropdown.locator("option").all_inner_texts()
    if len(options) > 1:
        # Select the first actual terrain (index 1, since 0 is "Tutti i Terreni")
        dropdown.select_option(index=1)

        # Verify the calendar view appears
        expect(page.locator("text=Calendario Occupazione")).to_be_visible()
        expect(page.locator("text=Rimuovi Filtro")).to_be_visible()

        # Click Remove Filter
        page.get_by_text("Rimuovi Filtro").click()

        # Verify Calendar is hidden again (since selected_terreno_id is None)
        expect(page.locator("text=Calendario Occupazione")).not_to_be_visible()
