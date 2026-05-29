"""Thin wrappers around the ``juju`` CLI.

cascade never links Juju's Go/Python API libraries; it shells out to the user's
``juju`` client. That keeps cascade inside the user's existing Juju authority — if
they can run ``juju ssh`` to a unit, cascade works; if they can't, it fails the
same way — and needs no ``kubectl`` / cluster-admin access.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from .errors import JujuError

DEFAULT_TIMEOUT = 30.0


def run_juju(
    args: list[str],
    *,
    model: str | None = None,
    juju_binary: str = "juju",
    input: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Run ``juju <args>`` and return stdout, raising :class:`JujuError` on failure.

    *model*, when given, is inserted as ``-m <model>`` immediately after the
    subcommand (``args[0]``), matching how ``juju`` expects the flag.
    """
    cmd = [juju_binary, args[0]]
    if model:
        cmd += ["-m", model]
    cmd += args[1:]
    try:
        result = subprocess.run(
            cmd,
            input=input,
            # Detach stdin unless we're sending input: `juju ssh` forwards our stdin
            # to the remote and would otherwise drain cascade's own piped-batch
            # command stream during discovery, leaving the REPL loop nothing to read.
            stdin=subprocess.DEVNULL if input is None else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
    except FileNotFoundError as exc:
        raise JujuError(
            f"'{juju_binary}' not found on PATH. Install Juju and try again."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise JujuError(f"'{' '.join(cmd)}' timed out after {timeout}s") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise JujuError(
            f"'{' '.join(cmd)}' failed: {stderr or 'unknown error'}",
            returncode=exc.returncode,
            stderr=stderr,
        ) from exc
    return result.stdout


def current_controller_model(
    juju_binary: str = "juju",
) -> tuple[str | None, str | None]:
    """Return ``(controller, model)`` from ``juju switch`` (either may be None)."""
    try:
        out = run_juju(["switch"], juju_binary=juju_binary).strip()
    except JujuError:
        return None, None
    if not out:
        return None, None
    # `juju switch` prints "<controller>:<user>/<model>" (or "<controller>:<model>").
    controller, _, model = out.partition(":")
    return controller or None, (model or None)


def status_json(
    *, model: str | None = None, juju_binary: str = "juju"
) -> dict[str, Any]:
    """Return parsed ``juju status --format=json`` for *model*."""
    out = run_juju(["status", "--format=json"], model=model, juju_binary=juju_binary)
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:
        raise JujuError("could not parse `juju status --format=json` output") from exc
