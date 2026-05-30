"""Run raw ``pebble`` subcommands over the same relay the transport uses.

A few Pebble CLI features (notably ``logs``) aren't part of the
``ops.pebble.Client`` API surface, so they're driven by invoking the ``pebble``
binary directly — remotely via ``juju ssh`` (the CLI relay), or locally against a
reachable socket. Both the ``logs`` command and ``--snapshot`` share this.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..discovery import Target


# Juju injects pebble here in every k8s charm container, but does NOT put it on
# $PATH. So in --here mode `shutil.which("pebble")` finds nothing — fall through
# to this absolute location before giving up.
_JUJU_PEBBLE = "/charm/bin/pebble"


def _local_pebble_binary() -> str:
    """Find the ``pebble`` binary for the local (socket) case.

    Tries ``$PATH`` first (so a dev with a local Pebble install or snap works),
    then the Juju-injected path inside a charm container.
    """
    found = shutil.which("pebble")
    if found:
        return found
    import os

    if os.path.exists(_JUJU_PEBBLE):
        return _JUJU_PEBBLE
    # Fall back to the bare name — subprocess will raise FileNotFoundError, which
    # callers wrap into a clear "logs_error" / similar.
    return "pebble"


def pebble_relay(target: Target) -> tuple[list[str], dict[str, str] | None, Any]:
    """Return ``(binary_prefix, env, runner)`` for running ``pebble <args>``.

    ``runner`` is a shimmer ``Runner`` (``run``/``popen``); ``binary_prefix`` is the
    argv that names the ``pebble`` binary (local ``["pebble"]`` or the remote path).
    """
    if target.socket_path:
        import os

        from shimmer import LocalSubprocessRunner

        env = {**os.environ, "PEBBLE_SOCKET": target.socket_path}
        return [_local_pebble_binary()], env, LocalSubprocessRunner()

    from .cli_transport import _RUNNERS, REMOTE_PEBBLE_BINARY

    # The runner injects the workload socket env itself (via the charm container),
    # so no env is needed here. Pick the runner that matches the target's
    # --via setting so `logs` / `--snapshot` use the same relay as everything else.
    runner_cls = _RUNNERS.get(target.via, _RUNNERS["ssh"])
    runner = runner_cls(
        target.unit,
        target.container,
        model=target.model,
        juju_binary=target.juju_binary,
    )
    return [REMOTE_PEBBLE_BINARY], None, runner


def run_pebble(
    target: Target, pebble_args: list[str], *, timeout: float = 30.0
) -> subprocess.CompletedProcess[Any]:
    """Run ``pebble <pebble_args>`` once and return the completed process."""
    prefix, env, runner = pebble_relay(target)
    return runner.run([*prefix, *pebble_args], env=env, timeout=timeout, check=False)
