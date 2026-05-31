# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

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

Both runners also implement shimmer's ``FileTransferRunner`` protocol so that
``push`` / ``pull`` (and the commands built on them: ``cat``, ``head``, ``tail``,
``grep <file>``) stage temp files via ``juju scp`` in the charm container,
rather than on the local filesystem (where the remote ``pebble`` can't reach
them).
"""

from __future__ import annotations

import base64
import shlex
import subprocess
import uuid
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
        juju_binary: str = 'juju',
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
        return f'/charm/containers/{self.container}/pebble.socket'

    def _prefix(self) -> list[str]:
        raise NotImplementedError

    def _remote_env_shim(self) -> list[str]:
        socket = self.pebble_socket
        if not socket:
            return []
        return [
            'env',
            f'PEBBLE_SOCKET={socket}',
            f'PEBBLE=/charm/containers/{self.container}',
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
        env: Mapping[str, str] | None = None,
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
        env: Mapping[str, str] | None = None,
    ) -> subprocess.Popen[Any]:
        return subprocess.Popen(
            self.wrap(argv),
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            text=text,
        )

    # ------------------------------------------------------------------
    # shimmer ``FileTransferRunner`` protocol — stage temp files for
    # ``PebbleCliClient.push`` and ``pull`` on the charm container's
    # filesystem (where the remote ``pebble`` can actually reach them)
    # rather than on the local workstation.
    #
    # Implementation note: ``juju scp`` would be the obvious choice but it
    # lands files as the ``ubuntu`` user, and Pebble (running as root) refuses
    # to ``open(2)`` a file owned by a different user — even with 0666
    # permission bits — for both ``pull`` (write) and ``push`` (read). So we
    # instead pipe base64-encoded bytes through the runner's own juju channel,
    # which executes as root: that lands the file as root, dodges Pebble's
    # owner check, and crucially works the same under ``juju ssh`` and
    # ``juju exec`` (no second auth bit required, no scp transport).
    # base64 also avoids any line-ending or charset mangling on binary
    # content over the (text-mode) ssh channel.

    def _juju_argv_no_pebble(self, *args: str) -> list[str]:
        """Build a juju argv for a non-pebble command in the charm container."""
        return [*self._prefix(), *args]

    def upload_temp(self, content: bytes) -> str:
        # /tmp here is the REMOTE charm container's /tmp, not the workstation's
        # — single-tenant, short-lived k8s pod, so the usual /tmp predictability
        # concerns don't apply; uuid4 suffix is just belt-and-braces.
        remote_path = f'/tmp/cascade-upload-{uuid.uuid4().hex}'  # noqa: S108
        encoded = base64.b64encode(content).decode('ascii')
        # `sh -c 'echo … | base64 -d > <path>'`: the runner's _prefix() handles
        # the juju framing; the inner `sh -c` makes the redirect work under
        # both runners (juju exec doesn't wrap argv in a shell the way k8s
        # juju ssh does).
        inner = f'echo {encoded} | base64 -d > {remote_path}'
        result = subprocess.run(
            self._juju_argv_no_pebble('sh', '-c', inner),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='replace')
            raise RuntimeError(f'upload_temp: staging {remote_path} failed: {stderr.strip()}')
        return remote_path

    def download_temp(self, path: str) -> bytes:
        # base64 the file on the remote side so binary content survives the
        # text-mode juju channel intact. Output goes to stdout, which works
        # the same under both ssh and exec.
        result = subprocess.run(
            self._juju_argv_no_pebble('base64', path),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='replace')
            raise RuntimeError(f'download_temp: reading {path} failed: {stderr.strip()}')
        return base64.b64decode(result.stdout)

    def cleanup_temp(self, path: str) -> None:
        # Best-effort: a stale /tmp/cascade-upload-<hex> isn't worth raising on.
        subprocess.run(
            self._juju_argv_no_pebble('rm', '-f', path),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
        )


class JujuSshRunner(_JujuRunnerBase):
    """Run a ``pebble`` argv against *container*'s Pebble, via ``juju ssh``.

    No ``--`` separator is used: juju's k8s ssh leaks it into the remote shell. juju
    passes everything after the unit to ``sh -c`` in the (charm) container and does
    not flag-parse it, so the remote pebble's own flags pass through.
    """

    def _prefix(self) -> list[str]:
        cmd = [self.juju_binary, 'ssh']
        if self.model:
            cmd += ['-m', self.model]
        # No --container: land in the charm container (which has a shell) and reach
        # the workload's Pebble through its mounted socket.
        cmd.append(self.unit)
        return cmd

    def wrap(self, argv: list[str]) -> list[str]:
        """Build the juju ssh argv with each tail token shell-quoted.

        juju's k8s ssh joins everything after the unit with spaces and runs
        the result through ``sh -c``, so shell metacharacters in argv get
        reinterpreted by the *outer* shell (e.g. ``pebble exec -- sh -c 'echo
        a; echo b'`` would have its ``;`` split before reaching the inner
        ``sh``). shlex-quote each piece so it survives the join; tokens with
        no metacharacters are returned unchanged.
        """
        full = [*self._remote_env_shim(), *argv]
        return [*self._prefix(), *(shlex.quote(a) for a in full)]


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
        cmd = [self.juju_binary, 'exec']
        if self.model:
            cmd += ['-m', self.model]
        cmd += ['-u', self.unit, '--']
        return cmd
