# Identity Swarm Probe

Proof test: can GitHub Actions give us many fresh machines with unique public IPs, for free?

## What it does

- One workflow runs 20 jobs in parallel (GitHub Free limit).
- Each job is a fresh virtual machine. It runs `probe.py`.
- `probe.py` records: public IP, country, city, org, timezone, hostname.
- A final `collect` job downloads all 20 results and counts unique IPs.

## Run it

Actions tab > Identity Swarm Probe > Run workflow.

Or with the GitHub CLI:

```
gh workflow run probe.yml
```

## Read the result

Open the finished run. The summary shows total jobs, unique IPs, and any duplicate IPs.
Full data is in the `summary` artifact (summary.json and summary.md).

## Identity Swarm (v1)

The full system on top of the probe.

You choose:
- `users`: 1 to 100
- `seed`: same seed repeats the same plans, new seed makes new plans
- the task, in `task.json`

Each user gets:
- a fresh GitHub Actions machine and its own public IP (probe proved 20 out of 20 unique)
- timezone and language matched to that IP (set at runtime from the IP geo)
- a unique plan from `planner.py`: screen size, colour scheme, start delay (0 to 90 s),
  typing speed, wait speed, scroll amount, mouse path, extra pauses
- a real Chromium run by `runner.py`: steps can goto, click, fill, press, wait,
  scroll, play_media, and download (download name, size and SHA-256 are recorded)

Task steps live in `task.json`. Example step types:
`goto {url}`, `click {selector}`, `fill {selector, text}`, `press {key}`,
`wait {seconds}`, `scroll`, `play_media {seconds}`, `download {selector}`

Run it:

```
gh workflow run swarm.yml -f users=5 -f seed=demo1
```

The `collect` job builds one summary: total users, passed, failed, unique IPs,
unique fingerprints (canvas + user agent + screen + timezone), and unique plans.

Known shared signals in v1 (honest list):
- all IPs are Microsoft Azure data center IPs
- all runners use the same VM image, so WebGL may show a software renderer
- automation flag `navigator.webdriver` is visible
- profiles are fresh each run, so there is no old browsing history
