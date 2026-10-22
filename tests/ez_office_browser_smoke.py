"""Real Chromium smoke through a local HTTP server mimicking GitHub Pages URLs."""
from __future__ import annotations

from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import base64
import tempfile
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1] / "docs"

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4"
    "z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg=="
)


def test_offline_suite() -> None:
    with tempfile.TemporaryDirectory() as temp:
        tempdir = Path(temp)
        picture = tempdir / "tiny.png"
        picture.write_bytes(PNG)
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            partial(SimpleHTTPRequestHandler, directory=str(ROOT)),
        )
        Thread(target=server.serve_forever, daemon=True).start()
        origin = f"http://127.0.0.1:{server.server_port}"
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(accept_downloads=True)
            console_errors = []
            requests = []
            page.on("pageerror", lambda error: console_errors.append(str(error)))
            page.on("request", lambda req: requests.append(req.url))
            page.goto(origin + "/portfolio/")
            page.locator('a[href="ez-office/"]').first.click()
            page.wait_for_url(origin + "/portfolio/ez-office/")
            assert page.title().startswith("EZ-Office")
            initial = page.evaluate("EZOffice.inspect()")
            assert initial["current"] == "home"
            assert initial["registered"] == [], initial
            for app in ["writer", "sheets", "slides", "media", "mail"]:
                assert page.locator(f'[data-tool="{app}"] .glyph').count() == 1

            # Writer: native file save and unload
            page.locator('[data-tool="writer"]').click()
            writer = page.locator('textarea[aria-label="Document editor"]')
            writer.fill("Hello EZ-Office\nhello offline!")
            assert page.evaluate("EZOffice.inspect().registered.includes('writer')")
            assert page.evaluate("EZOffice.inspect().dirty")
            with page.expect_download() as dl:
                page.get_by_role("button", name="Save copy").click()
            saved = dl.value
            assert saved.suggested_filename == "Untitled.txt"
            writer_copy = tempdir / "saved.txt"
            saved.save_as(writer_copy)
            assert writer_copy.read_text() == "Hello EZ-Office\nhello offline!"
            page.locator('[data-tool="home"]').click()
            assert page.locator("textarea").count() == 0
            assert page.evaluate("EZOffice.inspect().current") == "home"

            # CSV: quoted fields, embedded commas and newlines, export.
            page.locator('[data-tool="sheets"]').click()
            page.get_by_role("textbox", name="A1", exact=True).fill('quoted, "value"')
            page.get_by_role("textbox", name="B1", exact=True).fill("00123")
            with page.expect_download() as dl:
                page.get_by_role("button", name="Save CSV").click()
            out = tempdir / "table.csv"
            dl.value.save_as(out)
            assert out.read_text().startswith('"quoted, ""value""",00123,'), out.read_text()[:80]
            # Round-trip the saved copy through the browser file picker
            with page.expect_file_chooser() as chooser:
                page.get_by_role("button", name="Open CSV").click()
            chooser.value.set_files(str(out))
            assert page.get_by_role("textbox", name="A1", exact=True).input_value() == 'quoted, "value"'
            assert page.get_by_role("textbox", name="B1", exact=True).input_value() == "00123"
            page.locator('[data-tool="home"]').click()
            assert page.locator(".sheet").count() == 0

            # Text slideshow and fullscreen controls
            page.locator('[data-tool="slides"]').click()
            page.get_by_role("textbox", name="Slide deck text").fill("Slide One\n---\nSlide Two")
            assert page.locator(".slide-preview").inner_text() == "Slide One"
            page.get_by_role("button", name="Next →").click()
            assert page.locator(".slide-preview").inner_text() == "Slide Two"
            with page.expect_download() as dl:
                page.get_by_role("button", name="Save copy").click()
            assert dl.value.suggested_filename == "Presentation.txt"

            # Media: object URL is revoked when switching tools
            page.locator('[data-tool="media"]').click()
            page.evaluate("""() => {
              window.__revoked = [];
              const original = URL.revokeObjectURL;
              URL.revokeObjectURL = function(value) {
                window.__revoked.push(value);
                return original.call(URL, value);
              };
            }""")
            with page.expect_file_chooser() as chooser:
                page.get_by_role("button", name="Open media").click()
            chooser.value.set_files(str(picture))
            assert page.locator(".media-stage img").count() == 1
            image_url = page.locator(".media-stage img").get_attribute("src")
            assert image_url.startswith("blob:")
            page.locator('[data-tool="home"]').click()
            assert image_url in page.evaluate("window.__revoked")
            assert page.locator(".media-stage").count() == 0

            # Mail exports a real .eml file and does not claim to send.
            page.locator('[data-tool="mail"]').click()
            page.get_by_role("textbox", name="To").fill("friend@example.com")
            page.get_by_role("textbox", name="Subject").fill("Quick hello")
            page.get_by_role("textbox", name="Email body").fill("Testing local mail.")
            with page.expect_download() as dl:
                page.get_by_role("button", name="Download .eml").click()
            eml = tempdir / "draft.eml"
            dl.value.save_as(eml)
            contents = eml.read_text()
            assert "To: friend@example.com" in contents
            assert "Subject: Quick hello" in contents
            assert "Testing local mail." in contents
            assert not console_errors, console_errors
            assert requests, "Browser did not request any local site assets"
            assert all(url.startswith(origin + "/") for url in requests), requests
            browser.close()
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    test_offline_suite()
    print("BEAN_WORKSHOP_EZ_OFFICE_BROWSER_PASS")
