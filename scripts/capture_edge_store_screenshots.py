"""Capture real Microsoft Edge store screenshots for the packaged extension."""

from __future__ import annotations

import json
import random
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from test_extension import find_test_tab, launch_context, popup_url, start_server, wait_for_extension  # noqa: E402

OUT = ROOT / "store" / "edge" / "screenshots"
TMP = ROOT / "work" / "edge-store-capture"
EXTENSION = ROOT / "dist" / "extension-test"
ICON = ROOT / "store" / "edge" / "assets" / "store-icon-300.png"
PAPER = (243, 236, 220)
PAPER_RAISED = (251, 246, 234)
INK = (30, 27, 22)
MUTED = (102, 95, 84)
NAVY = (15, 23, 42)
RED = (125, 45, 42)
RULE = (207, 194, 170)
FONT_REGULAR = Path(r"C:\Windows\Fonts\georgia.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\georgiab.ttf")
FONT_MONO = Path(r"C:\Windows\Fonts\consola.ttf")


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def paper_canvas() -> Image.Image:
    image = Image.new("RGB", (1280, 800), PAPER)
    rng = random.Random(1415)
    noise = Image.new("RGB", image.size)
    pixels = noise.load()
    for y in range(image.height):
        for x in range(image.width):
            value = rng.randint(0, 9)
            pixels[x, y] = (PAPER[0] - value, PAPER[1] - value, PAPER[2] - value)
    image = Image.blend(image, noise, 0.16)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((18, 18, 1262, 782), radius=22, outline=RULE, width=2)
    draw.rounded_rectangle((28, 28, 1252, 772), radius=17, outline=(218, 203, 177), width=1)
    return image


def shadowed_popup(canvas: Image.Image, popup_path: Path, box: tuple[int, int, int, int]) -> None:
    popup = Image.open(popup_path).convert("RGB")
    target_w = box[2] - box[0]
    target_h = box[3] - box[1]
    popup = popup.resize((target_w, target_h), Image.Resampling.LANCZOS)
    mask = Image.new("L", canvas.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((box[0] + 12, box[1] + 18, box[2] + 12, box[3] + 18), radius=24, fill=120)
    shadow = Image.new("RGB", canvas.size, (43, 31, 18))
    canvas.paste(shadow, (0, 0), mask.filter(ImageFilter.GaussianBlur(20)))
    popup_mask = Image.new("L", popup.size, 0)
    ImageDraw.Draw(popup_mask).rounded_rectangle((0, 0, popup.width, popup.height), radius=14, fill=255)
    canvas.paste(popup, (box[0], box[1]), popup_mask)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(box, radius=14, outline=(205, 188, 160), width=1)


def brand_header(canvas: Image.Image, label: str) -> None:
    icon = Image.open(ICON).convert("RGB").resize((62, 62), Image.Resampling.LANCZOS)
    icon_mask = Image.new("L", icon.size, 0)
    ImageDraw.Draw(icon_mask).rounded_rectangle((0, 0, icon.width, icon.height), radius=13, fill=255)
    canvas.paste(icon, (62, 52), icon_mask)
    draw = ImageDraw.Draw(canvas)
    draw.text((144, 58), "NICKSPEARE", font=font(FONT_BOLD, 26), fill=NAVY)
    draw.text((144, 91), label.upper(), font=font(FONT_MONO, 12), fill=RED)
    draw.line((62, 132, 602, 132), fill=RULE, width=1)


def text_block(canvas: Image.Image, headline: str, body: str, note: str) -> None:
    draw = ImageDraw.Draw(canvas)
    draw.multiline_text((62, 174), headline, font=font(FONT_BOLD, 54), fill=INK, spacing=8)
    draw.multiline_text((64, 342), body, font=font(FONT_REGULAR, 22), fill=MUTED, spacing=10)
    draw.line((64, 636, 602, 636), fill=RULE, width=1)
    draw.multiline_text((64, 662), note, font=font(FONT_MONO, 14), fill=RED, spacing=6)


def render_generate(popup_path: Path) -> None:
    canvas = paper_canvas()
    brand_header(canvas, "Offline generating room")
    text_block(canvas, "A name with\na paper trail.", "Generate four to six seeded Shakespearean usernames locally.\nEach candidate keeps its formation story and source ingredients.", "LOCAL ENGINE  /  SEEDED REPLAY  /  COPY-READY")
    shadowed_popup(canvas, popup_path, (760, 44, 1234, 762))
    canvas.save(OUT / "01-generate.png", "PNG", optimize=True)


def render_shape(popup_path: Path) -> None:
    canvas = paper_canvas()
    brand_header(canvas, "Username constraints")
    text_block(canvas, "Shape the sound\nand the rules.", "Set length, case, suffix, candidate count, digits, underscores,\nreserved words, forbidden prefixes, and forbidden suffixes.", "REGENERATE  /  NEVER TRUNCATE  /  REVIEW EVERY CANDIDATE")
    shadowed_popup(canvas, popup_path, (760, 44, 1234, 762))
    canvas.save(OUT / "02-shape.png", "PNG", optimize=True)


def render_field(fixture_path: Path, popup_path: Path) -> None:
    fixture = Image.open(fixture_path).convert("RGB").resize((1280, 800), Image.Resampling.LANCZOS)
    overlay = Image.new("RGB", fixture.size, PAPER)
    canvas = Image.blend(fixture, overlay, 0.42)
    veil = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    veil_draw = ImageDraw.Draw(veil)
    veil_draw.rectangle((0, 0, 700, 800), fill=(*PAPER_RAISED, 226))
    veil_draw.rounded_rectangle((18, 18, 1262, 782), radius=22, outline=(*RULE, 255), width=2)
    canvas = Image.alpha_composite(canvas.convert("RGBA"), veil).convert("RGB")
    brand_header(canvas, "User-controlled page insertion")
    text_block(canvas, "Fill only the\nfield you choose.", "Page access begins with your click. Sensitive fields are excluded;\nnon-empty fields need an explicit replacement action.", "ACTIVE TAB  /  NO AUTO-SUBMIT  /  NO HOST PERMISSIONS")
    shadowed_popup(canvas, popup_path, (760, 44, 1234, 762))
    canvas.save(OUT / "03-fill-field.png", "PNG", optimize=True)


def capture() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    server, base_url, _thread = start_server()
    try:
        with sync_playwright() as playwright:
            with tempfile.TemporaryDirectory(prefix="nickspeare-store-edge-") as profile:
                context = launch_context(playwright, "msedge", profile, EXTENSION)
                try:
                    extension_id = wait_for_extension(context)
                    fixture_page = context.new_page()
                    fixture_page.goto(f"{base_url}/docs/fixtures/edge-review.html", wait_until="domcontentloaded")
                    fixture_page.set_viewport_size({"width": 1280, "height": 800})
                    fixture_page.screenshot(path=str(TMP / "fixture.png"), full_page=False)

                    popup = context.new_page()
                    popup.goto(popup_url(extension_id), wait_until="domcontentloaded")
                    popup.locator(".candidate-name").first.wait_for(timeout=15_000)
                    popup.screenshot(path=str(TMP / "generate.png"), full_page=False)

                    popup.locator(".advanced summary").click()
                    popup.locator("#rule").select_option("markov_coin")
                    popup.locator("#caseStyle").select_option("title")
                    popup.locator("#suffix").select_option("none")
                    popup.locator("#candidateCount").select_option("6")
                    popup.locator("#minLength").fill("5")
                    popup.locator("#maxLength").fill("16")
                    popup.locator("#generate").click()
                    popup.wait_for_function("document.querySelectorAll('.candidate-name').length >= 4")
                    popup.evaluate("document.querySelector('.advanced').scrollIntoView({block:'start'}); window.scrollBy(0,-8)")
                    popup.screenshot(path=str(TMP / "shape.png"), full_page=False)

                    popup.evaluate("document.querySelector('.advanced summary').click(); window.scrollTo(0,0)")
                    test_tab_id = find_test_tab(popup, "/docs/fixtures/edge-review.html")
                    popup.evaluate(f"chrome.tabs.update({test_tab_id}, {{active:true}})")
                    popup.evaluate("document.querySelector('.candidate .fill').click()")
                    popup.locator(".field-choice").first.wait_for(timeout=10_000)
                    popup.evaluate("document.querySelector('#field-panel').scrollIntoView({block:'center'})")
                    popup.screenshot(path=str(TMP / "field.png"), full_page=False)

                    render_generate(TMP / "generate.png")
                    render_shape(TMP / "shape.png")
                    render_field(TMP / "fixture.png", TMP / "field.png")
                finally:
                    context.close()
    finally:
        server.shutdown()
        server.server_close()

    report = {
        "schemaVersion": 1,
        "browser": "msedge",
        "screenshots": [
            "store/edge/screenshots/01-generate.png",
            "store/edge/screenshots/02-shape.png",
            "store/edge/screenshots/03-fill-field.png",
        ],
        "size": [1280, 800],
        "source": "Real packaged popup and public review fixture loaded in Microsoft Edge",
    }
    (OUT / "capture-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    sys.stdout.write(json.dumps(capture(), indent=2) + "\n")
