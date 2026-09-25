"""Run against a static server: python scripts/check_browser.py [URL]."""
import json
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8765'
out = Path('work/screenshots'); out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(permissions=['clipboard-read', 'clipboard-write'], viewport={'width':1440,'height':1080})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(url); page.wait_for_load_state('networkidle')
    assert page.locator('#go').is_enabled()
    first = page.locator('#result-name').inner_text()
    assert first.endswith('1415')
    page.screenshot(path=str(out/'desktop.png'), full_page=True)
    for _ in range(4): page.locator('#advance').click()
    assert page.locator('#journey li[aria-current="step"]').count() == 1
    assert page.locator('#status').inner_text().startswith('Step 4')
    page.locator('#alternatives button').nth(1).click()
    chosen = page.locator('#result-name').inner_text()
    page.locator('#copy').click()
    assert page.evaluate('navigator.clipboard.readText()') == chosen
    page.locator('#share').click()
    link = page.evaluate('navigator.clipboard.readText()')
    page.goto(link); page.wait_for_load_state('networkidle')
    assert page.locator('#result-name').inner_text() == chosen
    with page.expect_download() as download:
        page.locator('#download').click()
    payload = json.loads(Path(download.value.path()).read_text())
    assert payload['variant'] == chosen
    assert len(payload['provenance']['corpus']) == 3
    for rule in ['rogue_to_king','markov_coin','quote_splice','archaic_coinage']:
        page.locator('#rule').select_option(rule)
        page.locator('#suffix').select_option('none')
        page.locator('#go').click()
        assert page.locator('#result-name').inner_text().isalpha()
        assert page.locator('#alternatives button').count() == 4
        assert page.locator('#ambition').is_enabled() == (rule == 'rogue_to_king')
    page.goto(url); page.wait_for_load_state('networkidle')
    for width in [375, 768, 1440]:
        page.set_viewport_size({'width':width,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), width
        if width == 375: page.screenshot(path=str(out/'mobile.png'), full_page=True)
    page.route('**/atlas.json', lambda route: route.fulfill(status=503, body='unavailable'))
    page.reload(); page.wait_for_load_state('networkidle')
    assert page.locator('#go').is_disabled()
    assert '503' in page.locator('#status').inner_text()
    assert not errors, errors
    browser.close()
print('Browser checks passed: modes, replay, export, clipboard, steps, responsive layout, load failure.')
