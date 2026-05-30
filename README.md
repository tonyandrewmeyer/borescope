# borescope

A natural shell for debugging Juju Kubernetes **workload** containers.

Kubernetes charm workload containers usually run a [rock](https://documentation.ubuntu.com/rockcraft/)
with no shell — so when something breaks, `juju ssh --container=workload …` drops
you nowhere useful. borescope gives you a prompt that *feels* like `bash` but talks to
the container's [Pebble](https://github.com/canonical/pebble) instead of a real shell:

```console
$ borescope myapp/0
pebble:/# ls /var/log/myapp
pebble:/# tail -f /var/log/myapp/error.log
pebble:/# services
pebble:/# logs --follow myapp
pebble:/# plan
pebble:/# exit
```

No setup ceremony: borescope picks up your current Juju controller/model and uses your
existing `juju` authority — if you can `juju ssh` to the unit, borescope works; if you
can't, it fails the same way.

## Install

> v1 is under active development. For now, from a checkout:

```console
uv tool install .        # or: pipx install .
```

## Usage

```console
borescope <unit>                       # default (first) workload container
borescope <unit> --container=<name>    # a specific workload container
borescope --model <model> <unit>
borescope <unit> --command "services"  # one-shot, no REPL (for scripts)
borescope <unit> --snapshot            # dump container state as JSON
```

## How it works

borescope is three thin, independently-testable layers:

- **Transport** — talks to a Pebble. The primary backend (`CliTransport`) reaches the
  workload's Pebble *through the charm container* — `juju ssh <unit>` (the charm
  container always has a shell) pointed at the workload's socket, which Juju mounts
  there at `/charm/containers/<name>/pebble.socket`. This works even against rocks
  with **no shell** (the shell lives in the charm container, not the rock) and stays
  entirely within your Juju authority — no `kubectl` or cluster-admin. It drives
  `pebble` via [shimmer](https://github.com/tonyandrewmeyer/shimmer) (a drop-in
  `ops.pebble.Client` over the Pebble CLI). When the Pebble socket is directly
  reachable (running inside the charm, or a local Pebble), `SocketTransport` uses the
  real `ops.pebble.Client` HTTP API instead.
- **Discovery** — turns a unit reference into the right Pebble: confirms the unit,
  reads the charm's `metadata.yaml` for workload container names, and sanity-checks
  the container is alive. Everything uses your Juju model access — no `kubectl` /
  cluster-admin.
- **Shell** — a small REPL: `cd`/`pwd`, path-aware tab completion, history, and a
  minimal command set. Pebble's own vocabulary (`services`, `logs`, `plan`, …) is
  first-class, not hidden behind a `pebble` prefix. For anything else, `exec <cmd>`
  runs a binary that's already in the container.

## Scope

borescope is for **Kubernetes** charms (which run Pebble). Machine charms already have
a real shell and are out of scope. It deliberately ships a *minimal* command set and
grows on request — if a tool exists in the container, reach it with `exec`.

## License

Apache-2.0. See [LICENSE](LICENSE).
