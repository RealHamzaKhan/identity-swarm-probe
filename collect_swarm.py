#!/usr/bin/env python3
"""Aggregate all swarm result.json files. Count passes and uniqueness."""
import json, sys
from pathlib import Path
from collections import Counter

def fp_key(r):
    fp = r.get("fingerprint") or {}
    plan = r.get("plan") or {}
    vp = plan.get("viewport") or {}
    return "|".join([str(fp.get("canvasHash")), str(fp.get("userAgent")),
                     f"{vp.get('width')}x{vp.get('height')}", str(fp.get("timezone"))])

def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "artifacts")
    results = []
    for f in sorted(root.rglob("result.json")):
        try:
            results.append(json.loads(f.read_text()))
        except Exception as e:
            print(f"skip {f}: {e}")
    ips = [r["ip"] for r in results if r.get("ip")]
    fps = [fp_key(r) for r in results if r.get("fingerprint")]
    plans = [json.dumps(r.get("plan"), sort_keys=True) for r in results if r.get("plan")]
    summary = {
        "total": len(results),
        "passed": sum(1 for r in results if r.get("status") == "passed"),
        "failed": sum(1 for r in results if r.get("status") == "failed"),
        "unique_ips": len(set(ips)),
        "duplicate_ips": {k: v for k, v in Counter(ips).items() if v > 1},
        "unique_fingerprints": len(set(fps)),
        "unique_plans": len(set(plans)),
        "results": sorted(results, key=lambda r: r.get("index") or 0),
    }
    Path("swarm-summary.json").write_text(json.dumps(summary, indent=2))
    L = ["# Swarm Summary", "",
         f"Total users: {summary['total']}",
         f"Passed: {summary['passed']}  Failed: {summary['failed']}",
         f"Unique IPs: {summary['unique_ips']}  Duplicates: {json.dumps(summary['duplicate_ips']) or 'none'}",
         f"Unique fingerprints (canvas+UA+screen+timezone): {summary['unique_fingerprints']}",
         f"Unique behaviour plans: {summary['unique_plans']}", "",
         "| # | Status | IP | City | Timezone | Final URL | Error |",
         "|---|--------|----|------|----------|-----------|-------|"]
    for r in summary["results"]:
        g = r.get("geo") or {}
        fp = r.get("fingerprint") or {}
        L.append(f"| {r.get('index')} | {r.get('status')} | {r.get('ip')} | {g.get('city')} | "
                 f"{fp.get('timezone') or g.get('timezone')} | {r.get('final_url')} | {str(r.get('error') or '')[:80]} |")
    Path("swarm-summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))

if __name__ == "__main__":
    main()
