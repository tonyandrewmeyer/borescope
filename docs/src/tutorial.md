---
title: "Tutorial: Debug your first container — borescope"
description: "A step-by-step tutorial: install borescope and explore a live Juju Kubernetes workload container — services, logs, files, and the plan."
h1: "Debug your first container"
subtitle: "From install to poking around a live workload container, in about ten minutes. No prior borescope experience required."
section: tutorial
breadcrumb_label: ""
primary_list: on_this_page
on_this_page:
  - { anchor: "overview", label: "Overview" }
  - { anchor: "prerequisites", label: "Prerequisites" }
  - { anchor: "install", label: "Install borescope" }
  - { anchor: "connect", label: "Connect to a unit" }
  - { anchor: "look-around", label: "Look around the filesystem" }
  - { anchor: "services", label: "Inspect services and logs" }
  - { anchor: "plan", label: "Read the plan and checks" }
  - { anchor: "exec", label: "Reach for exec" }
  - { anchor: "leave", label: "Leave the session" }
  - { anchor: "next-steps", label: "Next steps" }
see_also:
  - { label: "Connect to a unit", href: "howto-connect.html" }
  - { label: "Command reference", href: "reference-commands.html" }
---

{#overview}
## Overview

Kubernetes charm workload containers usually run a
[rock](https://documentation.ubuntu.com/rockcraft/) with no shell, so
`juju ssh --container=workload …` drops you nowhere useful. borescope gives you
a prompt that *feels* like `bash` but talks to the container's
[Pebble](https://documentation.ubuntu.com/pebble/) instead.

In this tutorial you'll install borescope, connect to a running unit, and use
it to read the filesystem, inspect services, follow logs, and run a tool that
lives in the container. By the end you'll know your way around a borescope
session.

{#prerequisites}
## Prerequisites

You need:

- A working `juju` CLI, logged in to a controller, with a **Kubernetes** model
  containing at least one deployed application. If `juju ssh <unit>` works for
  you, borescope will too.
- [`uv`](https://docs.astral.sh/uv/) or `pipx` to install borescope.
- A checkout of borescope (v1 isn't on PyPI yet).

If you don't have a charm deployed, any Kubernetes charm will do. For example:

```console
juju add-model tutorial
juju deploy grafana-k8s
juju status --watch 2s        # wait until the unit is active/idle
```

Throughout this tutorial, replace `myapp/0` with your unit (for example
`grafana-k8s/0`).

{#install}
## Install borescope

From your checkout:

<pre><code><span class="prompt">$</span> uv tool install .        <span class="comment"># or: pipx install .</span></code></pre>

Check it's on your `PATH`:

<pre><code><span class="prompt">$</span> borescope --version
borescope 0.1.0.dev1</code></pre>

{#connect}
## Connect to a unit

Point borescope at your unit:

<pre><code><span class="prompt">$</span> borescope myapp/0
pebble:/#</code></pre>

borescope picked up your current Juju controller and model, confirmed the unit
exists, read the charm's metadata to find its workload container, and checked
that the container's Pebble answers. The `pebble:/#` prompt is borescope's, not
a real shell — but it behaves like one. You're in the container's root
directory.

> If the application declares more than one workload container, borescope uses
> the first one declared. Pick a specific one with
> [`--container`](howto-connect.html#container).

{#look-around}
## Look around the filesystem

The familiar commands work, even though the rock has no shell or coreutils —
borescope implements them over Pebble's files API:

<pre><code><span class="prompt">pebble:/#</span> pwd
/
<span class="prompt">pebble:/#</span> ls
bin  etc  usr  var
<span class="prompt">pebble:/#</span> cd /var/log
<span class="prompt">pebble:/var/log#</span> ls -l
-rw-r--r--      1024 2026-05-31 09:14 myapp.log</code></pre>

Tab-completion is path-aware: type `cat /var/lo` and press <kbd>Tab</kbd> to
complete the path. Read a file with `cat`, or peek at the first or last lines
with `head` and `tail`:

<pre><code><span class="prompt">pebble:/var/log#</span> tail -n 20 myapp.log</code></pre>

{#services}
## Inspect services and logs

Pebble's own vocabulary is built in — no `pebble` prefix. List the services
Pebble is supervising:

<pre><code><span class="prompt">pebble:/#</span> services
Service  Startup   Current
myapp    enabled   active</code></pre>

Follow a service's logs the way you would with `tail -f`:

<pre><code><span class="prompt">pebble:/#</span> logs --follow myapp</code></pre>

Press <kbd>Ctrl-C</kbd> to stop following. You can also restrict to the last
*N* lines with `logs -n 50`, and pipe the output through `grep`:

<pre><code><span class="prompt">pebble:/#</span> logs -n 200 myapp | grep error</code></pre>

{#plan}
## Read the plan and checks

The merged Pebble plan tells you how each service is configured to run:

<pre><code><span class="prompt">pebble:/#</span> plan</code></pre>

If the charm defines health checks, list them and their status:

<pre><code><span class="prompt">pebble:/#</span> checks
<span class="prompt">pebble:/#</span> health</code></pre>

When you're chasing a failed deploy, `changes` and `tasks` show what Pebble has
recently done and whether any step errored.

{#exec}
## Reach for exec

borescope ships a deliberately small command set. For anything else, `exec`
runs a binary that's *already in the container*, with your current working
directory:

<pre><code><span class="prompt">pebble:/#</span> exec ps aux
<span class="prompt">pebble:/#</span> exec cat /proc/1/status</code></pre>

If the tool isn't in the rock, `exec` will tell you it can't find it — that's
expected on a minimal image. (See
[Scope and philosophy](explanation-scope.html) for why borescope leans on
`exec` rather than bundling tools.)

{#leave}
## Leave the session

Type `exit` (or press <kbd>Ctrl-D</kbd>):

<pre><code><span class="prompt">pebble:/#</span> exit
<span class="prompt">$</span></code></pre>

{#next-steps}
## Next steps

You've connected to a unit, read its filesystem, inspected services and logs,
and run a container tool. From here:

- [Connect to a unit](howto-connect.html) — choose a container, model, or
  controller explicitly.
- [Run one command (no REPL)](howto-oneshot.html) — use borescope from scripts.
- [Capture a state snapshot](howto-snapshot.html) — dump container state as JSON
  for a bug report.
- [Command reference](reference-commands.html) — the full built-in command set.
