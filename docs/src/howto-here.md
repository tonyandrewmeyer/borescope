---
title: "How to run inside the charm container: borescope"
description: "Use borescope from inside a Juju Kubernetes charm container, or against a Pebble socket directly, with --here and --socket."
h1: "Run inside the charm container"
subtitle: "Skip Juju entirely and talk to a mounted Pebble socket directly, from a charm hook, a debug-hooks session, or against any socket path."
section: howto
breadcrumb_label: "Run inside the charm container"
on_this_page:
  - { anchor: "here", label: "Auto-detect with --here" }
  - { anchor: "multiple", label: "Several containers" }
  - { anchor: "socket", label: "Point at a socket" }
  - { anchor: "when", label: "When to use which" }
see_also:
  - { label: "Connect to a unit", href: "howto-connect.html" }
  - { label: "How it reaches Pebble", href: "explanation-transport.html" }
---

When borescope runs *inside* a Juju Kubernetes charm container, it doesn't need
Juju at all. Juju mounts each workload's Pebble socket into the charm container
at `/charm/containers/<name>/pebble.socket`, and borescope can talk to that
socket directly with the real `ops.pebble.Client` API.

{#here}
## Auto-detect with `--here`

From a `juju ssh <unit>` session, a `juju debug-hooks` shell, or charm code,
run:

<pre><code><span class="prompt">$</span> borescope --here</code></pre>

borescope scans `/charm/containers/` for mounted Pebble sockets. If the charm
declares exactly one workload container, it connects to that one. No unit
reference, no model, no Juju round-trip.

{#multiple}
## Several containers

If the charm has more than one workload container, `--here` can't guess which
you mean, so name it:

<pre><code><span class="prompt">$</span> borescope --here --container=workload</code></pre>

If you omit `--container` with multiple containers present, borescope lists the
available names and asks you to choose one.

{#workload-namespace}
## Files you see are the workload's, not the charm container's

When you run `borescope --here` inside the charm container, the prompt's
filesystem commands (`ls`, `cat`, `cp`, `push`, …) see the **workload
container's** filesystem, not the charm container's. That's the whole
point — `--here` talks to the workload's Pebble, which serves the
workload's files.

This bites most often with `/tmp`: a file you write in the charm
container's `/tmp` is invisible to `cat /tmp/whatever` at the borescope
prompt. To poke at a specific local file, push it across first:

<pre><code><span class="prompt">$</span> borescope --here -c "push /charm/scratch.txt /tmp/scratch.txt"
<span class="prompt">$</span> borescope --here -c "cat /tmp/scratch.txt"</code></pre>

The same applies in reverse: `pull /workload/path /charm/path` brings
a file out of the workload into the charm container's filesystem
where you can `juju scp` it back to your workstation.

{#socket}
## Point at a socket

To talk to a Pebble over a specific Unix socket (a workload socket at a
non-standard path, or a local Pebble you're running yourself), pass `--socket`:

<pre><code><span class="prompt">$</span> borescope --socket /charm/containers/workload/pebble.socket
<span class="prompt">$</span> borescope --socket /var/run/pebble.socket</code></pre>

With `--socket`, borescope skips Juju discovery entirely and connects straight
to that socket via the HTTP API. You can still pass a unit reference for
labelling (it's used for the history key and the prompt), but it isn't required.

{#when}
## When to use which

| You are… | Use |
|---|---|
| On your workstation, debugging a remote unit | `borescope myapp/0` (the [default](howto-connect.html)) |
| Inside the charm container already | `borescope --here` |
| Inside, with multiple workloads | `borescope --here --container=<name>` |
| Pointing at a specific or local socket | `borescope --socket <path>` |

`--here` and `--socket` both use the direct socket transport, which is faster
than going through `juju ssh` and works without any Juju access, but only
from somewhere that can see the socket. From your workstation, use a unit
reference instead. See [How it reaches Pebble](explanation-transport.html) for
how the two transports differ.
