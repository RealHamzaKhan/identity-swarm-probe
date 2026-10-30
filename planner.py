#!/usr/bin/env python3
"""Make one unique plan per user index.

Same seed + same index = same plan every time (tests stay repeatable).
Different index = different profile and different behaviour.
Only safe things are varied: screen size, colour scheme, timing,
scroll amount, typing speed, mouse path, extra pauses, start delay.
The OS and browser are NOT faked: the runner is a real Linux Chromium,
so the plan never claims to be Windows or a phone.
"""
import json, random, sys

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1680, "height": 1050},
    {"width": 1600, "height": 900},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1280, "height": 720},
    {"width": 1024, "height": 768},
]

def make_plan(seed: str, index: int) -> dict:
    rng = random.Random(f"swarm-{seed}-{index}")
    viewport = rng.choice(VIEWPORTS)
    return {
        "index": index,
        "seed": str(seed),
        "start_delay_s": round(rng.uniform(0, 90), 1),
        "viewport": viewport,
        "device_scale_factor": rng.choice([1, 1, 1, 1.25, 1.5]),
        "color_scheme": rng.choice(["light", "light", "dark", "no-preference"]),
        "typing_delay_ms": rng.randint(40, 150),
        "wait_multiplier": round(rng.uniform(0.7, 1.7), 2),
        "scroll_px": rng.randint(280, 900),
        "mouse_steps": rng.randint(12, 40),
        "extra_pauses_s": [round(rng.uniform(0.3, 2.8), 2) for _ in range(8)],
        "media_wait_multiplier": round(rng.uniform(0.8, 1.6), 2),
    }

if __name__ == "__main__":
    seed = sys.argv[1] if len(sys.argv) > 1 else "demo"
    index = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    print(json.dumps(make_plan(seed, index), indent=2))
