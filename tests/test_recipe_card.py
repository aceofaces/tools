import json

from playwright.sync_api import expect


def load_via_proxy(page, server, html, url="https://example.com/cookies"):
    """Serve `html` from the first CORS proxy and load `url` in the tool."""
    page.route(
        "https://api.allorigins.win/**",
        lambda route: route.fulfill(body=html, content_type="text/html"),
    )
    page.goto(f"{server}/recipe-card.html")
    page.evaluate("localStorage.clear()")
    page.fill("#url", url)
    page.click("#load-btn")
    expect(page.locator("#r-title")).to_have_text("Chocolate Chip Cookies")


def cell(page, text):
    return page.locator("#card td", has_text=text).first


def test_parser_library_loads(page, server):
    page.goto(f"{server}/recipe-card.html")
    assert page.evaluate("typeof ParseIngredient.parseIngredient") == "function"


def test_loads_recipe_from_url(page, server, fixture_html):
    load_via_proxy(page, server, fixture_html("cookies.html"))
    expect(page.locator("#r-meta")).to_contain_text("Prep 15 min")
    # One row per ingredient
    expect(page.locator("#card tr")).to_have_count(9)
    # Preheat is a note above the card, not a cell
    expect(page.locator("#r-notes li")).to_have_text(["Preheat oven to 375°F."])
    # Dry ingredients are whisked together, spanning their three rows
    whisk = cell(page, "whisk together")
    expect(whisk).to_have_attribute("rowspan", "3")
    # Ingredient names aren't mistaken for verbs ("baking soda", "brown sugar")
    expect(whisk).to_have_text("whisk together")
    expect(cell(page, "until creamy")).to_have_text("beat until creamy")
    # Butter gets its own prep cell
    expect(cell(page, "soften")).to_be_visible()
    # The final cell spans every row and picked up the oven temperature
    root = page.locator("#card td.root")
    expect(root).to_have_count(1)
    expect(root).to_have_attribute("rowspan", "9")
    expect(root).to_contain_text("bake 375°F 9–11 min until golden brown")
    assert "url=https%3A%2F%2Fexample.com%2Fcookies" in page.url


def test_scale_and_units(page, server, fixture_html):
    load_via_proxy(page, server, fixture_html("cookies.html"))
    expect(cell(page, "flour")).to_contain_text("2¼ cups")
    page.fill("#scale", "2")
    expect(cell(page, "flour")).to_contain_text("4½ cups")
    expect(page.locator("#servings")).to_have_value("48")
    page.select_option("#units", "metric")
    expect(cell(page, "flour")).to_contain_text("1.1 L")
    expect(page.locator("#card td.root")).to_contain_text("190°C")
    expect(page.locator("#r-notes")).to_contain_text("190°C")


def test_edit_structure(page, server, fixture_html):
    load_via_proxy(page, server, fixture_html("cookies.html"))
    page.click("#structure-panel summary")
    page.fill("#structure", "mix everything [7]\n  #1 flour\n  #2 soda\n")
    page.click("#structure-apply")
    expect(page.locator("#card tr")).to_have_count(2)
    expect(page.locator("#card td.root")).to_have_text("mix everything")
    expect(page.locator("#r-warn")).to_contain_text("Not in the card")
    page.fill("#structure", "stir\n  #99 nope")
    page.click("#structure-apply")
    expect(page.locator("#structure-error")).to_contain_text("no ingredient #99")


def test_paste_plain_text(page, server):
    page.goto(f"{server}/recipe-card.html")
    page.click("#paste-panel summary")
    page.fill("#paste", "\n".join([
        "Garlic Butter Pasta",
        "Ingredients",
        "8 oz spaghetti",
        "3 tbsp butter",
        "2 cloves garlic, minced",
        "Instructions",
        "1. Boil the spaghetti until al dente, then drain.",
        "2. Melt the butter in a pan over medium heat and add the garlic.",
        "3. Toss the spaghetti with the garlic butter and serve.",
    ]))
    page.click("#paste-btn")
    expect(page.locator("#r-title")).to_have_text("Garlic Butter Pasta")
    expect(page.locator("#card tr")).to_have_count(3)
    expect(cell(page, "mince")).to_be_visible()
    expect(page.locator("#card td.root")).to_have_attribute("rowspan", "3")
    page.select_option("#units", "metric")
    expect(cell(page, "spaghetti")).to_contain_text("225 g")


def test_paste_mealie_json(page, server):
    mealie = {
        "name": "Mealie Toast",
        "recipeServings": 2,
        "recipeIngredient": [
            {"display": "2 slices bread", "note": "bread"},
            {"display": "1 tbsp butter", "note": "butter"},
        ],
        "recipeInstructions": [
            {"title": "", "text": "Toast the bread."},
            {"title": "", "text": "Spread with butter."},
        ],
    }
    page.goto(f"{server}/recipe-card.html")
    page.click("#paste-panel summary")
    page.fill("#paste", json.dumps(mealie))
    page.click("#paste-btn")
    expect(page.locator("#r-title")).to_have_text("Mealie Toast")
    expect(page.locator("#card td.root")).to_have_text("spread")
    expect(page.locator("#card td.op").first).to_have_text("toast")


def test_fetch_failure_is_shown(page, server):
    for pattern in ["https://api.allorigins.win/**", "https://corsproxy.io/**", "https://api.codetabs.com/**"]:
        page.route(pattern, lambda route: route.fulfill(status=500, body="nope"))
    page.goto(f"{server}/recipe-card.html")
    page.fill("#url", "https://example.com/missing")
    page.click("#load-btn")
    expect(page.locator("#status")).to_contain_text("Could not fetch the page")
    expect(page.locator("#status")).to_contain_text("Wayback Machine")
