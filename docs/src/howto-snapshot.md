---
title: "How to capture a state snapshot — borescope"
description: "Dump a Juju Kubernetes workload container's Pebble state — services, plan, checks, notices, and recent logs — as a single stable JSON document."
h1: "Capture a state snapshot"
subtitle: "Produce one machine-readable JSON document describing a container's state, for bug reports and tooling."
section: howto
breadcrumb_label: "Capture a state snapshot"
on_this_page:
  - { anchor: "run", label: "Take a snapshot" }
  - { anchor: "shape", label: "What's in it" }
  - { anchor: "errors", label: "Partial snapshots" }
  - { anchor: "uses", label: "What it's for" }
see_also:
  - { label: "Run one command (no REPL)", href: "howto-oneshot.html" }
  - { label: "CLI reference", href: "reference-cli.html" }
---

{#run}
## Take a snapshot

Pass `--snapshot` to dump the container's state as JSON and exit — no REPL:

<pre><code><span class="prompt">$</span> borescope myapp/0 --snapshot</code></pre>

Redirect it to a file to attach to a bug report:

<pre><code><span class="prompt">$</span> borescope myapp/0 --snapshot &gt; myapp-0.json</code></pre>

`--snapshot` works with the same targeting flags as a normal session
(`--container`, `--model`, `--here`, `--socket`), so you can snapshot a specific
workload or run it from inside the charm container.

{#shape}
## What's in it

The output is a single JSON object. Its shape is intended to be **stable and
consumable** by other tools:

```json
{
  "borescope_version": "0.1.0.dev1",
  "captured_at": "2026-05-31T09:14:02.118402+00:00",
  "unit": "myapp/0",
  "container": "myapp",
  "model": "prod",
  "controller": "k8s",
  "system": { "version": "1.19.0" },
  "services": [
    { "name": "myapp", "startup": "enabled", "current": "active" }
  ],
  "plan": { "services": { "myapp": { "command": "/usr/bin/myapp", "override": "replace" } } },
  "checks": [
    { "name": "up", "level": "alive", "status": "up", "failures": 0, "threshold": 3 }
  ],
  "notices": [
    { "id": "1", "type": "custom", "key": "example.com/x", "occurrences": 1, "last_repeated": "…" }
  ],
  "recent_logs": [
    "2026-05-31T09:13:58Z myapp INFO listening on :8080"
  ]
}
```

The top-level keys:

| Key | Contents |
|---|---|
| `borescope_version` | The borescope that produced the snapshot. |
| `captured_at` | UTC ISO-8601 timestamp. |
| `unit`, `container`, `model`, `controller` | The resolved target. |
| `system` | Pebble's reported version. |
| `services` | Each service's name, configured startup, and current status. |
| `plan` | The merged Pebble plan, as a structured object. |
| `checks` | Each health check's level, status, and failure count vs threshold. |
| `notices` | Recent Pebble notices. |
| `recent_logs` | The last 20 log lines, one string per line. |

{#errors}
## Partial snapshots

A snapshot never aborts halfway because one section failed. If borescope can't
collect a section, it omits that key and adds a matching `*_error` key with the
reason — for example `services_error`, `plan_error`, or `logs_error`. So a
snapshot of a half-broken container still captures everything that *did* answer,
which is usually exactly what you want in a bug report.

{#uses}
## What it's for

- **Bug reports.** One file captures the whole picture — far more useful than a
  screenshot of `services`.
- **Diffing.** Snapshot before and after a change and `diff` the JSON.
- **Tooling.** The stable shape is meant to be fed into other tools (for
  example, model-explainers) rather than parsed by eye.

For ad-hoc, human-readable checks, run the individual commands
([`services`](reference-commands.html#pebble-native), `plan`, `checks`, …) or
use [`--command`](howto-oneshot.html) instead.
