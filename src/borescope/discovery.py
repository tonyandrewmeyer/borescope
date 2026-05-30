# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Discovery layer (B) — "find the right Pebble".

Turns a unit reference (``myapp/0``) plus optional ``--container`` / ``--model``
into a :class:`Target` describing exactly which workload container's Pebble to talk
to. Everything here uses only the user's Juju model access (``juju status``,
``juju ssh`` to read the charm's ``metadata.yaml``) — never ``kubectl`` or
cluster-admin — so borescope inherits Juju's authority for free.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import yaml

from . import juju
from .errors import DiscoveryError, JujuError

if TYPE_CHECKING:
    from .transport import Transport

_UNIT_RE = re.compile(r'^(?P<app>[a-z0-9][a-z0-9-]*)/(?P<num>\d+)$')

# Charm agent metadata lives at a deterministic path inside the *charm* container
# (which, unlike the workload rock, has a normal filesystem and `cat`).
_META_FILES = ('metadata.yaml', 'charmcraft.yaml')

# Inside a Juju k8s charm container, each declared workload's Pebble socket is
# mounted here, one subdirectory per container. This is what makes Mode A
# (``--here``) possible without any Juju round-trip.
_LOCAL_SOCKET_DIR = '/charm/containers'


@dataclass(frozen=True)
class Target:
    """A fully-resolved Pebble target."""

    unit: str
    app: str
    container: str | None
    model: str | None
    controller: str | None = None
    juju_binary: str = 'juju'
    socket_path: str | None = None
    # CLI-relay variant for Mode B: "ssh" (default) or "exec". Ignored when
    # socket_path is set (Mode A uses the socket directly).
    via: str = 'ssh'

    @property
    def history_key(self) -> str:
        """Stable per-controller/model/unit key for history files."""
        parts = [self.controller or '_', self.model or '_', self.unit]
        return '/'.join(parts).replace('/', '_')


def parse_unit_ref(ref: str) -> tuple[str, str]:
    """Split ``app/n`` into ``(app, n)``; raise :class:`DiscoveryError` if malformed."""
    match = _UNIT_RE.match(ref.strip())
    if not match:
        raise DiscoveryError(f"'{ref}' is not a valid unit reference (expected e.g. 'myapp/0').")
    return match.group('app'), match.group('num')


def _agent_dir(app: str, num: str) -> str:
    return f'unit-{app}-{num}'


def discover_containers(
    unit: str, app: str, num: str, *, model: str | None, juju_binary: str
) -> list[str]:
    """Return the workload container names declared in the charm's metadata.

    Reads the charm's ``metadata.yaml`` (falling back to ``charmcraft.yaml``) from
    the charm container — ``juju status`` does not list workload container names.
    """
    base = f'/var/lib/juju/agents/{_agent_dir(app, num)}/charm'
    last_error: JujuError | None = None
    for name in _META_FILES:
        try:
            raw = juju.run_juju(
                # No ``--`` separator: juju's k8s ssh leaks it into the remote sh.
                ['ssh', unit, 'cat', f'{base}/{name}'],
                model=model,
                juju_binary=juju_binary,
            )
        except JujuError as exc:
            last_error = exc
            continue
        try:
            meta = yaml.safe_load(raw) or {}
        except yaml.YAMLError:
            continue
        containers = meta.get('containers')
        if isinstance(containers, dict):
            return [str(name) for name in containers]
    if last_error is not None:
        raise DiscoveryError(
            f'could not read charm metadata for {unit}: {last_error}'
        ) from last_error
    return []


def resolve_target(
    unit_ref: str,
    *,
    container: str | None = None,
    model: str | None = None,
    juju_binary: str = 'juju',
    via: str = 'ssh',
) -> Target:
    """Resolve *unit_ref* to a :class:`Target`, confirming it exists and is on k8s."""
    app, num = parse_unit_ref(unit_ref)
    controller, current_model = juju.current_controller_model(juju_binary)
    effective_model = model or current_model

    status = juju.status_json(model=model, juju_binary=juju_binary)

    model_type = (status.get('model') or {}).get('type')
    if model_type == 'iaas':
        raise DiscoveryError(
            f'{unit_ref} is on a machine (IAAS) model. borescope only supports '
            'Kubernetes charms, which run Pebble; machine charms already have a '
            'real shell. See the project scope.'
        )

    apps = status.get('applications') or {}
    if app not in apps:
        raise DiscoveryError(
            f"application '{app}' not found in model '{effective_model or '<current>'}'."
        )
    units = apps[app].get('units') or {}
    if unit_ref not in units:
        available = ', '.join(sorted(units)) or 'none'
        raise DiscoveryError(f"unit '{unit_ref}' not found. Units of '{app}': {available}.")

    chosen = container
    if chosen is None:
        containers = discover_containers(unit_ref, app, num, model=model, juju_binary=juju_binary)
        if not containers:
            raise DiscoveryError(
                f"no workload containers declared by '{app}'. Is this a "
                'Kubernetes (sidecar) charm?'
            )
        # Default to the first declared workload container (open question #5).
        chosen = containers[0]

    return Target(
        unit=unit_ref,
        app=app,
        container=chosen,
        model=effective_model,
        controller=controller,
        juju_binary=juju_binary,
        via=via,
    )


def discover_local_sockets(base: str = _LOCAL_SOCKET_DIR) -> dict[str, str]:
    """Map workload container name → mounted Pebble socket path.

    As seen from *inside the charm container*, where Juju mounts every workload's
    socket at ``/charm/containers/<name>/pebble.socket``. Returns an empty mapping
    if *base* isn't present (i.e. we're not in a charm container).
    """
    sockets: dict[str, str] = {}
    try:
        names = os.listdir(base)
    except OSError:
        return sockets
    for name in sorted(names):
        path = f'{base}/{name}/pebble.socket'
        if os.path.exists(path):
            sockets[name] = path
    return sockets


def resolve_local_target(*, container: str | None = None, base: str = _LOCAL_SOCKET_DIR) -> Target:
    """Resolve a :class:`Target` for borescope running *inside the charm container*.

    Talks directly to a workload's mounted Pebble socket (Mode A) — no Juju, no
    unit reference. Picks the socket named by *container*, or the sole one if the
    charm declares just a single workload.
    """
    sockets = discover_local_sockets(base)
    if not sockets:
        raise DiscoveryError(
            f"no Pebble sockets found under {base}. '--here' only works from inside "
            "a Juju Kubernetes charm container, which mounts each workload's socket "
            "there. From your workstation, run 'borescope <unit>' instead."
        )
    if container is not None:
        socket = sockets.get(container)
        if socket is None:
            available = ', '.join(sockets)
            raise DiscoveryError(
                f"no Pebble socket for container '{container}' under {base}. "
                f'Available: {available}.'
            )
        chosen = container
    elif len(sockets) == 1:
        chosen, socket = next(iter(sockets.items()))
    else:
        available = ', '.join(sockets)
        raise DiscoveryError(
            f'this charm has multiple workload containers ({available}); '
            'choose one with --container.'
        )
    return Target(
        unit='local',
        app=chosen,
        container=chosen,
        model=None,
        socket_path=socket,
    )


def sanity_check(transport: Transport, target: Target) -> None:
    """Confirm the container's Pebble answers, and is new enough, before prompting."""
    try:
        info = transport.get_system_info()
    except Exception as exc:
        raise DiscoveryError(
            f"could not reach Pebble in {target.unit} container '{target.container}': {exc}"
        ) from exc

    # borescope v1 relies on Pebble's `--format json` output (via shimmer). Older
    # Pebbles (e.g. v1.26, still shipped by current stable charms) lack it. Probe
    # one structured read so we fail fast with a clear message rather than letting
    # every read command die with a cryptic "unknown flag `format'".
    try:
        transport.get_services()
    except Exception as exc:
        message = str(exc).lower()
        if 'unknown flag' in message and 'format' in message:
            version = getattr(info, 'version', 'unknown')
            raise DiscoveryError(
                f"the Pebble in {target.unit} container '{target.container}' "
                f'(version {version}) is too old for borescope: it lacks the '
                '`--format json` output borescope relies on. borescope v1 needs a '
                'newer Pebble (support for older Pebble may come later).'
            ) from exc
        # Any other failure here isn't necessarily fatal; reachability is already
        # proven, so let the session start and let individual commands report.
