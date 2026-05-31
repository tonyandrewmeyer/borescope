# Inside the charm container with --here

*2026-05-30T00:34:19Z by Showboat 0.6.1*
<!-- showboat-id: 8993f5ec-745e-42db-b8d7-c73ebaf538be -->

<!--
Setup assumed for this demo: same Juju model as `shell-less-rock.md`
(`borescope-dev:shimmer-test`, `bareshell/0`, distroless workload, Pebble 1.31),
but borescope is installed *inside the charm container* so it can talk to the
workload's Pebble socket directly — no `juju ssh` per call.

To get the wheel in:

  uv build
  juju scp dist/borescope-0.1.0.dev0-py3-none-any.whl bareshell/0:/tmp/
  juju ssh bareshell/0 'pip install --break-system-packages /tmp/borescope-0.1.0.dev0-py3-none-any.whl'

The charm container ships python3 + pip (charm-base). `--break-system-packages`
is needed because charm-base has no `ensurepip`. After install, borescope lives
at `/usr/local/bin/borescope` inside `bareshell/0`'s charm container.
-->

**Mode A: `--here`.** When borescope is already inside the charm container it
can skip the `juju ssh` relay entirely and talk to the workload's Pebble
socket through `ops.pebble.Client`. `--here` auto-detects the socket under
`/charm/containers/` and picks the workload (use `--container` to
disambiguate when there's more than one).

In the snippets below the outer `juju ssh bareshell/0 …` just opens a shell
in the charm container; the *borescope* invocation is `borescope --here -c …`
with no Juju args, because borescope is running locally to the socket.

Services and plan (still empty — `bareshell` is a deliberately empty test
charm), but rendered with no per-call `juju ssh` round-trip:

```bash
/home/ubuntu/juju-build/juju ssh -m borescope-dev:shimmer-test bareshell/0 'borescope --here -c services'
```

```output
(no services)
```

```bash
/home/ubuntu/juju-build/juju ssh -m borescope-dev:shimmer-test bareshell/0 'borescope --here -c plan'
```

```output
{}
```

Mode A has the additional perk that file reads work — Mode B's `cat`/`head`/
`tail` currently fail over the CLI relay (see
[shimmer#56](https://github.com/tonyandrewmeyer/shimmer/issues/56): `pebble pull`
stages a temp file on the wrong side of the relay). `--here` streams bytes
straight over the HTTP API. Here's the distroless workload's `/etc/os-release`
— proof that borescope is looking at the *workload's* filesystem, not the charm
container's:

```bash
/home/ubuntu/juju-build/juju ssh -m borescope-dev:shimmer-test bareshell/0 'borescope --here -c "cat /etc/os-release"'
```

```output
PRETTY_NAME="Distroless"
NAME="Debian GNU/Linux"
ID="debian"
VERSION_ID="12"
VERSION="Debian GNU/Linux 12 (bookworm)"
HOME_URL="https://github.com/GoogleContainerTools/distroless"
SUPPORT_URL="https://github.com/GoogleContainerTools/distroless/blob/master/README.md"
BUG_REPORT_URL="https://github.com/GoogleContainerTools/distroless/issues/new"
```

Same `ls /` as the workstation demo — same UX, different transport. Mode A's
big win is that it works against **any** Pebble version (the HTTP API has
always returned JSON), so it sidesteps the "needs a Juju that bundles
Pebble ≥1.31" constraint that Mode B has (Pebble 1.31 is in `latest/stable`
now, but Juju doesn't bundle it yet). The trade-off is that you have to
get borescope into the charm container first.

```bash
/home/ubuntu/juju-build/juju ssh -m borescope-dev:shimmer-test bareshell/0 'borescope --here -c "ls /"'
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
