"""SocketTransport — the secondary / opportunistic backend.

Wraps the real ``ops.pebble.Client`` (HTTP API over the unix socket). It is the
fast, structured path, used only when the Pebble socket is *directly* reachable —
borescope running inside the charm, a local Pebble, or once a pushed socket relay
exists. The discovery spike showed the socket is not reachable from a laptop
against a remote cluster without extra plumbing, so for remote use the CLI relay
(:mod:`borescope.transport.cli_transport`) is the default.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from . import Transport

DEFAULT_TIMEOUT = 5.0


def build_socket_transport(
    socket_path: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> Transport:
    """Build a direct-socket transport against the Pebble at *socket_path*."""
    from ops import pebble  # lazy: keep ops off the cold-start path

    return cast("Transport", pebble.Client(socket_path=socket_path, timeout=timeout))
