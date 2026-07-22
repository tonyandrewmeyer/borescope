# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Pebble-native commands against an in-memory Pebble fake."""

from __future__ import annotations

import pytest
from ops import pebble

from borescope.shell.commands import base
from borescope.transport import logs, relay


@pytest.fixture
def registry():
    return base.build_registry()


def run(registry, ctx, name, *args, stdin=None):
    return registry[name].run(ctx, list(args), stdin)


# -- services ----------------------------------------------------------------
def test_services_lists(registry, pebble_ctx):
    result = run(registry, pebble_ctx, 'services')
    assert 'web' in result.output
    assert 'worker' in result.output
    assert 'SERVICE' in result.output  # UPPER CASE header per Canonical CLI spec


def test_services_filtered(registry, pebble_ctx):
    result = run(registry, pebble_ctx, 'services', 'web')
    assert 'web' in result.output
    assert 'worker' not in result.output


def test_services_no_headers(registry, pebble_ctx):
    result = run(registry, pebble_ctx, 'services', '--no-headers')
    assert 'SERVICE' not in result.output
    assert 'web' in result.output


def test_services_empty(registry, pebble_ctx, pebble_transport):
    pebble_transport._services = []
    result = run(registry, pebble_ctx, 'services')
    # Empty-state line goes to stderr, exit code stays 0, stdout is bare.
    assert result.output == ''
    assert result.error == 'No services configured.'
    assert result.code == 0


def test_services_format_json(registry, pebble_ctx):
    import json

    result = run(registry, pebble_ctx, 'services', '--format=json')
    items = json.loads(result.output)
    assert {'name': 'web', 'startup': 'enabled', 'current': 'active'} in items


def test_services_format_yaml(registry, pebble_ctx):
    result = run(registry, pebble_ctx, 'services', '--format', 'yaml')
    assert 'items:' in result.output
    assert 'name: web' in result.output


def test_services_format_json_empty(registry, pebble_ctx, pebble_transport):
    import json

    pebble_transport._services = []
    result = run(registry, pebble_ctx, 'services', '--format=json')
    assert json.loads(result.output) == []
    assert result.error == ''


def test_services_format_unknown(registry, pebble_ctx):
    result = run(registry, pebble_ctx, 'services', '--format=xml')
    assert result.code == 1
    assert 'unknown value' in result.error


@pytest.mark.parametrize(
    ('cmd', 'verb', 'past'),
    [
        ('start', 'start', 'Started'),
        ('stop', 'stop', 'Stopped'),
        ('restart', 'restart', 'Restarted'),
    ],
)
def test_service_actions(registry, pebble_ctx, pebble_transport, cmd, verb, past):
    result = run(registry, pebble_ctx, cmd, 'web', 'worker')
    assert result.output == f'{past}: web, worker'
    assert (verb, (('web', 'worker'),)) in pebble_transport.calls


def test_service_action_requires_name(registry, pebble_ctx):
    result = run(registry, pebble_ctx, 'start')
    assert result.code == 1
    assert 'usage' in result.error


def test_replan(registry, pebble_ctx, pebble_transport):
    assert run(registry, pebble_ctx, 'replan').output == 'Replanned'
    assert ('replan', ()) in pebble_transport.calls


# -- plan / checks / health --------------------------------------------------
def test_plan_yaml(registry, pebble_ctx):
    result = run(registry, pebble_ctx, 'plan')
    assert 'services:' in result.output
    assert 'web' in result.output


def test_checks_lists(registry, pebble_ctx):
    result = run(registry, pebble_ctx, 'checks')
    assert 'ready' in result.output
    assert '0/3' in result.output


def test_checks_empty(registry, pebble_ctx, pebble_transport):
    pebble_transport._checks = []
    result = run(registry, pebble_ctx, 'checks')
    assert result.output == ''
    assert result.error == 'No checks configured.'
    assert result.code == 0


def test_health_healthy(registry, pebble_ctx):
    result = run(registry, pebble_ctx, 'health')
    assert result.output == 'healthy'
    assert result.code == 0


def test_health_unhealthy(registry, pebble_ctx, pebble_transport):
    pebble_transport.set_check_status(pebble.CheckStatus.DOWN)
    result = run(registry, pebble_ctx, 'health')
    assert result.code == 1
    assert 'unhealthy' in result.output
    assert 'ready' in result.output


def test_health_no_checks(registry, pebble_ctx, pebble_transport):
    pebble_transport._checks = []
    assert run(registry, pebble_ctx, 'health').output == 'healthy (no checks configured)'


# -- notices -----------------------------------------------------------------
def test_notices_lists(registry, pebble_ctx):
    result = run(registry, pebble_ctx, 'notices')
    assert 'example.com/thing' in result.output


def test_notices_empty(registry, pebble_ctx, pebble_transport):
    pebble_transport.get_notices = lambda **kw: []
    result = run(registry, pebble_ctx, 'notices')
    assert result.output == ''
    assert result.error == 'No notices recorded.'
    assert result.code == 0


def test_notice_detail(registry, pebble_ctx):
    result = run(registry, pebble_ctx, 'notice', '1')
    assert 'ID:' in result.output
    assert 'example.com/thing' in result.output
    assert "{'k': 'v'}" in result.output


def test_notice_requires_id(registry, pebble_ctx):
    assert run(registry, pebble_ctx, 'notice').code == 1


def test_notify(registry, pebble_ctx, pebble_transport):
    result = run(registry, pebble_ctx, 'notify', 'example.com/x', 'a=1', 'b=2')
    assert result.output == 'Recorded notice 7'
    assert ('notify', ('example.com/x', {'a': '1', 'b': '2'})) in pebble_transport.calls


def test_notify_requires_key(registry, pebble_ctx):
    assert run(registry, pebble_ctx, 'notify').code == 1


# -- changes / tasks ---------------------------------------------------------
def test_changes_lists(registry, pebble_ctx):
    result = run(registry, pebble_ctx, 'changes')
    assert 'Start web' in result.output


def test_tasks_default_latest(registry, pebble_ctx):
    result = run(registry, pebble_ctx, 'tasks')
    assert 'Do the thing' in result.output


def test_tasks_by_id(registry, pebble_ctx):
    result = run(registry, pebble_ctx, 'tasks', '42')
    assert 'Change 42' in result.output


def test_changes_empty(registry, pebble_ctx, pebble_transport):
    pebble_transport.get_changes = lambda *a, **k: []
    result = run(registry, pebble_ctx, 'changes')
    assert result.output == ''
    assert result.error == 'No changes recorded.'
    assert result.code == 0


def test_tasks_no_changes(registry, pebble_ctx, pebble_transport):
    pebble_transport.get_changes = lambda *a, **k: []
    result = run(registry, pebble_ctx, 'tasks')
    assert result.output == ''
    assert result.error == 'No changes recorded.'


def test_tasks_change_without_tasks(registry, pebble_ctx, pebble_transport):
    from types import SimpleNamespace

    pebble_transport.get_change = lambda cid: SimpleNamespace(id=str(cid), summary='x', tasks=[])
    result = run(registry, pebble_ctx, 'tasks', '5')
    assert result.output == ''
    assert result.error == 'Change 5: no tasks.'


def test_notice_without_data(registry, pebble_ctx, pebble_transport):
    from types import SimpleNamespace

    pebble_transport.get_notice = lambda nid: SimpleNamespace(
        id=nid,
        type=SimpleNamespace(value='custom'),
        key='k',
        occurrences=1,
        first_occurred=None,
        last_occurred=None,
        last_data=None,
    )
    result = run(registry, pebble_ctx, 'notice', '1')
    assert 'Data:' not in result.output


# -- pull / push usage -------------------------------------------------------
def test_pull_usage_error(registry, pebble_ctx):
    assert run(registry, pebble_ctx, 'pull', 'only-one').code == 1


def test_push_usage_error(registry, pebble_ctx):
    assert run(registry, pebble_ctx, 'push', 'only-one').code == 1


# -- logs --------------------------------------------------------------------
# On a directly-reachable socket, `logs` speaks /v1/logs itself: no `pebble`
# binary on the host, and no relay. See tests/test_logs.py for the wire format.
@pytest.fixture
def socket_ctx(pebble_ctx):
    import dataclasses

    pebble_ctx.target = dataclasses.replace(pebble_ctx.target, socket_path='/run/pebble.socket')
    return pebble_ctx


def _capture_iter_logs(monkeypatch, lines):
    calls = {}

    def fake_iter_logs(socket_path, *, services=(), n=30, follow=False, timeout=30.0):
        calls.update(socket_path=socket_path, services=list(services), n=n, follow=follow)
        yield from lines

    # pebble.py calls logs.iter_logs, so patching the module attribute bites.
    monkeypatch.setattr(logs, 'iter_logs', fake_iter_logs)
    return calls


def test_logs_over_socket_needs_no_pebble_binary(registry, socket_ctx, monkeypatch):
    def no_relay(target):
        raise AssertionError('socket targets must not go through the pebble relay')

    monkeypatch.setattr(relay, 'pebble_relay', no_relay)
    calls = _capture_iter_logs(monkeypatch, ['ts [web] one', 'ts [web] two'])

    result = run(registry, socket_ctx, 'logs')
    assert result.output == 'ts [web] one\nts [web] two'
    assert result.code == 0
    assert calls == {
        'socket_path': '/run/pebble.socket',
        'services': [],
        'n': 30,  # Pebble's own default for `logs -n`
        'follow': False,
    }


def test_logs_over_socket_passes_n_and_services(registry, socket_ctx, monkeypatch):
    calls = _capture_iter_logs(monkeypatch, [])
    run(registry, socket_ctx, 'logs', '-n', '5', 'web', 'worker')
    assert calls['n'] == 5
    assert calls['services'] == ['web', 'worker']


def test_logs_over_socket_accepts_n_all(registry, socket_ctx, monkeypatch):
    calls = _capture_iter_logs(monkeypatch, [])
    run(registry, socket_ctx, 'logs', '-n', 'all')
    assert calls['n'] == -1


def test_logs_over_socket_rejects_bad_n(registry, socket_ctx, monkeypatch):
    _capture_iter_logs(monkeypatch, [])
    result = run(registry, socket_ctx, 'logs', '-n', 'bogus')
    assert result.code == 1
    assert 'non-negative integer' in result.error


def test_logs_over_socket_follow_streams_to_stdout(registry, socket_ctx, monkeypatch, capsys):
    calls = _capture_iter_logs(monkeypatch, ['ts [web] one', 'ts [web] two'])
    result = run(registry, socket_ctx, 'logs', '-f')
    assert calls['follow'] is True
    assert capsys.readouterr().out == 'ts [web] one\nts [web] two\n'
    assert result.output == ''


def test_logs_over_socket_reports_connection_failure(registry, socket_ctx, monkeypatch):
    def boom(socket_path, **kwargs):
        raise logs.LogsError('could not connect to Pebble')
        yield  # pragma: no cover - generator marker

    monkeypatch.setattr(logs, 'iter_logs', boom)
    result = run(registry, socket_ctx, 'logs')
    assert result.code == 1
    assert result.error == 'logs: could not connect to Pebble'
