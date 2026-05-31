---
title: "How borescope works: borescope"
description: "The three layers behind borescope (transport, discovery, and shell) and why they're separated."
h1: "How borescope works"
subtitle: "borescope is three thin, independently-testable layers. Understanding the seams helps you read its behaviour when something goes wrong."
section: explanation
breadcrumb_label: "How borescope works"
on_this_page:
  - { anchor: "layers", label: "Three layers" }
  - { anchor: "transport", label: "Transport" }
  - { anchor: "discovery", label: "Discovery" }
  - { anchor: "shell", label: "Shell" }
  - { anchor: "why", label: "Why the separation" }
see_also:
  - { label: "How it reaches Pebble", href: "explanation-transport.html" }
  - { label: "Scope and philosophy", href: "explanation-scope.html" }
---

{#layers}
## Three layers

borescope is built as three layers, each with a narrow job and a clean seam to
the next:

1. **Transport**: talk to a Pebble.
2. **Discovery**: find the right Pebble.
3. **Shell**: give you a prompt over it.

A session flows top-down: discovery turns your unit reference into a target,
the transport opens a connection to that target's Pebble, and the shell runs a
REPL whose commands call the transport.

{#transport}
## Transport

The transport is the **only** code that touches Pebble. Everything above it
talks to a narrow `Transport` interface, a structural subset of
`ops.pebble.Client` (services, plan, changes, checks, notices, and the files
and exec APIs). There are two backends, both satisfying that interface:

- **`CliTransport`** (the v1 default) drives the workload's `pebble` binary
  through the charm container over `juju ssh`, using
  [shimmer](https://github.com/tonyandrewmeyer/shimmer), a drop-in
  `ops.pebble.Client` implemented over the Pebble CLI.
- **`SocketTransport`** uses the real `ops.pebble.Client` HTTP API directly,
  when the Pebble socket is reachable (inside a charm, or a local Pebble).

Because the shell only ever sees the `Transport` interface, the backend choice
is invisible to it, and a future reimplementation of just this layer (in Go,
say) would sit entirely behind the same seam. [How it reaches
Pebble](explanation-transport.html) covers the backends in detail.

{#discovery}
## Discovery

Discovery turns a unit reference (`myapp/0`), plus optional `--container` and
`--model`, into a fully-resolved target describing exactly which workload
container's Pebble to talk to. It:

- parses and validates the unit reference;
- reads `juju status` to confirm the model is Kubernetes and the unit exists;
- reads the charm's `metadata.yaml` from the charm container to learn the
  workload container names;
- sanity-checks that the chosen container's Pebble answers and is new enough.

Crucially, **everything here uses only your Juju model access** (`juju status`
and `juju ssh` to read metadata). Never `kubectl`, never cluster-admin. borescope
inherits Juju's authority for free: if you can reach the unit with Juju,
discovery succeeds; if you can't, it fails with the same boundary Juju would
enforce.

When borescope runs inside a charm container (`--here`) or against an explicit
socket (`--socket`), discovery short-circuits: there's no unit to resolve, just
a socket to point at.

{#shell}
## Shell

The shell is a small REPL: a line parser, a current-directory and environment
context, path-aware Tab-completion, per-unit history, and a registry of
commands. Commands are auto-discovered, each subclasses a common `Command`
base, declaring its `name`, `summary`, and `usage`, so adding one is a small,
self-contained change with no registration boilerplate.

The command set splits into three groups: shell built-ins (`cd`, `pwd`, …),
file commands implemented over the files API (`ls`, `cat`, `grep`, …), and
Pebble-native commands (`services`, `logs`, `plan`, …). The
[`exec`](reference-commands.html#exec) command is the escape hatch for
everything else. See the [command reference](reference-commands.html).

{#why}
## Why the separation

The layering isn't ceremony. It earns its keep:

- **Testability.** Discovery's argv construction and status parsing are tested
  with mocks, needing no live Juju or cluster. The shell is tested against a
  fake transport. Each layer is exercised in isolation.
- **Authority containment.** Only discovery and the CLI transport invoke
  `juju`; only the transport speaks Pebble. The blast radius of each concern is
  small and obvious.
- **A swappable backend.** Keeping the `Transport` interface narrow means the
  primary backend can change, or be rewritten in another language, without
  the shell noticing.
