# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Pebble-native commands against an in-memory Pebble fake."""

from __future__ import annotations

import pytest
from ops import pebble

from borescope.shell.commands.base import build_registry


@pytest.fixture
def registry():
    return build_registry()


def run(registry, ctx, name, *args, stdin=None):
    return registry[name].run(ctx, list(args), stdin)


# -- services ----------------------------------------------------------------
def test_services_lists(registry, pebble_ctx):
    result = run(registry, pebble_ctx, 'services')
    assert 'web' in result.output
    assert 'worker' in result.output
    assert 'Service' in result.output  # header


def test_services_filtered(registry, pebble_ctx):
    result = run(registry, pebble_ctx, 'services', 'web')
    assert 'web' in result.output
    assert 'worker' not in result.output


def test_services_empty(registry, pebble_ctx, pebble_transport):
    pebble_transport._services = []
    assert run(registry, pebble_ctx, 'services').output == '(no services)'


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
    assert run(registry, pebble_ctx, 'replan').output == 'Replanned.'
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
    assert run(registry, pebble_ctx, 'checks').output == '(no checks)'


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
    assert run(registry, pebble_ctx, 'notices').output == '(no notices)'


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
    assert run(registry, pebble_ctx, 'changes').output == '(no changes)'


def test_tasks_no_changes(registry, pebble_ctx, pebble_transport):
    pebble_transport.get_changes = lambda *a, **k: []
    assert run(registry, pebble_ctx, 'tasks').output == '(no changes)'


def test_tasks_change_without_tasks(registry, pebble_ctx, pebble_transport):
    from types import SimpleNamespace

    pebble_transport.get_change = lambda cid: SimpleNamespace(id=str(cid), summary='x', tasks=[])
    assert run(registry, pebble_ctx, 'tasks', '5').output == 'Change 5: (no tasks)'


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
