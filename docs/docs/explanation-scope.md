# Scope and philosophy

_What borescope deliberately does (and doesn't), and why._

borescope has a small, opinionated surface. The constraints below are choices,
and they're what keep it sharp.

{#k8s-only}
## Kubernetes only

borescope is for **Kubernetes** charms, which run their workloads under Pebble.
Machine (IAAS) charms are explicitly out of scope: they already run on a machine
with a real shell, so `juju ssh` drops you somewhere useful and borescope would
add nothing. Discovery detects a machine model and refuses early, with a message
pointing you back to `juju ssh`.

The whole reason borescope exists is the gap Kubernetes workloads create, a
supervised container with no shell of its own. Where that gap doesn't exist,
neither does borescope's job.

{#minimal}
## A minimal command set

borescope ships a *minimal* set of commands on purpose. The built-ins exist for
two reasons only:

- they need **session state**, paths relative to your current directory; or
- they need the **Pebble files API** to work against a rock with no shell or
  coreutils (`ls`, `cat`, `grep`, …); or
- they expose **Pebble's own operations** that a shell wouldn't have at all
  (`services`, `logs`, `plan`, `checks`, …).

Likewise the [line grammar](reference-commands.html#grammar) is tiny, one
command, at most one pipe, no sequencing or redirection. That covers the
overwhelming majority of debug-shell use at a fraction of the complexity of a
real shell, and keeps each command small and well-tested.

{#exec-first}
## exec over reimplementation

For anything outside that core, the answer is
[`exec`](reference-commands.html#exec), not a new built-in. `exec` runs a binary
that's *already in the container*, so if the rock ships `ps`, `curl`, or the
workload's own CLI, you reach it directly. borescope deliberately does **not**
bundle tools into the container or reimplement a coreutils zoo: that would bloat
the surface, drift from the real tools' behaviour, and still never be complete.

Before any command is added, the question is always: *does `exec <tool>` already
cover this?* Usually it does.

{#grow}
## Growing on request

The guiding principle is **ship a minimal core and grow on request** rather than
speculate. Commands are auto-discovered and self-contained, so adding one when a
real need shows up is a small change, but the default is to wait for that need.
A command earns its place by being something `exec` genuinely can't do well, not
by being conceivably useful.

{#not}
## What borescope is not

- **Not a replacement for `juju ssh`** on machine charms. Those already have a
  shell.
- **Not a `kubectl` wrapper.** It never uses `kubectl` or cluster-admin; it
  works strictly within your Juju authority. See [How it reaches
  Pebble](explanation-transport.html#authority).
- **Not a full shell.** No job control, scripting constructs, or redirection.
  Use [`--command`](howto-oneshot.html) and your real shell around borescope for
  that.
- **Not a config manager.** It's a debugging instrument: look first, change
  deliberately. The Pebble-native write commands (`start`, `stop`, `push`, …)
  are there for fixing things in the moment, not for managing a deployment.
