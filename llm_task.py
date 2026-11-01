#!/usr/bin/env python3
"""Plain words in, checked task file out. Uses the NVIDIA free API.

  export NVIDIA_API_KEY=...        (never paste the key in chat)
  python3 llm_task.py "go to https://shop.com, search for dress, download the photo" task.json

Rules the output must pass (validate_task below):
  - only allowed step types
  - every step has its required fields
  - important steps should carry "alts": other real ways to do that step,
    because variant_planner.py deals those out as the N different paths
  - URLs must be http or https
If the model output fails any rule, the file is rejected, not fixed silently.
Model: set NVIDIA_MODEL, default meta/llama-3.3-70b-instruct.
Endpoint: NVIDIA NIM OpenAI-compatible API (integrate.api.nvidia.com).
"""
import json, os, sys, urllib.request

ALLOWED = {
    "goto": ["url"], "click": ["selector"], "click_text": ["text"],
    "fill": ["selector", "text"], "fill_placeholder": ["placeholder", "text"],
    "press": ["key"], "wait": ["seconds"], "scroll": [],
    "play_media": [], "download": ["selector"], "noop": [], "verify_playing": [],
    "dump_links": [], "click_media": [],
}

def validate_task(task) -> list:
    errors = []
    if not isinstance(task, dict) or not isinstance(task.get("steps"), list) or not task["steps"]:
        return ["task must be an object with a non-empty steps list"]
    def check_step(s, where):
        if not isinstance(s, dict) or s.get("do") not in ALLOWED:
            errors.append(f"{where}: bad or missing step type: {s.get('do') if isinstance(s, dict) else s}")
            return
        for field in ALLOWED[s["do"]]:
            if field not in s:
                errors.append(f"{where}: step '{s['do']}' is missing '{field}'")
        if s["do"] == "goto" and not str(s.get("url", "")).startswith(("http://", "https://")):
            errors.append(f"{where}: goto url must start with http:// or https://")
    for i, step in enumerate(task["steps"]):
        check_step(step, f"step {i+1}")
        for j, alt in enumerate(step.get("alts", [])):
            check_step(alt, f"step {i+1} alt {j+1}")
    return errors

PROMPT = """You convert a plain task into a JSON task file for a web test runner.
Output ONLY JSON, no other text.

Allowed step types and fields:
goto{url}, click{selector}, click_text{text}, fill{selector,text},
fill_placeholder{placeholder,text}, press{key}, wait{seconds}, scroll,
play_media{seconds}, download{selector}

Format: {"name": "...", "steps": [ ... ]}
For every important step, add "alts": a list of 1 to 3 OTHER real steps that
reach the same next state on that site (different link, different search path,
different selector for the same element). Alternatives create different user paths,
so make them real, not copies.

Task: """

def main():
    if len(sys.argv) < 3:
        print("use: llm_task.py \"plain task words\" output_task.json"); sys.exit(2)
    key = os.environ.get("NVIDIA_API_KEY")
    if not key:
        print("NVIDIA_API_KEY is not set. Add the key as an environment secret, not in chat.")
        sys.exit(2)
    body = {
        "model": os.environ.get("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct"),
        "messages": [{"role": "user", "content": PROMPT + sys.argv[1]}],
        "temperature": 0.3, "max_tokens": 2000,
    }
    req = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode())
    text = data["choices"][0]["message"]["content"].strip()
    start, end = text.find("{"), text.rfind("}")
    task = json.loads(text[start:end + 1])
    errors = validate_task(task)
    if errors:
        print("REJECTED, model output failed checks:")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    out = sys.argv[2]
    with open(out, "w") as f:
        json.dump(task, f, indent=2)
    alts = sum(len(s.get("alts", [])) for s in task["steps"])
    print(f"OK: wrote {out} with {len(task['steps'])} steps and {alts} alternatives")

if __name__ == "__main__":
    main()
