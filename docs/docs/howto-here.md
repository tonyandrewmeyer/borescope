# Run inside the charm container

_Skip Juju entirely and talk to a mounted Pebble socket directly, from a charm hook, a debug-hooks session, or against any socket path._

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
