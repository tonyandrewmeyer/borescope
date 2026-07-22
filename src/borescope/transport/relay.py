# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Run raw ``pebble`` subcommands over the Juju relay.

A few Pebble CLI features (notably ``logs``) aren't part of the
``ops.pebble.Client`` API surface. Over the Juju relay we drive the workload
container's ``pebble`` binary — always present at ``/charm/bin/pebble`` — via
``juju ssh``/``juju exec``.

Directly-reachable sockets do *not* come through here: they'd need a ``pebble``
binary on the host, which is exactly the requirement
:mod:`borescope.transport.logs` exists to remove.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..discovery import Target


def pebble_relay(target: Target) -> tuple[list[str], dict[str, str] | None, Any]:
    """Return ``(binary_prefix, env, runner)`` for running ``pebble <args>``.

    ``runner`` is a shimmer ``Runner`` (``run``/``popen``); ``binary_prefix`` is the
    argv that names the remote ``pebble`` binary.
    """
    from .cli_transport import _RUNNERS, REMOTE_PEBBLE_BINARY

    # The runner injects the workload socket env itself (via the charm container),
    # so no env is needed here. Pick the runner that matches the target's
    # --via setting so `logs` / `--snapshot` use the same relay as everything else.
    runner_cls = _RUNNERS.get(target.via, _RUNNERS['ssh'])
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
