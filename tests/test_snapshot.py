# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""--snapshot: capturing container state as JSON."""

from __future__ import annotations

import json
import subprocess

import pytest

from borescope import snapshot
from borescope.transport import relay


@pytest.fixture(autouse=True)
def _fake_logs(monkeypatch):
    # build_snapshot pulls recent logs over the relay; stub it out.
    def fake_run_pebble(target, args, *, timeout=30.0):
        return subprocess.CompletedProcess(args, 0, stdout='log line 1\nlog line 2\n', stderr='')

    monkeypatch.setattr(relay, 'run_pebble', fake_run_pebble)


def test_build_snapshot_happy_path(pebble_transport, target):
    data = snapshot.build_snapshot(pebble_transport, target)
    assert data['unit'] == 'app/0'
    assert data['container'] == 'workload'
    assert data['system'] == {'version': '1.99'}
    assert {s['name'] for s in data['services']} == {'web', 'worker'}
    assert 'services' in data['plan']
    assert data['checks'][0]['name'] == 'ready'
    assert data['notices'][0]['key'] == 'example.com/thing'
    assert data['recent_logs'] == ['log line 1', 'log line 2']
    assert 'borescope_version' in data
    assert 'captured_at' in data


def test_build_snapshot_records_section_errors(pebble_transport, target):
    def boom(*a, **k):
        raise RuntimeError('nope')

    pebble_transport.get_services = boom
    data = snapshot.build_snapshot(pebble_transport, target)
    assert 'services_error' in data
    assert 'nope' in data['services_error']
    # Other sections still captured.
    assert 'checks' in data


def test_build_snapshot_all_sections_error(pebble_transport, target, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError('down')

    for method in ('get_system_info', 'get_services', 'get_plan', 'get_checks', 'get_notices'):
        monkeypatch.setattr(pebble_transport, method, boom)
    monkeypatch.setattr(relay, 'run_pebble', boom)

    data = snapshot.build_snapshot(pebble_transport, target)
    for key in (
        'system_error',
        'services_error',
        'plan_error',
        'checks_error',
        'notices_error',
        'logs_error',
    ):
        assert key in data


def test_snapshot_json_is_valid_json(pebble_transport, target):
    text = snapshot.snapshot_json(pebble_transport, target)
    parsed = json.loads(text)
    assert parsed['unit'] == 'app/0'
