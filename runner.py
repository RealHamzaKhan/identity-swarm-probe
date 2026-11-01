#!/usr/bin/env python3
"""Run one user's task in a real Chromium, using that user's plan.

Steps (task.json): goto, click, click_text, fill, fill_placeholder, press,
wait, scroll, play_media, click_media, verify_playing, download,
dump_links (scout: record links, buttons, inputs, media on the page), noop.

Always records, PASS OR FAIL: public IP + geo, timezone matched to that IP,
final URL, page title, page text start, browser fingerprint, screenshot.
A failed run keeps its evidence, so the reason is visible, not guessed.
"""
import argparse, hashlib, json, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from planner import make_plan
from variant_planner import resolve_steps

def fetch_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "identity-swarm/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def get_ip_geo():
    ip = None
    for url, key in [("https://api.ipify.org?format=json", "ip"),
                     ("https://ipinfo.io/json", "ip"),
                     ("https://ifconfig.me/all.json", "ip_addr")]:
        try:
            d = fetch_json(url)
            if d.get(key):
                ip = d[key]; break
        except Exception:
            pass
    geo = {}
    if ip:
        try:
            geo = fetch_json(f"https://ipinfo.io/{ip}/json")
        except Exception:
            pass
    return ip, geo

FINGERPRINT_JS = """() => {
  const c = document.createElement('canvas');
  const ctx = c.getContext('2d');
  ctx.textBaseline = 'top'; ctx.font = '14px Arial';
  ctx.fillText('swarm-fingerprint', 2, 2);
  let webgl = {};
  try {
    const gl = document.createElement('canvas').getContext('webgl');
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    webgl = { vendor: ext ? gl.getParameter(ext.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR),
              renderer: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER) };
  } catch(e) { webgl = { error: String(e) }; }
  return {
    userAgent: navigator.userAgent,
    language: navigator.language,
    languages: navigator.languages,
    platform: navigator.platform,
    webdriver: navigator.webdriver,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    screen: { width: screen.width, height: screen.height },
    canvasHash: c.toDataURL().length + ':' + c.toDataURL().slice(-32),
    webgl: webgl,
    hardwareConcurrency: navigator.hardwareConcurrency,
    deviceMemory: navigator.deviceMemory || null
  };
}"""

DUMP_JS = """() => {
  const links = Array.from(document.querySelectorAll('a[href]')).slice(0, 100).map(a => ({
    hrefAttr: a.getAttribute('href'), text: (a.innerText || '').trim().slice(0, 60),
    id: a.id || null, cls: (a.className && a.className.toString) ? a.className.toString().slice(0, 60) : null }));
  const buttons = Array.from(document.querySelectorAll('button')).slice(0, 40).map(b => ({
    text: (b.innerText || '').trim().slice(0, 40), aria: b.getAttribute('aria-label'),
    testid: b.getAttribute('data-testid'), cls: (b.className || '').toString().slice(0, 50) }));
  const inputs = Array.from(document.querySelectorAll('input')).slice(0, 20).map(i => ({
    placeholder: i.placeholder || null, name: i.name || null, type: i.type,
    testid: i.getAttribute('data-testid') }));
  const media = Array.from(document.querySelectorAll('video, audio')).map(m => ({
    tag: m.tagName, paused: m.paused, t: m.currentTime, ready: m.readyState,
    cls: (m.className || '').toString().slice(0, 60) }));
  return { url: location.href, title: document.title, links, buttons, inputs, media,
           textStart: document.body ? document.body.innerText.slice(0, 400) : '' };
}"""

MEDIA_PROBE = "() => { const v = document.querySelector('video, audio'); return v ? {t: v.currentTime, paused: v.paused, ready: v.readyState} : null; }"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=int, required=True)
    ap.add_argument("--seed", default="demo")
    ap.add_argument("--task", default="task.json")
    ap.add_argument("--no-delay", action="store_true")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    plan = make_plan(args.seed, args.index)
    task = json.loads(Path(args.task).read_text())
    task = dict(task, steps=resolve_steps(task, args.index))
    out = {"index": args.index, "plan": plan, "task_name": task.get("name"),
           "started_utc": datetime.now(timezone.utc).isoformat(),
           "steps_done": [], "checks": [], "dumps": [], "status": "running"}
    out_dir = Path("out"); out_dir.mkdir(exist_ok=True)

    if not args.no_delay and plan["start_delay_s"]:
        time.sleep(plan["start_delay_s"])

    ip, geo = get_ip_geo()
    out["ip"] = ip
    out["geo"] = {k: geo.get(k) for k in ("city", "region", "country", "org", "timezone")}
    tz = geo.get("timezone") or "UTC"
    locale = "en-GB" if (geo.get("country") and geo["country"] != "US") else "en-US"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            version = browser.version
            ua = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  f"(KHTML, like Gecko) Chrome/{version} Safari/537.36")
            ctx = browser.new_context(
                viewport=plan["viewport"],
                device_scale_factor=plan["device_scale_factor"],
                color_scheme=None if plan["color_scheme"] == "no-preference" else plan["color_scheme"],
                timezone_id=tz, locale=locale, user_agent=ua)
            page = ctx.new_page()
            pauses = iter(plan["extra_pauses_s"] * 8)
            step_error = None
            try:
                for step in task["steps"]:
                    do = step["do"]
                    if do == "goto":
                        page.goto(step["url"], wait_until="domcontentloaded", timeout=45000)
                    elif do == "click":
                        el = page.locator(step["selector"]).first
                        box = el.bounding_box()
                        if box:
                            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2,
                                            steps=plan["mouse_steps"])
                        el.click(timeout=20000)
                    elif do == "click_text":
                        el = page.get_by_text(step["text"]).first
                        box = el.bounding_box()
                        if box:
                            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2,
                                            steps=plan["mouse_steps"])
                        el.click(timeout=20000)
                    elif do == "fill":
                        page.locator(step["selector"]).first.type(step["text"], delay=plan["typing_delay_ms"])
                    elif do == "fill_placeholder":
                        page.get_by_placeholder(step["placeholder"]).first.type(
                            step["text"], delay=plan["typing_delay_ms"])
                    elif do == "press":
                        page.keyboard.press(step["key"])
                    elif do == "wait":
                        page.wait_for_timeout(step["seconds"] * 1000 * plan["wait_multiplier"])
                    elif do == "scroll":
                        page.mouse.wheel(0, plan["scroll_px"])
                        page.wait_for_timeout(600 * plan["wait_multiplier"])
                    elif do == "dump_links":
                        try:
                            out["dumps"].append(page.evaluate(DUMP_JS))
                        except Exception as e:
                            out["dumps"].append({"error": str(e)[:200]})
                    elif do == "click_media":
                        el = page.locator("video").first
                        box = el.bounding_box(timeout=15000)
                        if box:
                            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2,
                                            steps=plan["mouse_steps"])
                            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                        page.wait_for_timeout(1500)
                    elif do == "verify_playing":
                        first = page.evaluate(MEDIA_PROBE)
                        if first is None:
                            out["checks"].append({"type": "verify_playing", "ok": False, "reason": "no media element on page"})
                            raise RuntimeError("verify_playing: no media element on page")
                        page.wait_for_timeout(step.get("seconds", 12) * 1000)
                        second = page.evaluate(MEDIA_PROBE)
                        ok = bool(second and second["t"] > first["t"] + 2 and not second["paused"])
                        out["checks"].append({"type": "verify_playing", "ok": ok,
                                              "t_start": first["t"], "t_end": second["t"] if second else None,
                                              "paused_at_end": second["paused"] if second else None})
                        if not ok:
                            raise RuntimeError(f"verify_playing: media time did not advance ({first['t']} to {second['t'] if second else None})")
                    elif do == "play_media":
                        page.evaluate("() => { const m = document.querySelector('video, audio'); if (m) return m.play(); }")
                        page.wait_for_timeout(step.get("seconds", 30) * 1000 * plan["media_wait_multiplier"])
                        page.evaluate("() => { const m = document.querySelector('video, audio'); if (m) m.pause(); }")
                    elif do == "download":
                        with page.expect_download(timeout=30000) as dl:
                            page.locator(step["selector"]).first.click()
                        d = dl.value
                        path = out_dir / d.suggested_filename
                        d.save_as(str(path))
                        data = path.read_bytes()
                        out["download"] = {"name": d.suggested_filename, "bytes": len(data),
                                            "sha256": hashlib.sha256(data).hexdigest()}
                    elif do == "noop":
                        pass
                    else:
                        raise ValueError(f"unknown step: {do}")
                    out["steps_done"].append(do)
                    try:
                        page.wait_for_timeout(next(pauses) * 1000)
                    except StopIteration:
                        pass
            except Exception as e:
                step_error = e
            # Evidence capture: ALWAYS, pass or fail, while the page is alive.
            out["final_url"] = page.url
            try:
                out["final_title"] = page.title()
            except Exception:
                out["final_title"] = None
            try:
                out["page_text_start"] = page.evaluate("() => document.body ? document.body.innerText.slice(0, 600) : ''")
            except Exception:
                out["page_text_start"] = None
            try:
                out["fingerprint"] = page.evaluate(FINGERPRINT_JS)
            except Exception:
                out["fingerprint"] = None
            try:
                page.screenshot(path=str(out_dir / "final.png"), full_page=True)
            except Exception:
                pass
            browser.close()
            if step_error is not None:
                raise step_error
        out["status"] = "passed"
    except Exception as e:
        out["status"] = "failed"
        out["error"] = f"{type(e).__name__}: {e}"[:800]
    out["finished_utc"] = datetime.now(timezone.utc).isoformat()
    (out_dir / "result.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out.get(k) for k in ("index", "ip", "status", "final_url", "error")}, indent=2))
    sys.exit(0 if out["status"] == "passed" else 1)

if __name__ == "__main__":
    main()
