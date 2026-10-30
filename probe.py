#!/usr/bin/env python3
"""Run on one runner. Record its public IP and basic identity signals."""
import json, os, socket, sys, time, urllib.request
from datetime import datetime, timezone

def fetch_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "identity-swarm-probe/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def main():
    index = os.environ.get("PROBE_INDEX", "local")
    ip = None
    ip_source = None
    # Try several IP sources, first one that works wins
    for url, key in [
        ("https://api.ipify.org?format=json", "ip"),
        ("https://ipinfo.io/json", "ip"),
        ("https://ifconfig.me/all.json", "ip_addr"),
    ]:
        try:
            data = fetch_json(url)
            if data.get(key):
                ip = data[key]
                ip_source = url
                break
        except Exception as e:
            print(f"probe: {url} failed: {e}", file=sys.stderr)
    geo = {}
    if ip:
        try:
            geo = fetch_json(f"https://ipinfo.io/{ip}/json")
        except Exception as e:
            print(f"probe: geo lookup failed: {e}", file=sys.stderr)
    result = {
        "index": str(index),
        "ip": ip,
        "ip_source": ip_source,
        "city": geo.get("city"),
        "region": geo.get("region"),
        "country": geo.get("country"),
        "org": geo.get("org"),
        "ip_timezone": geo.get("timezone"),
        "hostname": socket.gethostname(),
        "runner_name": os.environ.get("RUNNER_NAME"),
        "runner_os": os.environ.get("RUNNER_OS"),
        "system_timezone": time.tzname,
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }
    with open("result.json", "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result, indent=2))
    if not ip:
        print("probe: NO IP FOUND", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
