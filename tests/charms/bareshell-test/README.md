# `bareshell-test`

A sidecar charm whose workload container is **distroless** (no shell, no
standard binaries). Used to exercise cascade against the headline case — a
workload rock you can't `kubectl exec -- sh` into.

The charm boots an otherwise empty distroless container, then pushes a tiny
static `workload-app` Go binary (built from [`workload-src/`](workload-src/))
into `/usr/local/bin/`, adds a Pebble layer with two services (`app` HTTP
server + `ticker` log emitter) and one HTTP check (`app-ready`), and pushes a
couple of sample config + history files. The workload stays shell-less; the
charm just gives cascade something realistic to drive: services to
start/stop/restart, logs to `tail -f`, checks to query, and files to
`cat`/`pull`.

## Build

Requires the Go toolchain and `charmcraft`. From this directory:

```sh
make            # builds src/workload-app and packs bareshell-test_amd64.charm
make binary     # just the Go binary (no charmcraft)
make clean      # remove both build outputs
```

The compiled binary and packed `.charm` are git-ignored; only the source
(`charmcraft.yaml`, `src/charm.py`, `workload-src/*`) is in version control.

## Deploy

```sh
juju deploy ./bareshell-test_amd64.charm bareshell \
    --resource workload-image=gcr.io/distroless/base-debian12
```

Verify it came up with services + check:

```sh
borescope <controller>:<model> bareshell/0 -c services
borescope <controller>:<model> bareshell/0 -c checks
borescope <controller>:<model> bareshell/0 -c "logs -n 5"
```
