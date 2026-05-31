---
title: "CLI reference — borescope"
description: "Complete reference for borescope's command-line arguments, modes, and exit codes."
h1: "CLI reference"
subtitle: "Every command-line argument, the modes they select, and exit codes."
section: reference
breadcrumb_label: "CLI reference"
on_this_page:
  - { anchor: "synopsis", label: "Synopsis" }
  - { anchor: "target", label: "Target arguments" }
  - { anchor: "modes", label: "Mode arguments" }
  - { anchor: "behaviour", label: "Behaviour arguments" }
  - { anchor: "transport", label: "Transport arguments" }
  - { anchor: "meta", label: "Meta" }
  - { anchor: "exit-codes", label: "Exit codes" }
  - { anchor: "environment", label: "Environment" }
see_also:
  - { label: "Command reference", href: "reference-commands.html" }
  - { label: "Connect to a unit", href: "howto-connect.html" }
---

{#synopsis}
## Synopsis

```
borescope [UNIT] [OPTIONS]
```

`UNIT` is a unit reference such as `myapp/0`. It is required unless you pass
`--here` or `--socket`. With no `--command` and an interactive terminal,
borescope opens a REPL; otherwise it runs non-interactively (see
[Behaviour arguments](#behaviour)).

{#target}
## Target arguments

These select *which* workload container borescope talks to.

| Argument | Description |
|---|---|
| `UNIT` | Positional. Unit reference (`app/n`), for example `myapp/0`. Required unless `--here`/`--socket` is given. |
| `--container NAME` | Workload container name. Defaults to the first container declared in the charm's metadata. |
| `-m`, `--model MODEL` | Juju model. Defaults to the current model. Passed through to `juju`. (Short form retained for `juju`-CLI muscle memory.) |
| `--juju PATH` | The `juju` binary to invoke. Default: `juju` (found on `PATH`). |

{#modes}
## Mode arguments

These change *how* borescope finds the Pebble. Without either, borescope
resolves the target through Juju (the default for a remote unit).

| Argument | Description |
|---|---|
| `--here` | Run inside the charm container: auto-detect a workload's mounted Pebble socket under `/charm/containers/`. Use `--container` to choose when there are several. No Juju access needed. |
| `--socket PATH` | Talk directly to a Pebble Unix socket at `PATH`, skipping Juju discovery entirely. |

See [Run inside the charm container](howto-here.html) for when to use each.

{#behaviour}
## Behaviour arguments

These change what borescope *does* once connected.

| Argument | Description |
|---|---|
| `--command CMD` | Run a single command `CMD` and exit, without entering the REPL. |
| `--snapshot` | Dump the container's state as JSON and exit. See [Capture a state snapshot](howto-snapshot.html). |

With neither flag set: if stdin is a terminal, borescope opens the interactive
REPL; if stdin is **not** a terminal, it reads commands line by line from stdin,
runs each, and exits with the status of the last. See
[Run one command (no REPL)](howto-oneshot.html).

{#transport}
## Transport arguments

| Argument | Description |
|---|---|
| `--via {ssh,exec}` | The Juju relay to use when going through Juju (the default mode). `ssh` (default) streams over `juju ssh`; `exec` uses request/response `juju exec`, for sites where `juju ssh` is disabled. Ignored when `--socket`/`--here` is in effect. |

{#meta}
## Meta

| Argument | Description |
|---|---|
| `--version`, `version` | Print the borescope version and exit. |
| `-h`, `--help`, `help` | Print usage and exit. |

`help` and `version` (bare, as the first argument) are Canonical-CLI aliases
for the Python-conventional `--help` / `--version`. borescope accepts both
forms.

`--help` and `--version` are fast: borescope defers its heavier imports until
after argument parsing.

### Verbosity

borescope does **not** implement the Canonical `--quiet` / `--verbose` /
`--verbosity=debug|trace` ladder. The tool's output is the REPL or a single
command's result; a five-level taxonomy adds no value, so v1 stays minimal.
This may change if a concrete need surfaces.

{#exit-codes}
## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success. |
| `1` | A command failed, or discovery/connection failed. The reason is printed to stderr as `borescope: …`. |
| `2` | Usage error — no unit reference and neither `--here` nor `--socket`. |

In non-interactive modes the exit code is that of the command run (or the last
command, when reading from stdin), making borescope safe to use in shell
conditionals and CI.

{#environment}
## Environment

borescope has no environment variables of its own. It inherits the environment
of the `juju` CLI it shells out to — so the controller and model selection,
`JUJU_DATA`, and your Juju credentials are all picked up exactly as `juju`
would use them. If `juju status` and `juju ssh` work in your shell, borescope
works too.
