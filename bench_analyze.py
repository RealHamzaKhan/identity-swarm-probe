#!/usr/bin/env python3
"""Analyse one benchmark run folder (downloaded artifacts).
Prints per site: total, passed, verify_playing ok, unique IPs, failure reasons."""
import json, sys
from pathlib import Path
from collections import Counter

def category(err: str) -> str:
    e = (err or "").lower()
    if "no video element" in e: return "no media element (login wall or no player)"
    if "did not advance" in e: return "media present but not playing"
    if "timeout" in e and "locator" in e: return "element not found in time (layout, wall or block page)"
    if "timeout" in e: return "timeout"
    if "err_" in e or "net::" in e: return "network error"
    if "captcha" in e or "unusual traffic" in e: return "captcha or traffic block"
    return (err or "unknown")[:90]

def main():
    root = Path(sys.argv[1])
    rows = []
    for f in sorted(root.rglob("result.json")):
        if "summary" in str(f):
            continue
        try:
            rows.append(json.loads(f.read_text()))
        except Exception:
            pass
    passed = [r for r in rows if r.get("status") == "passed"]
    vok = sum(1 for r in rows for c in r.get("checks", []) if c.get("type") == "verify_playing" and c.get("ok"))
    ips = [r["ip"] for r in rows if r.get("ip")]
    fails = Counter(category(r.get("error", "")) for r in rows if r.get("status") != "passed")
    print(f"total {len(rows)}  passed {len(passed)}  failed {len(rows)-len(passed)}")
    print(f"verify_playing ok: {vok}")
    print(f"unique IPs: {len(set(ips))}")
    print(f"titles: {Counter((r.get('final_title') or '')[:60] for r in passed)}")
    if fails:
        print("failure reasons:")
        for k, v in fails.items():
            print(f"  {v} x {k}")
    for r in sorted(rows, key=lambda x: x.get("index") or 0):
        chk = [c for c in r.get("checks", []) if c.get("type") == "verify_playing"]
        print(f"  user {r.get('index')}: {r.get('status')} steps={r.get('steps_done')} check={chk} err={str(r.get('error') or '')[:90]}")

if __name__ == "__main__":
    main()
