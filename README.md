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
