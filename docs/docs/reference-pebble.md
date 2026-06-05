# Pebble compatibility

_What Pebble versions borescope supports, by transport._

{#supported}
## Supported versions

borescope 1.0 is tested against **Pebble 1.31.0** end-to-end (see the
[`spread.yaml`](https://github.com/tonyandrewmeyer/borescope/blob/main/spread.yaml)
conformance suite, which pins `PEBBLE_VERSION=v1.31.0`). 1.31 is what currently
ships in the `pebble` snap's `latest/stable` channel.

Compatibility across Pebble versions depends on which
[transport](explanation-transport.html) you're using.

{#ssh-shimmer}
## ssh / exec (shimmer) path

The default Juju-relayed transports (`--via ssh`, `--via exec`) drive the
remote `pebble` CLI through
[shimmer](https://github.com/tonyandrewmeyer/shimmer). They require
**Pebble ≥ 1.31** in the charm container, because shimmer relies on CLI
surface and JSON output shapes that stabilised in that release.

If a Juju version you're using ships an older Pebble in its charm-container
sidecar, the ssh/exec path will not work reliably — fall back to the direct
socket path below, or upgrade the charm to a base that ships a current Pebble.

{#socket}
## Direct socket path

`--here` and `--socket PATH` talk to Pebble over its HTTP-on-Unix-socket
API using the real `ops.pebble.Client`. This path doesn't go through the
CLI at all, so it isn't bound to the shimmer compatibility floor.

In principle older Pebbles work here too, going back as far as the
`ops.pebble.Client` surface borescope relies on. **In practice we currently
only test against Pebble 1.31.0**; older versions are unverified for 1.0.
Automated multi-version coverage is tracked in
[issue #28](https://github.com/tonyandrewmeyer/borescope/issues/28) — if
you hit a regression on an older Pebble, please file it with the exact
version.

{#checking}
## Checking what you have

Inside a charm container, `pebble version --client` reports the bundled
Pebble. From a borescope session, `pebble version` (Pebble's own command,
exposed as a built-in) prints the server version of whatever Pebble you're
currently connected to.
