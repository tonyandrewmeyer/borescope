# A real shell against a shell-less rock

*2026-05-30T00:33:30Z by Showboat 0.6.1*
<!-- showboat-id: e184d6f4-4a61-4970-ac3c-814c18e9195e -->

<!--
Setup assumed for this demo:

  juju bootstrap microk8s borescope-dev
  juju add-model shimmer-test
  juju deploy ./bareshell-test-r1.charm bareshell --resource workload=gcr.io/distroless/base-debian12:latest

`bareshell` is a tiny test charm whose workload container is plain distroless
(no `sh`, no `ls`, no busybox) running Pebble 1.31. borescope is run from this
repo via `uv run borescope`; in production you'd `uv tool install borescope` and
just `borescope bareshell/0`.

Local-only wart: this box runs a custom Juju 4.0.11 build at
`/home/ubuntu/juju-build/juju` (the snap `juju` is 3.6.x and can't talk to a
4.0.x controller), so every borescope invocation here passes
`--juju /home/ubuntu/juju-build/juju`. Drop that flag everywhere on a normal
install.
-->

**The pitch.** Most Juju Kubernetes charms run their workload in a
[distroless rock](https://github.com/canonical/rockcraft) — no shell, no
busybox. When something breaks, `juju ssh --container=workload …` drops you
nowhere useful, because it tries to exec `sh` inside the rock and there's no
`sh` to exec.

Watch `juju ssh` fall over on a distroless workload:

```bash
/home/ubuntu/juju-build/juju ssh -m borescope-dev:shimmer-test --container workload bareshell/0 -- ls / ; true
```

```output
ERROR Internal error occurred: error executing command in container: failed to exec in container: failed to start exec "a432fe02706a4d728857fb3f52759e774b67df2ec5d451b2ac616cc202e61ae8": OCI runtime exec failed: exec failed: unable to start container process: exec: "sh": executable file not found in $PATH: unknown
```

borescope gets in by going through the **charm container** instead (which always
has a shell) and driving the workload's Pebble socket — which Juju mounts at
`/charm/containers/<name>/pebble.socket` on the charm side. Same authority
(`juju ssh`), but useful output:

```bash
uv run borescope --juju /home/ubuntu/juju-build/juju -m borescope-dev:shimmer-test bareshell/0 -c 'ls /'
```

```output
bin
boot
charm
dev
etc
home
lib
lib64
proc
root
run
sbin
sys
tmp
usr
var
```

Pebble's services and plan, the way `pebble services` / `pebble plan` would
render them inside the container. The `bareshell` test charm intentionally
lays down no layer, so both are empty — but borescope still reports cleanly
instead of silently spewing JSON:

```bash
uv run borescope --juju /home/ubuntu/juju-build/juju -m borescope-dev:shimmer-test bareshell/0 -c services
```

```output
(no services)
```

```bash
uv run borescope --juju /home/ubuntu/juju-build/juju -m borescope-dev:shimmer-test bareshell/0 -c plan
```

```output
{}
```

A few commands fall through to `pebble exec` (which delegates to the workload),
so anything that needs a shell still genuinely can't run on a shell-less rock.
The difference is that borescope tells you why, instead of an OCI runtime stack
trace:

```bash
uv run borescope --juju /home/ubuntu/juju-build/juju -m borescope-dev:shimmer-test bareshell/0 -c 'exec sh' ; true
```

```output
error: cannot find executable "sh"
ERROR command terminated with exit code 1
```
