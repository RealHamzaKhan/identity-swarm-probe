#!/usr/bin/env python3
"""Turn one task with alternative steps into N different ways to do it.

How a task offers alternatives:
  a step may carry "alts": a list of other steps that reach the same
  next state. Example: open the search page by typing the search URL,
  or by using the search box, or by clicking the category link.

How variants are picked (mixed radix, no luck involved):
  user number is treated as a number in a mixed base system.
  Step 1 picks by digit 1, step 2 by digit 2, and so on.
  So the first K users are guaranteed all different paths, where
  K = (options of step 1) x (options of step 2) x ...
  After K, paths repeat, but profile and timing plans still differ.

The LLM's job is to write a task with many real alternatives.
This file's job is to deal them out without repeats or collisions.
"""
import json, sys
from pathlib import Path

def options_of(step):
    main = {k: v for k, v in step.items() if k != "alts"}
    return [main] + list(step.get("alts", []))

def total_combinations(task) -> int:
    total = 1
    for step in task["steps"]:
        total *= len(options_of(step))
    return total

def resolve_steps(task, index: int):
    """index is 1-based, like user numbers."""
    n = index - 1
    resolved = []
    for step in task["steps"]:
        opts = options_of(step)
        resolved.append(opts[n % len(opts)])
        n //= len(opts)
    return resolved

def describe(steps) -> str:
    parts = []
    for s in steps:
        d = s["do"]
        if d == "goto":
            parts.append(f"open {s['url']}")
        elif d in ("fill", "fill_placeholder"):
            parts.append(f"type '{s.get('text','')}'")
        elif d in ("click",):
            parts.append(f"click {s.get('selector','')}")
        elif d == "click_text":
            parts.append(f"click text '{s.get('text','')}'")
        elif d == "press":
            parts.append(f"press {s.get('key','')}")
        elif d == "play_media":
            parts.append(f"play media {s.get('seconds',30)}s")
        elif d == "download":
            parts.append(f"download via {s.get('selector','')}")
        else:
            parts.append(d)
    return " -> ".join(parts)

if __name__ == "__main__":
    task = json.loads(Path(sys.argv[1]).read_text())
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    print(f"task: {task.get('name')}")
    print(f"different paths possible: {total_combinations(task)}")
    seen = set()
    for i in range(1, count + 1):
        steps = resolve_steps(task, i)
        key = json.dumps(steps, sort_keys=True)
        seen.add(key)
        print(f"user {i}: {describe(steps)}")
    print(f"unique paths in first {count}: {len(seen)}")
