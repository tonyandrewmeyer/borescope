# Connect to a unit

_Point borescope at exactly the workload container you want to debug._

{#basic}
## The basic case

Give borescope a unit reference (`app/n`):

<pre><code><span class="prompt">$</span> borescope myapp/0</code></pre>

That's all most sessions need. borescope uses your **current** Juju controller
and model, exactly the ones `juju status` would show, and your existing Juju
authority. There's no separate login: if you can `juju ssh myapp/0`, borescope
works; if you can't, it fails the same way.

{#container}
## Choose a container

A charm can declare several workload containers. Without `--container`,
borescope reads the charm's `metadata.yaml` and uses the **first** declared
workload container. To target a specific one:

<pre><code><span class="prompt">$</span> borescope myapp/0 --container=workload</code></pre>

If you name a container the charm doesn't declare, borescope lists the names it
found so you can pick a valid one.

{#model}
## Choose a model

By default borescope talks to your current model. Target another with
`-m`/`--model`:

<pre><code><span class="prompt">$</span> borescope --model prod myapp/0
<span class="prompt">$</span> borescope -m prod myapp/0</code></pre>

The value is passed straight to `juju`, so anything `juju --model` accepts
(including `controller:model` qualifiers) works here too.

{#controller}
## Use a different juju

borescope shells out to whatever `juju` is on your `PATH`. To use a specific
binary (a snap alias, a development build, or a non-standard install), pass
`--juju`:

<pre><code><span class="prompt">$</span> borescope --juju /snap/bin/juju myapp/0</code></pre>

The controller is always the one that `juju` itself considers current; borescope
doesn't switch controllers for you. Switch with `juju switch` first if you need
a different one.

{#what-it-checks}
## What borescope checks

Before dropping you at a prompt, borescope's discovery layer:

1. **Parses** the unit reference and rejects anything that isn't `app/n`.
2. **Confirms** the model is a Kubernetes (CAAS) model. Machine (IAAS) models
   are out of scope (they already have a real shell).
3. **Confirms** the application and unit exist in the model.
4. **Reads** the charm's `metadata.yaml` (falling back to `charmcraft.yaml`)
   from the charm container to find workload container names.
5. **Probes** the container's Pebble to confirm it answers and is new enough to
   support the `--format json` output borescope relies on.

All of this uses only your Juju model access. Never `kubectl`, never
cluster-admin. See [How it reaches Pebble](explanation-transport.html) for the
details.

{#errors}
## Common errors

| Message | Cause |
|---|---|
| `'…' is not a valid unit reference` | The argument wasn't `app/n` (for example `myapp` with no unit number). |
| `… is on a machine (IAAS) model` | The unit is a machine charm. borescope is Kubernetes-only. Use `juju ssh`. |
| `application '…' not found` | No such application in the target model. Check `juju status` and `--model`. |
| `unit '…' not found` | The application exists but not that unit number; borescope lists the units it found. |
| `no workload containers declared` | The charm declares no containers, likely not a sidecar (Kubernetes) charm. |
| `the Pebble in … is too old` | The container's Pebble predates `--format json`. borescope v1 needs a newer Pebble. |

Most failures are the same ones you'd hit with `juju ssh`, surfaced earlier and
with a clearer message.
