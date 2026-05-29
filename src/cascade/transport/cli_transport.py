"""CliTransport — the v1 primary backend.

Wraps ``shimmer.PebbleCliClient`` (a drop-in ``ops.pebble.Client`` over the Pebble
CLI) with a :class:`~cascade.transport.runner.JujuSshRunner`. The runner reaches the
workload's Pebble *through the charm container* (which always has a shell and has the
workload's socket mounted), so this works even against shell-less rocks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from .runner import JujuSshRunner

if TYPE_CHECKING:
    from . import Transport

# The charm container's pebble binary (juju-injected; not on $PATH). The per-workload
# socket path is owned by JujuSshRunner (``/charm/containers/<name>/pebble.socket``).
REMOTE_PEBBLE_BINARY = "/charm/bin/pebble"

# Default per-call timeout. Higher than shimmer's local default (5 s) because each
# call pays a ``juju ssh`` round-trip (~0.2 s measured, plus juju client startup).
DEFAULT_TIMEOUT = 30.0


def build_cli_transport(
    *,
    unit: str,
    container: str | None,
    model: str | None = None,
    juju_binary: str = "juju",
    timeout: float = DEFAULT_TIMEOUT,
) -> Transport:
    """Build a CLI-relay transport for *unit*'s *container*."""
    # Imported lazily: shimmer pulls in ops.pebble, which we keep off the
    # --help / --version cold-start path.
    from shimmer import PebbleCliClient

    runner = JujuSshRunner(unit, container, model=model, juju_binary=juju_binary)
    # shimmer's client conforms structurally; cast past the overloaded `exec`
    # signature the type checker can't match against the Transport protocol.
    return cast(
        "Transport",
        PebbleCliClient(
            socket_path=runner.pebble_socket or "",
            pebble_binary=REMOTE_PEBBLE_BINARY,
            runner=runner,
            timeout=timeout,
        ),
    )
