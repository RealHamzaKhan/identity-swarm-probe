#!/usr/bin/env python3
"""Convert a Playwright codegen recording into task.json steps.

Record once on your own machine:
  playwright codegen https://example.com     (do the task, close the window)
It saves Python code. Then:
  python3 codegen_to_task.py recording.py task.json

Understood codegen lines:
  page.goto("URL")                          -> goto
  page.locator("SEL").click()               -> click
  page.locator("SEL").fill("TEXT")          -> fill
  page.get_by_text("TEXT").click()          -> click_text
  page.get_by_placeholder("PH").fill("T")   -> fill_placeholder
  page.keyboard.press("KEY")  / page.press  -> press
Anything else is listed in a comment field so nothing is silently lost.
"""
import json, re, sys
from pathlib import Path

PATTERNS = [
    (re.compile(r"""page\.goto\(\s*['"](.+?)['"]\s*\)"""), lambda m: {"do": "goto", "url": m.group(1)}),
    (re.compile(r"""page\.get_by_text\(\s*['"](.+?)['"]\s*\)\.click\("""),
     lambda m: {"do": "click_text", "text": m.group(1)}),
    (re.compile(r"""page\.get_by_placeholder\(\s*['"](.+?)['"]\s*\)\.fill\(\s*['"](.*?)['"]\s*\)"""),
     lambda m: {"do": "fill_placeholder", "placeholder": m.group(1), "text": m.group(2)}),
    (re.compile(r"""page\.locator\(\s*['"](.+?)['"]\s*\)\.click\("""),
     lambda m: {"do": "click", "selector": m.group(1)}),
    (re.compile(r"""page\.locator\(\s*['"](.+?)['"]\s*\)\.fill\(\s*['"](.*?)['"]\s*\)"""),
     lambda m: {"do": "fill", "selector": m.group(1), "text": m.group(2)}),
    (re.compile(r"""page\.keyboard\.press\(\s*['"](.+?)['"]\s*\)"""),
     lambda m: {"do": "press", "key": m.group(1)}),
]

def convert(text: str) -> dict:
    steps, skipped = [], []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        hit = None
        for pat, fn in PATTERNS:
            m = pat.search(line)
            if m:
                hit = fn(m); break
        if hit:
            steps.append(hit)
        elif "page." in line:
            skipped.append(line)
    return {"name": "recorded task", "steps": steps, "not_converted": skipped}

if __name__ == "__main__":
    src = Path(sys.argv[1]).read_text()
    out = convert(src)
    Path(sys.argv[2] if len(sys.argv) > 2 else "task.json").write_text(json.dumps(out, indent=2))
    print(f"steps converted: {len(out['steps'])}, not converted: {len(out['not_converted'])}")
    for s in out["not_converted"]:
        print("  skipped:", s)
