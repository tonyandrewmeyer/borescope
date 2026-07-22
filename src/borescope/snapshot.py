# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""``borescope --snapshot`` — dump container state as JSON.

Cheap to produce, useful for filing bugs and for feeding tools like
``explain-my-model``. The shape is intended to be stable and consumable.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import yaml

from . import __version__

if TYPE_CHECKING:
    from .discovery import Target
    from .transport import Transport


def _value(obj: object) -> str:
    return getattr(obj, 'value', str(obj))


def build_snapshot(transport: Transport, target: Target, *, log_lines: int = 20) -> dict[str, Any]:
    """Capture *target*'s Pebble state as a serialisable dict."""
    data: dict[str, Any] = {
        'borescope_version': __version__,
        'captured_at': datetime.now(UTC).isoformat(),
        'unit': target.unit,
        'container': target.container,
        'model': target.model,
        'controller': target.controller,
    }

    try:
        data['system'] = {'version': transport.get_system_info().version}
    except Exception as exc:
        data['system_error'] = str(exc)

    try:
        data['services'] = [
            {'name': s.name, 'startup': _value(s.startup), 'current': _value(s.current)}
            for s in transport.get_services()
        ]
    except Exception as exc:
        data['services_error'] = str(exc)

    try:
        plan = transport.get_plan()
        data['plan'] = (
            plan.to_dict() if hasattr(plan, 'to_dict') else yaml.safe_load(plan.to_yaml())
        )
    except Exception as exc:
        data['plan_error'] = str(exc)

    try:
        data['checks'] = [
            {
                'name': c.name,
                'level': _value(c.level),
                'status': _value(c.status),
                'failures': c.failures,
                'threshold': c.threshold,
            }
            for c in transport.get_checks()
        ]
    except Exception as exc:
        data['checks_error'] = str(exc)

    try:
        data['notices'] = [
            {
                'id': n.id,
                'type': _value(n.type),
                'key': n.key,
                'occurrences': n.occurrences,
                'last_repeated': n.last_repeated.isoformat() if n.last_repeated else None,
            }
            for n in transport.get_notices()
        ]
    except Exception as exc:
        data['notices_error'] = str(exc)

    try:
        if target.socket_path:
            from .transport.logs import iter_logs

            data['recent_logs'] = list(iter_logs(target.socket_path, n=log_lines))
        else:
            from .transport.relay import run_pebble

            result = run_pebble(target, ['logs', '-n', str(log_lines)])
            data['recent_logs'] = (result.stdout or '').splitlines()
    except Exception as exc:
        data['logs_error'] = str(exc)

    return data


def snapshot_json(transport: Transport, target: Target, *, log_lines: int = 20) -> str:
    """Capture *target*'s Pebble state as a JSON string."""
    return json.dumps(build_snapshot(transport, target, log_lines=log_lines), indent=2)
