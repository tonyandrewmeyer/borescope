#!/usr/bin/env python3
# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Sidecar charm with a shell-less workload, set up so cascade has things to look at.

The workload container is distroless (no shell, no binaries) at start. On
``pebble_ready`` the charm:

* pushes a tiny static ``workload-app`` binary into ``/usr/local/bin/`` (shipped
  as a charm file resource);
* pushes a couple of sample config and log files so cascade has paths to ``ls``,
  ``cat``, and ``pull``;
* adds a Pebble layer with two services (``app`` and ``ticker``) and one HTTP
  check (``app-ready``), then replans.

The result is a workload that still has no shell — every binary is invoked
directly by Pebble — but exposes services, logs, checks, and files for cascade
to drive.
"""

from __future__ import annotations

import logging
from pathlib import Path

import ops

logger = logging.getLogger(__name__)

WORKLOAD_CONTAINER = 'workload'
APP_BINARY_PATH = '/usr/local/bin/workload-app'
CONFIG_PATH = '/etc/workload-app/config.yaml'
HISTORY_LOG_PATH = '/var/log/workload-app/history.log'


SAMPLE_CONFIG = """\
# bareshell-test workload-app sample config.
# The binary doesn't actually read this — it exists so cascade has something
# to `cat`, `head`, `tail`, `pull`, and `grep`.
app:
  name: bareshell-workload
  mode: demo
  http:
    listen: ":8080"
  ticker:
    interval_seconds: 2
"""

SAMPLE_HISTORY = """\
2026-05-01T00:00:00Z startup
2026-05-01T00:00:01Z ready
2026-05-15T12:34:56Z reload
2026-05-30T09:00:00Z restart
"""

PEBBLE_LAYER: ops.pebble.LayerDict = {
    'summary': 'bareshell-test workload',
    'description': 'Two services and an HTTP check for cascade to exercise.',
    'services': {
        'app': {
            'override': 'replace',
            'summary': 'HTTP demo server',
            'command': f'{APP_BINARY_PATH} http :8080',
            'startup': 'enabled',
        },
        'ticker': {
            'override': 'replace',
            'summary': 'Log a tick every 2 seconds',
            'command': f'{APP_BINARY_PATH} ticker 2',
            'startup': 'enabled',
        },
    },
    'checks': {
        'app-ready': {
            'override': 'replace',
            'level': 'ready',
            'period': '5s',
            'timeout': '2s',
            'threshold': 3,
            'http': {'url': 'http://localhost:8080/health'},
        },
    },
}


class BareShellCharm(ops.CharmBase):
    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        framework.observe(self.on[WORKLOAD_CONTAINER].pebble_ready, self._on_ready)

    def _on_ready(self, _: ops.PebbleReadyEvent) -> None:
        container = self.unit.get_container(WORKLOAD_CONTAINER)
        self._push_binary(container)
        self._push_sample_files(container)
        container.add_layer('workload', PEBBLE_LAYER, combine=True)
        container.replan()
        self.unit.status = ops.ActiveStatus('workload ready: app + ticker (no shell)')

    def _push_binary(self, container: ops.Container) -> None:
        # Binary is bundled inside the charm at src/workload-app; the charm's
        # `src` dir is the package containing this module.
        source = Path(__file__).parent / 'workload-app'
        with source.open('rb') as f:
            container.push(
                APP_BINARY_PATH,
                f,
                make_dirs=True,
                permissions=0o755,
            )

    def _push_sample_files(self, container: ops.Container) -> None:
        container.push(CONFIG_PATH, SAMPLE_CONFIG, make_dirs=True, permissions=0o644)
        container.push(
            HISTORY_LOG_PATH,
            SAMPLE_HISTORY,
            make_dirs=True,
            permissions=0o644,
        )


if __name__ == '__main__':
    ops.main(BareShellCharm)
