"""Drive the app in headless Chrome at iPhone size and save phone screenshots.

Serves docs/ under /telehealth-access-explorer/ (the same sub-path GitHub Pages uses) so
relative paths are tested, then checks: no JS errors, tapping a state opens the detail
sheet, every tab renders, manifest + service worker work, and the app reloads offline.
Writes images/phone_*.png, images/phone_screens.png and reports/verification.json.

Usage: python scripts/verify_mobile.py [--chrome /usr/bin/google-chrome]
"""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import shutil
import socketserver
import sys
import tempfile
import threading
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
IMAGES, REPORTS = ROOT / "images", ROOT / "reports"
SUBPATH = "telehealth-access-explorer"
TABS = ["map", "state", "compare", "insights", "about"]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve() -> tuple[socketserver.TCPServer, str, Path]:
    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(ROOT / "docs", tmp / SUBPATH)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(tmp)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/{SUBPATH}/", tmp


def combine(paths: list[Path], labels: list[str], out: Path) -> None:
    shots = [Image.open(p).convert("RGB") for p in paths]
    w, h = 390, int(shots[0].height * 390 / shots[0].width)
    shots = [s.resize((w, h), Image.LANCZOS) for s in shots]
    gap, top = 28, 64
    canvas = Image.new("RGB", (len(shots) * (w + gap) + gap, h + top + gap), (233, 239, 241))
    d = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    for i, (s, lab) in enumerate(zip(shots, labels)):
        x = gap + i * (w + gap)
        d.rounded_rectangle([x - 6, top - 6, x + w + 6, top + h + 6], radius=34, fill=(18, 35, 43))
        mask = Image.new("L", s.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=30, fill=255)
        canvas.paste(s, (x, top), mask)
        tw = d.textlength(lab, font=font)
        d.text((x + (w - tw) / 2, 18), lab, fill=(11, 60, 73), font=font)
    canvas.save(out, optimize=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chrome", default="/usr/bin/google-chrome")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    IMAGES.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    httpd, url, tmp = serve()
    errors: list[str] = []
    checks: dict[str, object] = {"url_path": f"/{SUBPATH}/"}
    shots: list[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chrome, headless=True)
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True,
                                  has_touch=True, user_agent=("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
                                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"))
        page = ctx.new_page()
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        aborted: list[str] = []  # fetches cancelled by our own reloads (net::ERR_ABORTED) are not app errors
        page.on("requestfailed", lambda r: (aborted if "ABORTED" in (r.failure or "") else errors).append(
            f"requestfailed: {r.url} ({r.failure})"))
        page.goto(url)
        page.wait_for_selector("body[data-ready='1']", timeout=15000)
        page.evaluate("localStorage.setItem('hintDismissed','1')")  # screenshots without the iOS install hint
        page.evaluate("document.getElementById('installHint').hidden = true")

        # manifest + head tags
        head = page.evaluate("""() => ({
            manifest: document.querySelector('link[rel=manifest]')?.getAttribute('href'),
            apple: document.querySelector('link[rel=apple-touch-icon]')?.getAttribute('href'),
            capable: document.querySelector('meta[name=apple-mobile-web-app-capable]')?.content,
            viewport: document.querySelector('meta[name=viewport]')?.content })""")
        man = page.evaluate("async (h) => (await fetch(h)).json()", head["manifest"])
        icon_ok = all(page.evaluate("async (s) => (await fetch(s)).ok", i["src"]) for i in man["icons"])
        checks["manifest"] = {"name": man["name"], "display": man["display"], "start_url": man["start_url"],
                              "scope": man["scope"], "icons": [i["sizes"] for i in man["icons"]], "icons_load": icon_ok}
        checks["ios_meta"] = head
        checks["apple_touch_icon_loads"] = page.evaluate("async (s) => (await fetch(s)).ok", head["apple"])

        # service worker registered and controlling after reload
        page.evaluate("navigator.serviceWorker.ready.then(() => true)")
        page.reload()
        page.wait_for_selector("body[data-ready='1']")
        checks["service_worker"] = page.evaluate("""async () => { const r = await navigator.serviceWorker.getRegistration();
            return { registered: !!r, scope: r && r.scope, controlling: !!navigator.serviceWorker.controller,
                     cached: (await (await caches.open('tae-v1')).keys()).length }; }""")

        # 1) Map tab
        n_paths = page.locator("#map path.state").count()
        checks["map_states_drawn"] = n_paths
        checks["map_states_colored"] = page.evaluate(
            "[...document.querySelectorAll('#map path.state')].filter(p => p.getAttribute('fill') !== '#d9dfe2').length")
        page.screenshot(path=str(IMAGES / "phone_map.png"))
        shots.append(IMAGES / "phone_map.png")

        # tap Texas on the map -> sheet
        page.locator("#map path[data-code='TX']").tap()
        page.wait_for_selector("#sheet:not([hidden])")
        checks["tap_state_opens_sheet"] = page.locator("#sheetTitle").inner_text()
        page.wait_for_timeout(300)
        page.screenshot(path=str(IMAGES / "phone_map_sheet.png"))
        shots.append(IMAGES / "phone_map_sheet.png")
        page.locator("#sheetDetail").tap()
        page.wait_for_selector("#view-state:not([hidden])")
        checks["sheet_to_state_detail"] = {"hash": page.evaluate("location.hash"),
                                           "picker": page.locator("#statePick").input_value()}

        # 2) State tab (Texas, from the tap) - full-page shot too
        page.wait_for_timeout(200)
        page.screenshot(path=str(IMAGES / "phone_state.png"))
        page.screenshot(path=str(IMAGES / "phone_state_full.png"), full_page=True)
        shots.append(IMAGES / "phone_state.png")
        checks["state_bars"] = page.locator("#view-state .bar-row").count()
        # chart scrub readout
        box = page.locator("#stateTrend svg").bounding_box()
        page.touchscreen.tap(box["x"] + box["width"] * 0.25, box["y"] + box["height"] / 2)
        checks["chart_touch_readout"] = page.locator("#trendReadout").inner_text()

        # quarter selector changes the map
        page.locator(".tabbar button[data-tab='map']").tap()
        before = page.locator("#map path[data-code='CA']").get_attribute("fill")
        page.select_option("#quarter", label="2020 Q2")
        after = page.locator("#map path[data-code='CA']").get_attribute("fill")
        checks["quarter_selector_recolors_map"] = {"before": before, "after_2020_Q2": after, "changed": before != after,
                                                   "caption": page.locator("#mapCaption").inner_text()}
        page.select_option("#quarter", index=len(page.locator("#quarter option").all()) - 1)

        # 3) Compare tab: NY vs National
        page.locator(".tabbar button[data-tab='compare']").tap()
        page.select_option("#cmpA", "NY")
        page.select_option("#cmpB", "US")
        page.wait_for_timeout(200)
        checks["compare_rows"] = page.locator("#cmpTable tbody tr").count()
        page.screenshot(path=str(IMAGES / "phone_compare.png"))
        shots.append(IMAGES / "phone_compare.png")

        # 4) Insights, 5) About
        for tab in ["insights", "about"]:
            page.locator(f".tabbar button[data-tab='{tab}']").tap()
            page.wait_for_selector(f"#view-{tab}:not([hidden])")
            page.wait_for_timeout(150)
            page.screenshot(path=str(IMAGES / f"phone_{tab}.png"))
            shots.append(IMAGES / f"phone_{tab}.png")
        checks["insight_cards"] = page.locator("#insightList .insight").count()
        checks["tabs_rendered"] = page.evaluate(
            "[...document.querySelectorAll('.view')].map(v => [v.dataset.tab, v.innerText.trim().length > 50])")

        # deep link
        page.goto(url + "#compare/CA/MS?q=2024-Q3")
        page.wait_for_selector("body[data-ready='1']")
        checks["deep_link"] = {"tab_visible": page.locator("#view-compare").is_visible(),
                               "quarter": page.locator("#quarter option:checked").inner_text(),
                               "a": page.locator("#cmpA").input_value(), "b": page.locator("#cmpB").input_value()}

        # offline: stop the server, reload from the service worker cache
        ctx.set_offline(True)
        offline_errors_before = len(errors)
        page.goto(url + "#map")
        page.wait_for_selector("body[data-ready='1']", timeout=10000)
        checks["offline_reload"] = {"map_states": page.locator("#map path.state").count(),
                                    "new_errors": errors[offline_errors_before:]}
        ctx.set_offline(False)

        # tap targets in the tab bar
        checks["tabbar_button_min_height_px"] = page.evaluate(
            "Math.min(...[...document.querySelectorAll('.tabbar button')].map(b => b.getBoundingClientRect().height))")
        browser.close()
    httpd.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)

    combine([IMAGES / f"phone_{n}.png" for n in ["map", "map_sheet", "state", "compare", "insights", "about"]],
            ["Map", "Tap a state", "State detail", "Compare", "Insights", "About"], IMAGES / "phone_screens.png")
    checks["js_errors"] = errors
    checks["aborted_requests_ignored"] = aborted
    ok = (not errors and n_paths == 51 and checks["tap_state_opens_sheet"] == "Texas"
          and checks["service_worker"]["controlling"] and checks["offline_reload"]["map_states"] == 51
          and checks["insight_cards"] == 5 and all(r for _, r in checks["tabs_rendered"])
          and checks["quarter_selector_recolors_map"]["changed"] and checks["deep_link"]["a"] == "CA")
    checks["passed"] = ok
    (REPORTS / "verification.json").write_text(json.dumps(checks, indent=2))
    print(json.dumps(checks, indent=2))
    print(f"[verify] {'PASS' if ok else 'FAIL'}; screenshots in {IMAGES.relative_to(ROOT)}/")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
