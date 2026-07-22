# How it reaches Pebble

_The trick that makes borescope work against a rock with no shell, and the two ways it connects._

{#problem}
## The problem

A Kubernetes charm runs its workload in a separate container called a
[rock](https://documentation.ubuntu.com/rockcraft/). The rock typically contains
*only* the workload: no shell, no `ls`, no `cat`, sometimes a single static
binary and nothing else. So when something breaks,
`juju ssh --container=workload myapp/0` either fails outright or drops you into
a container where you can't run a single command. The very thing you'd reach
for to debug isn't there.

{#insight}
## The key insight

Every Kubernetes charm workload is supervised by
[Pebble](https://documentation.ubuntu.com/pebble/), and Pebble exposes a
complete API: list and control services, read the plan, follow logs, run health
checks, and, importantly, **read and write files** and **execute processes**
in the container. Anything you'd want a shell for, Pebble can already do for you.

So borescope doesn't need a shell in the rock. It maps familiar commands onto
Pebble's API: `ls` becomes a files-list call, `cat` a files-pull, `exec` a
Pebble exec. The rock can be completely empty and `ls /var/log` still works.

The remaining question is how to *reach* that Pebble. borescope has two
transports for it.

{#mode-b}
## Through the charm container (the default)

The Pebble you care about is the workload's, but the workload container has no
shell to run a client from. The **charm container**, however, always has a
normal filesystem and shell, and Juju mounts the workload's Pebble socket into
it at `/charm/containers/<name>/pebble.socket`.

So borescope's default `CliTransport` does this: `juju ssh` into the *charm*
container (which works, because that container has a shell), and there run the
`pebble` CLI pointed at the workload's mounted socket. It drives that CLI with
[shimmer](https://github.com/tonyandrewmeyer/shimmer), a drop-in
`ops.pebble.Client` that speaks to the Pebble binary instead of an HTTP socket,
so the rest of borescope sees an ordinary `Client`.

This is what lets borescope debug a shell-less rock from your workstation: the
shell it borrows lives in the charm container, not the workload, and the only
access it needs is the `juju ssh` you already have.

{#mode-a}
## Direct to the socket

When the Pebble socket is *directly* reachable, there's no need to go through
Juju at all. `SocketTransport` uses the real `ops.pebble.Client` HTTP API over
the Unix socket. This is the faster path, and borescope uses it when you run:

- `--here`, inside the charm container, against a workload socket mounted at
  `/charm/containers/<name>/pebble.socket`; or
- `--socket PATH`, against any Pebble socket you name (a workload socket, or a
  local Pebble you're running yourself).

This path needs nothing on your machine but the socket itself — no `pebble`
binary, no Juju. That includes [`logs`](reference-commands.html#logs), which
`ops.pebble.Client` doesn't cover: borescope speaks Pebble's `/v1/logs`
endpoint over the socket directly rather than shelling out to a client.

See [Run inside the charm container](howto-here.html) for how to pick this path.

{#relay}
## ssh vs exec relay

When going through Juju (the default mode), borescope can use one of two relays,
chosen with [`--via`](reference-cli.html#transport):

- **`ssh`** (default) streams over `juju ssh`. It's the natural fit for
  interactive use and for following logs, because the connection stays open and
  output streams back live.
- **`exec`** uses request/response `juju exec` instead. It's there for sites
  where `juju ssh` is disabled by policy: each operation is a discrete
  command-and-response rather than a persistent stream.

Both reach the same workload Pebble through the charm container; they differ
only in the Juju mechanism used to get there.

{#authority}
## Authority, not privilege

Notice what borescope never does: it doesn't touch `kubectl`, doesn't read a
kubeconfig, and doesn't need cluster-admin. Every path to the container goes
through Juju (`juju status`, `juju ssh`, `juju exec`), so borescope operates
strictly within the authority Juju already grants you for that model. It can't
reach anything you couldn't reach by hand, and it fails at exactly the same
boundaries. That's a deliberate design choice, not a limitation to work around;
see [Scope and philosophy](explanation-scope.html).
