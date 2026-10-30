#!/usr/bin/env python3
"""Run one user's task in a real Chromium, using that user's plan.

Supported steps in task.json:
  goto {url}            open a page
  click {selector}      click first match (real mouse move first)
  fill {selector,text}  type with the plan's typing delay
  press {key}           keyboard key
  wait {seconds}        wait, scaled by the plan's wait multiplier
  scroll                scroll by the plan's scroll amount
  play_media {seconds}  play first audio/video, wait (scaled), pause
  download {selector}   click and save the download, record name/size/hash

Always records: public IP + geo, timezone matched to that IP,
browser fingerprint as the page sees it, final screenshot, pass/fail.
"""
import argparse, hashlib, json, os, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from planner import make_plan

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=int, required=True)
    ap.add_argument("--seed", default="demo")
    ap.add_argument("--task", default="task.json")
    ap.add_argument("--no-delay", action="store_true", help="skip start delay (local tests)")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    plan = make_plan(args.seed, args.index)
    task = json.loads(Path(args.task).read_text())
    out = {"index": args.index, "plan": plan, "task_name": task.get("name"),
           "started_utc": datetime.now(timezone.utc).isoformat(),
           "steps_done": [], "status": "running"}
    out_dir = Path("out"); out_dir.mkdir(exist_ok=True)

    if not args.no_delay and plan["start_delay_s"]:
        time.sleep(plan["start_delay_s"])

    ip, geo = get_ip_geo()
    out["ip"] = ip
    out["geo"] = {k: geo.get(k) for k in ("city", "region", "country", "org", "timezone")}
    # Timezone and language must match the IP, not fight it.
    tz = geo.get("timezone") or "UTC"
    locale = "en-US"
    if geo.get("country") and geo["country"] != "US":
        locale = "en-GB"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            version = browser.version
            # Same real Chromium version, without the Headless token.
            ua = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  f"(KHTML, like Gecko) Chrome/{version} Safari/537.36")
            ctx = browser.new_context(
                viewport=plan["viewport"],
                device_scale_factor=plan["device_scale_factor"],
                color_scheme=None if plan["color_scheme"] == "no-preference" else plan["color_scheme"],
                timezone_id=tz, locale=locale, user_agent=ua)
            page = ctx.new_page()
            pauses = iter(plan["extra_pauses_s"] * 4)
            for i, step in enumerate(task["steps"]):
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
                elif do == "fill":
                    page.locator(step["selector"]).first.type(step["text"], delay=plan["typing_delay_ms"])
                elif do == "press":
                    page.keyboard.press(step["key"])
                elif do == "wait":
                    page.wait_for_timeout(step["seconds"] * 1000 * plan["wait_multiplier"])
                elif do == "scroll":
                    page.mouse.wheel(0, plan["scroll_px"])
                    page.wait_for_timeout(600 * plan["wait_multiplier"])
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
                else:
                    raise ValueError(f"unknown step: {do}")
                out["steps_done"].append(do)
                page.wait_for_timeout(next(pauses) * 1000)
            out["final_url"] = page.url
            out["final_title"] = page.title()
            out["fingerprint"] = page.evaluate(FINGERPRINT_JS)
            page.screenshot(path=str(out_dir / "final.png"), full_page=True)
            browser.close()
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
