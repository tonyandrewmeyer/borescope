"""A shimmer ``Runner`` that reaches a workload Pebble *via the charm container*.

The obvious approach — ``juju ssh --container=<workload> <unit> …`` — does **not**
work for cascade's headline case: Juju's k8s ssh ``exec``s ``sh`` inside the target
container, so a shell-less rock fails with ``exec: "sh": not found`` (verified
against a distroless workload). The charm/operator container, however, **always has
a shell** and has every workload's Pebble socket mounted at
``/charm/containers/<name>/pebble.socket``. So cascade ``juju ssh <unit>`` (no
``--container`` — landing in the charm container) and points ``pebble`` at the
workload's socket. This reaches shell-less rocks *and* stays entirely within the
user's Juju authority (no ``kubectl`` / cluster-admin).
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from typing import IO, Any


class JujuSshRunner:
    """Run a ``pebble`` argv against *container*'s Pebble, via the charm container.

    Implements shimmer's ``Runner`` protocol (``run`` / ``popen``). Each argv —
    which already starts with the charm container's ``pebble`` binary path, because
    the ``PebbleCliClient`` is configured with ``pebble_binary=/charm/bin/pebble`` —
    is prefixed with ``juju ssh [-m <model>] <unit>`` and an ``env
    PEBBLE_SOCKET=… PEBBLE=…`` shim pointing at the workload container's socket as
    mounted in the charm container.

    No ``--`` separator is used: juju's k8s ssh leaks it into the remote shell. juju
    passes everything after the unit to ``sh -c`` in the (charm) container and does
    not flag-parse it, so the remote pebble's own flags pass through.
    """

    def __init__(
        self,
        unit: str,
        container: str | None,
        *,
        model: str | None = None,
        juju_binary: str = "juju",
    ):
        self.unit = unit
        self.container = container
        self.model = model
        self.juju_binary = juju_binary

    @property
    def pebble_socket(self) -> str | None:
        """The workload's Pebble socket as mounted in the charm container."""
        if not self.container:
            return None
        return f"/charm/containers/{self.container}/pebble.socket"

    def _ssh_prefix(self) -> list[str]:
        cmd = [self.juju_binary, "ssh"]
        if self.model:
            cmd += ["-m", self.model]
        # No --container: land in the charm container (which has a shell) and reach
        # the workload's Pebble through its mounted socket.
        cmd.append(self.unit)
        return cmd

    def _remote_env_shim(self) -> list[str]:
        socket = self.pebble_socket
        if not socket:
            return []
        return [
            "env",
            f"PEBBLE_SOCKET={socket}",
            f"PEBBLE=/charm/containers/{self.container}",
        ]

    def wrap(self, argv: list[str]) -> list[str]:
        """Build the full local ``juju ssh …`` argv for a remote pebble *argv*."""
        return [*self._ssh_prefix(), *self._remote_env_shim(), *argv]

    def run(
        self,
        argv: list[str],
        *,
        input: str | None = None,
        timeout: float | None = None,
        env: Mapping[str, str] | None = None,  # noqa: ARG002 - socket comes from container
        check: bool = True,
    ) -> subprocess.CompletedProcess[Any]:
        return subprocess.run(
            self.wrap(argv),
            input=input,
            # Detach stdin unless we're sending input: otherwise `juju ssh` drains
            # cascade's piped-batch command stream (see juju.run_juju).
            stdin=subprocess.DEVNULL if input is None else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=check,
        )

    def popen(
        self,
        argv: list[str],
        *,
        stdin: int | IO[Any] | None,
        stdout: int | IO[Any] | None,
        stderr: int | IO[Any] | None,
        text: bool,
        env: Mapping[str, str] | None = None,  # noqa: ARG002 - socket comes from container
    ) -> subprocess.Popen[Any]:
        return subprocess.Popen(
            self.wrap(argv),
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            text=text,
        )
