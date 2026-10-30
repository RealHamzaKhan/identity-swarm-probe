#!/usr/bin/env python3
"""Read all probe result.json files under a folder. Count unique IPs."""
import json, sys
from pathlib import Path
from collections import Counter

def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "artifacts")
    files = sorted(root.rglob("result.json"))
    results = []
    for f in files:
        try:
            results.append(json.loads(f.read_text()))
        except Exception as e:
            print(f"skip {f}: {e}")
    ips = [r.get("ip") for r in results if r.get("ip")]
    counts = Counter(ips)
    dupes = {ip: n for ip, n in counts.items() if n > 1}
    summary = {
        "total_jobs": len(results),
        "jobs_with_ip": len(ips),
        "unique_ips": len(counts),
        "duplicate_ips": dupes,
        "countries": dict(Counter(r.get("country") for r in results if r.get("country"))),
        "orgs": dict(Counter(r.get("org") for r in results if r.get("org"))),
        "results": sorted(results, key=lambda r: str(r.get("index"))),
    }
    Path("summary.json").write_text(json.dumps(summary, indent=2))
    lines = [
        "# Identity Swarm Probe Summary",
        "",
        f"Total jobs: {summary['total_jobs']}",
        f"Jobs with IP: {summary['jobs_with_ip']}",
        f"Unique IPs: {summary['unique_ips']}",
        f"Duplicate IPs: {json.dumps(dupes) if dupes else 'none'}",
        f"Countries: {json.dumps(summary['countries'])}",
        f"Orgs: {json.dumps(summary['orgs'])}",
        "",
        "| # | IP | Country | City | Org |",
        "|---|----|---------|------|-----|",
    ]
    for r in summary["results"]:
        lines.append(f"| {r.get('index')} | {r.get('ip')} | {r.get('country')} | {r.get('city')} | {r.get('org')} |")
    Path("summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
