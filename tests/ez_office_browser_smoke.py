"""Real Chromium smoke: editing, OOXML zip structure, formula results and media persistence."""
from __future__ import annotations
from pathlib import Path
import base64
import json
import tempfile
import zipfile
from xml.etree import ElementTree as ET
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1] / "docs" / "portfolio" / "ez-office"
PAGE=(ROOT/"index.html").as_uri()
PNG=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg==")


def downloaded(page,button,target):
    with page.expect_download() as d:
        page.get_by_role("button", name=button, exact=True).click()
    d.value.save_as(target)
    assert target.stat().st_size>50, target
    return target


def validate_office(path,required):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        names=set(z.namelist())
        assert set(required).issubset(names), (path,names)
        for name in names:
            if name.endswith((".xml",".rels")) or name=="[Content_Types].xml":
                ET.fromstring(z.read(name))
        return {key:z.read(key).decode("utf8") for key in required if key.endswith(".xml")}


def test_browser():
    with tempfile.TemporaryDirectory() as temp:
        p=Path(temp)
        photo=p/"pixel.png";photo.write_bytes(PNG)
        unsafe=p/"unsafe.html"
        unsafe.write_text('<h2>Visible heading</h2><script>window.bad=1</script><p onclick="window.bad=2">Safe text</p>',encoding="utf8")
        with sync_playwright() as play:
            browser=play.chromium.launch(headless=True)
            page=browser.new_page(accept_downloads=True)
            page.on("dialog",lambda d:d.accept())
            errors=[];requests=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            page.on("request",lambda r:requests.append(r.url))
            page.goto(PAGE)
            assert page.evaluate("EZOffice.inspect().registered")==[]
            assert page.evaluate("typeof EZOfficeExport.docx")=="function"

            # Writer: actual formatted OOXML, then safe HTML import.
            page.locator('[data-tool="writer"]').click()
            writer=page.get_by_role("textbox",name="Rich document editor")
            writer.fill("Formatted sample document")
            page.evaluate("""() => {
              const editor=document.querySelector('[aria-label="Rich document editor"]');
              const range=document.createRange();
              range.selectNodeContents(editor.querySelector("p")||editor);
              const sel=window.getSelection();
              sel.removeAllRanges();sel.addRange(range);
            }""")
            page.get_by_role("button",name="Bold",exact=True).click()
            assert "strong" in writer.inner_html().lower() or "<b>" in writer.inner_html().lower(), repr(writer.inner_html())
            word=downloaded(page,"Save DOCX",p/"document.docx")
            contents=validate_office(word,["word/document.xml","word/styles.xml"])
            assert "Formatted sample document" in contents["word/document.xml"]
            assert "<w:b" in contents["word/document.xml"]
            downloaded(page,"Save HTML",p/"document.html")
            with page.expect_file_chooser() as picker:
                page.get_by_role("button",name="Open",exact=True).click()
            picker.value.set_files(str(unsafe))
            assert writer.locator("script").count()==0
            assert writer.locator('[onclick]').count()==0
            assert page.evaluate("window.bad===undefined")
            expect(writer).to_contain_text("Visible heading")
            page.locator('[data-tool="home"]').click()

            # Sheets: dependencies, cell changes, circular errors and XLSX.
            page.locator('[data-tool="sheets"]').click()
            a=page.get_by_role("textbox",name="A6",exact=True)
            b=page.get_by_role("textbox",name="B6",exact=True)
            a.fill("12")
            b.fill("=A6*2+3")
            result=page.locator('[data-result="5:1"]')
            expect(result).to_have_text("27")
            a.fill("10")
            expect(result).to_have_text("23")
            calc=page.locator('[data-result="3:3"]')
            expect(calc).to_have_text("295")
            xlsx=downloaded(page,"Save XLSX",p/"sheet.xlsx")
            content=validate_office(xlsx,["xl/worksheets/sheet1.xml","xl/workbook.xml"])
            assert "<f>A6*2+3</f>" in content["xl/worksheets/sheet1.xml"]
            assert "<v>23</v>" in content["xl/worksheets/sheet1.xml"]
            csv=downloaded(page,"Save CSV",p/"sheet.csv")
            assert "=A6*2+3" in csv.read_text()
            b.fill("=B6")
            expect(result).to_have_text("#CYCLE!")
            # clear cycle before leaving
            b.fill("=A6+5")
            page.locator('[data-tool="home"]').click()

            # Slides: image embedded in both native deck and PPTX.
            page.locator('[data-tool="slides"]').click()
            page.get_by_role("textbox",name="Slide title").fill("Revenue overview")
            page.get_by_role("textbox",name="Slide body").fill("Hello slideshow")
            with page.expect_file_chooser() as picker:
                page.get_by_role("button",name="Insert image / audio / video").click()
            picker.value.set_files(str(photo))
            expect(page.locator(".slide-preview img")).to_have_count(1)
            deck=downloaded(page,"Save deck",p/"show.ezslides")
            data=json.loads(deck.read_text())
            assert data["format"]=="EZSlides-2"
            assert data["slides"][0]["media"]["data"].startswith("data:image/png;base64,")
            slides=downloaded(page,"Save PowerPoint",p/"show.pptx")
            content=validate_office(slides,["ppt/presentation.xml","ppt/slides/slide1.xml","ppt/slides/slide2.xml"])
            assert "Revenue overview" in content["ppt/slides/slide1.xml"]
            with zipfile.ZipFile(slides) as z:
                assert "ppt/media/media1.png" in z.namelist()
                assert z.read("ppt/media/media1.png")==PNG
            page.get_by_role("button",name="Next →").click()
            assert "New slide" in page.locator(".slide-preview").inner_text()
            # Native deck survives reopening.
            with page.expect_file_chooser() as picker:
                page.get_by_role("button",name="Open deck").click()
            picker.value.set_files(str(deck))
            expect(page.locator(".slide-preview img")).to_have_count(1)
            page.locator('[data-tool="home"]').click()

            # Media: export exact bytes and revoke blob URL on closure.
            page.locator('[data-tool="media"]').click()
            with page.expect_file_chooser() as picker:
                page.get_by_role("button",name="Open media").click()
            picker.value.set_files(str(photo))
            expect(page.locator(".media-stage img")).to_have_count(1)
            with page.expect_download() as d:
                page.get_by_role("button",name="Save original").click()
            out=p/"copy.png";d.value.save_as(out)
            assert out.read_bytes()==PNG
            page.locator('[data-tool="home"]').click()

            # Mail: local export, provider OAuth control is real (but no user auth in test).
            page.locator('[data-tool="mail"]').click()
            page.get_by_role("textbox",name="To").fill("person@example.com")
            page.get_by_role("textbox",name="Subject").fill("Hello")
            page.get_by_role("textbox",name="Email body").fill("Real message body")
            mail=downloaded(page,"Download .eml",p/"draft.eml")
            assert "person@example.com" in mail.read_text()
            assert page.get_by_role("button",name="Connect Gmail").count()==1
            assert page.get_by_role("button",name="Connect Outlook").count()==1
            assert page.get_by_role("button",name="Send via connected account").is_disabled()
            assert not errors,errors
            # No OAuth scripts/API requests unless connection explicitly initiated.
            assert not any(url.startswith(("http://","https://")) for url in requests),requests
            browser.close()


if __name__=="__main__":
    test_browser()
    print("EZ_OFFICE_RICH_FORMATS_EXPORT_SMOKE_PASS")
