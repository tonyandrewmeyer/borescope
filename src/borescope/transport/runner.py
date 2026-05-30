"""shimmer ``Runner``s that reach a workload Pebble *via the charm container*.

The obvious approach — ``juju ssh --container=<workload> <unit> …`` — does **not**
work for borescope's headline case: Juju's k8s ssh ``exec``s ``sh`` inside the target
container, so a shell-less rock fails with ``exec: "sh": not found`` (verified
against a distroless workload). The charm/operator container, however, **always has
a shell** and has every workload's Pebble socket mounted at
``/charm/containers/<name>/pebble.socket``. So borescope lands in the *charm* container
(via ``juju ssh <unit>`` or ``juju exec -u <unit>``) and points ``pebble`` at the
workload's socket. This reaches shell-less rocks *and* stays entirely within the
user's Juju authority (no ``kubectl`` / cluster-admin).

Two runners share that pattern:

- :class:`JujuSshRunner` (default) prefixes ``juju ssh [-m <model>] <unit>``. Best
  for general use; streams stdin/pty so borescope's ``exec`` / ``push`` work.
- :class:`JujuExecRunner` (``--via exec``) prefixes ``juju exec [-m <model>]
  -u <unit> --``. For sites where interactive ssh is disabled but ``juju exec`` is
  allowed. Request/response, so streaming commands (``logs -f``, ``exec`` with stdin)
  may not behave the same.
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from typing import IO, Any


class _JujuRunnerBase:
    """Shared wrap/run/popen plumbing for the two Juju-based runners.

    Subclasses just supply ``_prefix()`` — the leading ``juju ...`` argv that
    reaches the charm container.
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

    def _prefix(self) -> list[str]:
        raise NotImplementedError

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
        """Build the full local argv (juju prefix + env shim + pebble argv)."""
        return [*self._prefix(), *self._remote_env_shim(), *argv]

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
            # borescope's piped-batch command stream (see juju.run_juju).
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


class JujuSshRunner(_JujuRunnerBase):
    """Run a ``pebble`` argv against *container*'s Pebble, via ``juju ssh``.

    No ``--`` separator is used: juju's k8s ssh leaks it into the remote shell. juju
    passes everything after the unit to ``sh -c`` in the (charm) container and does
    not flag-parse it, so the remote pebble's own flags pass through.
    """

    def _prefix(self) -> list[str]:
        cmd = [self.juju_binary, "ssh"]
        if self.model:
            cmd += ["-m", self.model]
        # No --container: land in the charm container (which has a shell) and reach
        # the workload's Pebble through its mounted socket.
        cmd.append(self.unit)
        return cmd


class JujuExecRunner(_JujuRunnerBase):
    """Run a ``pebble`` argv against *container*'s Pebble, via ``juju exec``.

    Useful when interactive ``juju ssh`` is disabled by site policy but ``juju
    exec`` is allowed. Caveat: ``juju exec`` is request/response, not a streaming
    channel — so streaming commands (``logs -f``, ``exec`` with interactive stdin,
    ``push`` from a non-EOF source) may not work the same as over ssh.

    Uses the ``--`` separator (which ``juju exec`` accepts, unlike k8s ssh) so the
    command's own flags don't get parsed by ``juju exec`` itself.
    """

    def _prefix(self) -> list[str]:
        cmd = [self.juju_binary, "exec"]
        if self.model:
            cmd += ["-m", self.model]
        cmd += ["-u", self.unit, "--"]
        return cmd
