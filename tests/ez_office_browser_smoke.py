"""Real Chromium smoke: editing, OOXML zip structure, formula results and media persistence."""
from __future__ import annotations
from pathlib import Path
import base64
import json
import tempfile
import zipfile
import wave
from xml.etree import ElementTree as ET
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1] / "docs" / "portfolio" / "ez-office"
PAGE=(ROOT/"index.html").as_uri()
PNG=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg==")


def downloaded(page,button,target,min_bytes=50):
    with page.expect_download() as d:
        page.get_by_role("button", name=button, exact=True).click()
    d.value.save_as(target)
    assert target.stat().st_size>=min_bytes, target
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

def compressed_copy(original, destination):
    """Simulate ordinary compressed Office files (not only EZ-Office's stored ZIP)."""
    with zipfile.ZipFile(original) as z, zipfile.ZipFile(destination,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as out:
        for name in z.namelist():
            out.writestr(name,z.read(name))
    with zipfile.ZipFile(destination) as z:
        assert z.testzip() is None
        assert any(i.compress_type==zipfile.ZIP_DEFLATED for i in z.infolist())


def external_shared_strings_xlsx(target):
    """Common Excel OOXML: compressed ZIP, sharedStrings, workbook relationship, sparse cells."""
    rel_ns="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    main="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel_package="http://schemas.openxmlformats.org/package/2006/relationships"
    workbook=f'<workbook xmlns="{main}" xmlns:r="{rel_ns}"><sheets><sheet name="Inventory" sheetId="1" r:id="rId7"/></sheets></workbook>'
    rels=f'<Relationships xmlns="{rel_package}"><Relationship Id="rId7" Type="{rel_ns}/worksheet" Target="worksheets/inventory.xml"/></Relationships>'
    strings=f'<sst xmlns="{main}"><si><t>Part</t></si><si><r><t>Steel </t></r><r><t>plate</t></r></si></sst>'
    sheet=f'<worksheet xmlns="{main}"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="inlineStr"><is><t>Qty</t></is></c></row><row r="2"><c r="A2" t="s"><v>1</v></c><c r="B2"><v>12</v></c><c r="C2"><f>B2*2</f><v>24</v></c></row></sheetData></worksheet>'
    with zipfile.ZipFile(target,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        z.writestr("xl/workbook.xml",workbook)
        z.writestr("xl/_rels/workbook.xml.rels",rels)
        z.writestr("xl/sharedStrings.xml",strings)
        z.writestr("xl/worksheets/inventory.xml",sheet)


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
            compressed_word=compressed_copy(word,p/"compressed.docx")
            with page.expect_file_chooser() as picker:
                page.get_by_role("button",name="Open DOCX").click()
            picker.value.set_files(str(p/"compressed.docx"))
            expect(writer).to_contain_text("Formatted sample document")
            assert writer.locator("strong,b").count()>=1
            downloaded(page,"Save HTML",p/"document.html")
            with page.expect_file_chooser() as picker:
                page.get_by_role("button",name="Open",exact=True).click()
            picker.value.set_files(str(unsafe))
            assert writer.locator("script").count()==0
            assert writer.locator('[onclick]').count()==0
            assert page.evaluate("window.bad===undefined")
            expect(writer).to_contain_text("Visible heading")
            page.get_by_role("textbox",name="Find text").fill("Safe")
            page.get_by_role("textbox",name="Replacement text").fill("Protected")
            page.get_by_role("button",name="Replace all").click()
            expect(writer).to_contain_text("Protected text")
            assert writer.locator("h2").inner_text()=="Visible heading"
            assert page.evaluate("EZOffice.inspect().dirty")
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
            # Mixed data range: Qty label is text, B2 and B3 are numeric.
            page.get_by_role("textbox",name="B7",exact=True).fill("=SUM(B1:B3)")
            page.get_by_role("textbox",name="C7",exact=True).fill("=COUNT(B1:B3)")
            page.get_by_role("textbox",name="D7",exact=True).fill("=AVERAGE(B1:B3)")
            expect(page.locator('[data-result="6:1"]')).to_have_text("12")
            expect(page.locator('[data-result="6:2"]')).to_have_text("2")
            expect(page.locator('[data-result="6:3"]')).to_have_text("6")
            xlsx=downloaded(page,"Save XLSX",p/"sheet.xlsx")
            content=validate_office(xlsx,["xl/worksheets/sheet1.xml","xl/workbook.xml"])
            assert "<f>A6*2+3</f>" in content["xl/worksheets/sheet1.xml"]
            assert "<v>23</v>" in content["xl/worksheets/sheet1.xml"]
            compressed_copy(xlsx,p/"compressed.xlsx")
            with page.expect_file_chooser() as picker:
                page.get_by_role("button",name="Open XLSX").click()
            picker.value.set_files(str(p/"compressed.xlsx"))
            expect(page.get_by_role("textbox",name="B6",exact=True)).to_have_value("=A6*2+3")
            expect(page.locator('[data-result="5:1"]')).to_have_text("23")
            csv=downloaded(page,"Save CSV",p/"sheet.csv")
            assert "=A6*2+3" in csv.read_text()
            b.fill("=B6")
            expect(result).to_have_text("#CYCLE!")
            # clear cycle before leaving
            b.fill("=A6+5")
            # Sort and filter are view-only; original physical row ids remain correct.
            page.get_by_role("searchbox",name="Filter spreadsheet rows").fill("Fasteners")
            expect(page.locator(".sheet-index-cell")).to_have_count(2)
            expect(page.get_by_role("textbox",name="A3",exact=True)).to_have_value("Fasteners")
            page.evaluate("""() => {
              window.__sheetPrint=null;
              window.print=()=>{
                const page=document.querySelector(".sheet-print-pages");
                window.__sheetPrint={rows:page?.querySelectorAll("tbody tr").length,
                                     headers:page?.querySelectorAll("thead th").length,
                                     text:page?.textContent};
                window.dispatchEvent(new Event("afterprint"));
              };
            }""")
            page.get_by_role("button",name="Print / PDF").click()
            printable=page.evaluate("window.__sheetPrint")
            assert printable["rows"]==1 and printable["headers"]==4,printable
            assert "Fasteners" in printable["text"] and "Sheet metal" not in printable["text"]
            visible_csv=downloaded(page,"Export visible CSV",p/"visible.csv",min_bytes=20)
            assert "Fasteners" in visible_csv.read_text()
            assert "Sheet metal" not in visible_csv.read_text()
            page.get_by_role("button",name="Clear view").click()
            page.get_by_role("combobox",name="Sort view column").select_option("1")
            page.get_by_role("combobox",name="Sort view direction").select_option("desc")
            expect(page.locator(".sheet-index-cell").nth(1)).to_have_text("6")
            page.get_by_role("button",name="Clear view").click()
            page.get_by_role("textbox",name="A9",exact=True).evaluate("""input=>{
                const data=new DataTransfer();
                data.setData("text/plain","Alpha\\t8\\nBeta\\t5");
                input.dispatchEvent(new ClipboardEvent("paste",{clipboardData:data,bubbles:true,cancelable:true}));
            }""")
            expect(page.get_by_role("textbox",name="A9",exact=True)).to_have_value("Alpha")
            expect(page.get_by_role("textbox",name="B10",exact=True)).to_have_value("5")
            page.get_by_role("textbox",name="Go to cell reference").fill("B10")
            page.get_by_role("button",name="Go to cell").click()
            assert page.get_by_role("textbox",name="B10",exact=True).evaluate("(e)=>e===document.activeElement")
            # Import a compressed XLSX with shared strings, sparse cells and a custom sheet path.
            fixture=p/"external.xlsx"
            external_shared_strings_xlsx(fixture)
            with page.expect_file_chooser() as picker:
                page.get_by_role("button",name="Open XLSX").click()
            picker.value.set_files(str(fixture))
            expect(page.get_by_role("textbox",name="A2",exact=True)).to_have_value("Steel plate")
            expect(page.get_by_role("textbox",name="C2",exact=True)).to_have_value("=B2*2")
            expect(page.locator('[data-result="1:2"]')).to_have_text("24")
            page.locator('[data-tool="home"]').click()

            # Slides: image embedded in both native deck and PPTX.
            page.locator('[data-tool="slides"]').click()
            page.get_by_role("textbox",name="Slide title").fill("Revenue overview")
            page.get_by_role("textbox",name="Slide body").fill("Hello slideshow\nSecond line")
            page.get_by_role("combobox",name="Text alignment").select_option("left")
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
            assert "Second line" in content["ppt/slides/slide1.xml"]
            assert 'algn="l"' in content["ppt/slides/slide1.xml"]
            assert content["ppt/slides/slide1.xml"].count("<a:p>")>=3
            with zipfile.ZipFile(slides) as z:
                assert "ppt/media/media1.png" in z.namelist()
                assert z.read("ppt/media/media1.png")==PNG
            expect(page.locator(".slide-thumb")).to_have_count(2)
            page.get_by_role("button",name="Next →").click()
            assert "New slide" in page.locator(".slide-preview").inner_text()
            page.get_by_role("button",name="Select slide 1: Revenue overview").click()
            expect(page.get_by_role("textbox",name="Slide title")).to_have_value("Revenue overview")
            outline=downloaded(page,"Export outline & notes",p/"slides-outline.txt")
            assert "SLIDE 1: Revenue overview" in outline.read_text()
            assert "Presenter notes go here" in outline.read_text()
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
            audio=p/"sound.wav"
            with wave.open(str(audio),"wb") as wav:
                wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(8000)
                wav.writeframes(bytes(16000))
            with page.expect_file_chooser() as picker:
                page.get_by_role("button",name="Open media").click()
            picker.value.set_files(str(audio))
            expect(page.locator(".media-stage audio")).to_have_count(1)
            page.get_by_role("combobox",name="Playback speed").select_option("1.5")
            assert page.locator("audio").evaluate("(e)=>e.playbackRate")==1.5
            page.get_by_role("checkbox",name="Loop playback").check()
            assert page.locator("audio").evaluate("(e)=>e.loop")
            page.locator('[data-tool="home"]').click()

            # Mail: local export, provider OAuth control is real (but no user auth in test).
            page.locator('[data-tool="mail"]').click()
            page.get_by_role("textbox",name="To").fill("person@example.com")
            page.get_by_role("textbox",name="Subject").fill("Hello")
            page.get_by_role("textbox",name="Email body").fill("Real message body")
            mail=downloaded(page,"Download .eml",p/"draft.eml")
            assert "person@example.com" in mail.read_text()
            page.get_by_role("textbox",name="Subject").fill("Changed")
            with page.expect_file_chooser() as picker:
                page.get_by_role("button",name="Open .eml draft").click()
            picker.value.set_files(str(mail))
            expect(page.get_by_role("textbox",name="Subject")).to_have_value("Hello")
            expect(page.get_by_role("textbox",name="Email body")).to_have_value("Real message body")
            assert page.get_by_role("button",name="Connect Gmail").count()==1
            assert page.get_by_role("button",name="Connect Outlook").count()==1
            assert page.get_by_role("button",name="Send via connected account").is_disabled()
            assert not errors,errors
            # No OAuth scripts/API requests unless connection explicitly initiated.
            assert not any(url.startswith(("http://","https://")) for url in requests),requests
            browser.close()



def test_mobile_layout():
    """Check phone viewports across each application without page overflow."""
    with sync_playwright() as play:
        browser=play.chromium.launch(headless=True)
        for width in (390,360):
            page=browser.new_page(viewport={"width":width,"height":844},device_scale_factor=2,is_mobile=True,has_touch=True)
            page.goto(PAGE)
            for app in ("home","writer","sheets","slides","media","mail"):
                page.locator(f'[data-tool="{app}"]').click()
                page.wait_for_function("(name) => EZOffice.inspect().current === name",arg=app)
                if app!="home":
                    page.wait_for_function("document.querySelector('#tool-root .hint')?.textContent?.startsWith('Opening') !== true")
                m=page.evaluate("""() => ({
                    html:document.documentElement.scrollWidth,
                    body:document.body.scrollWidth,
                    width:window.innerWidth,
                    nav:document.querySelector('#app-menu').getBoundingClientRect().width
                })""")
                assert m["html"]<=m["width"]+2,m
                assert m["body"]<=m["width"]+2,m
                assert m["nav"]<=m["width"]+2,m
                assert page.locator(f'[data-tool="{app}"]').is_visible()
                if app=="sheets":
                    grid=page.locator(".grid-wrap")
                    assert grid.evaluate("(e) => e.scrollWidth > e.clientWidth")
                if app=="slides":
                    preview=page.locator(".slide-preview").bounding_box()
                    controls=page.locator(".slide-controls").bounding_box()
                    assert preview and controls and preview["y"] < controls["y"]
            page.close()
        browser.close()


def test_sheet_independent_axes():
    """A finger-scrolled sheet keeps corner, column rail and row rail aligned.
    Test both Chromium and WebKit (the rendering engine used on iOS).
    """
    with sync_playwright() as playwright:
        for browser_type in (playwright.chromium, playwright.webkit):
            browser=browser_type.launch(headless=True)
            page=browser.new_page(viewport={"width":390,"height":844},
                                  device_scale_factor=2,is_mobile=True,has_touch=True)
            errors=[]
            page.on("pageerror",lambda e: errors.append(str(e)))
            page.goto(PAGE)
            page.locator('[data-tool="sheets"]').click()
            expect(page.locator(".sheet-axis-cell")).to_have_count(8)
            expect(page.locator(".sheet-index-cell")).to_have_count(15)
            assert page.get_by_role("button",name="Unfreeze panes").count()==0
            assert page.locator(".sheet tbody th").count()==0

            def measure():
                return page.evaluate("""() => {
                  const frame=document.querySelector(".sheet-frame");
                  const grid=frame.querySelector(".grid-wrap");
                  const corner=frame.querySelector(".sheet-corner");
                  const top=frame.querySelector(".sheet-x-header");
                  const side=frame.querySelector(".sheet-y-header");
                  const a=frame.querySelector(".sheet-axis-cell");
                  const one=frame.querySelector(".sheet-index-cell");
                  const cell=frame.querySelector(".sheet tbody tr:first-child td:first-child");
                  const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height};};
                  return {frame:rect(frame),grid:rect(grid),corner:rect(corner),
                    top:rect(top),side:rect(side),a:rect(a),one:rect(one),
                    cell:rect(cell),scrollX:grid.scrollLeft,scrollY:grid.scrollTop,
                    maxX:grid.scrollWidth-grid.clientWidth,
                    maxY:grid.scrollHeight-grid.clientHeight,
                    snap:getComputedStyle(grid).scrollSnapType,
                    cellPosition:getComputedStyle(cell).position};
                }""")

            first=measure()
            assert abs(first["a"]["x"]-first["cell"]["x"])<=2,first
            assert abs(first["one"]["y"]-first["cell"]["y"])<=2,first
            assert first["maxX"]>=200 and first["maxY"]>=100,first
            assert first["cellPosition"]=="static",first
            assert first["snap"]=="none",first

            page.locator(".grid-wrap").evaluate("""e=>{
                e.scrollLeft=190;
                e.scrollTop=120;
            }""")
            page.wait_for_function("""() => {
                const f=document.querySelector('.sheet-frame');
                const g=f.querySelector('.grid-wrap');
                const a=f.querySelector('.sheet-axis-cell').getBoundingClientRect();
                const first=f.querySelector('tbody tr:first-child td:first-child').getBoundingClientRect();
                const row=f.querySelector('.sheet-index-cell').getBoundingClientRect();
                return g.scrollLeft>150 && g.scrollTop>90 &&
                  Math.abs(a.x-first.x)<1.5 && Math.abs(row.y-first.y)<1.5;
            }""")
            after=measure()
            for name in ("corner","top","side"):
                assert abs(after[name]["x"]-first[name]["x"])<2,(name,first,after)
                assert abs(after[name]["y"]-first[name]["y"])<2,(name,first,after)
            assert abs(after["a"]["x"]-after["cell"]["x"])<2,after
            assert abs(after["one"]["y"]-after["cell"]["y"])<2,after
            assert abs(after["cell"]["x"]-(first["cell"]["x"]-after["scrollX"]))<2,after
            assert abs(after["cell"]["y"]-(first["cell"]["y"]-after["scrollY"]))<2,after
            assert not errors,errors
            browser.close()

if __name__=="__main__":
    test_browser()
    test_mobile_layout()
    test_sheet_independent_axes()
    print("EZ_OFFICE_WORKSHOP_PASS02")
