# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Thin juju CLI wrappers, with subprocess mocked."""

from __future__ import annotations

import subprocess

import pytest

from borescope import juju
from borescope.errors import JujuError


def _fake_run(monkeypatch, *, stdout='', returncode=0, exc=None, capture=None):
    def fake(cmd, **kwargs):
        if capture is not None:
            capture['cmd'] = cmd
            capture['kwargs'] = kwargs
        if exc is not None:
            raise exc
        if returncode != 0:
            raise subprocess.CalledProcessError(returncode, cmd, output='', stderr='boom')
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr='')

    monkeypatch.setattr(juju.subprocess, 'run', fake)


def test_run_juju_returns_stdout(monkeypatch):
    _fake_run(monkeypatch, stdout='hello\n')
    assert juju.run_juju(['status']) == 'hello\n'


def test_run_juju_inserts_model_after_subcommand(monkeypatch):
    cap = {}
    _fake_run(monkeypatch, stdout='', capture=cap)
    juju.run_juju(['ssh', 'app/0', 'cat', '/x'], model='m1', juju_binary='juju')
    assert cap['cmd'] == ['juju', 'ssh', '-m', 'm1', 'app/0', 'cat', '/x']


def test_run_juju_detaches_stdin_without_input(monkeypatch):
    cap = {}
    _fake_run(monkeypatch, stdout='', capture=cap)
    juju.run_juju(['status'])
    assert cap['kwargs']['stdin'] == subprocess.DEVNULL


def test_run_juju_not_found(monkeypatch):
    _fake_run(monkeypatch, exc=FileNotFoundError())
    with pytest.raises(JujuError, match='not found'):
        juju.run_juju(['status'])


def test_run_juju_timeout(monkeypatch):
    _fake_run(monkeypatch, exc=subprocess.TimeoutExpired(cmd='juju', timeout=30.0))
    with pytest.raises(JujuError, match='timed out'):
        juju.run_juju(['status'])


def test_run_juju_called_process_error(monkeypatch):
    _fake_run(monkeypatch, returncode=2)
    with pytest.raises(JujuError) as excinfo:
        juju.run_juju(['status'])
    assert excinfo.value.returncode == 2
    assert 'boom' in excinfo.value.stderr


def test_current_controller_model_parses(monkeypatch):
    monkeypatch.setattr(juju, 'run_juju', lambda *a, **k: 'ctrl:alice/prod\n')
    assert juju.current_controller_model() == ('ctrl', 'alice/prod')


def test_current_controller_model_empty(monkeypatch):
    monkeypatch.setattr(juju, 'run_juju', lambda *a, **k: '\n')
    assert juju.current_controller_model() == (None, None)


def test_current_controller_model_juju_error(monkeypatch):
    def boom(*a, **k):
        raise JujuError('no controller')

    monkeypatch.setattr(juju, 'run_juju', boom)
    assert juju.current_controller_model() == (None, None)


def test_status_json_parses(monkeypatch):
    monkeypatch.setattr(juju, 'run_juju', lambda *a, **k: '{"model": {"type": "caas"}}')
    assert juju.status_json() == {'model': {'type': 'caas'}}


def test_status_json_bad_json(monkeypatch):
    monkeypatch.setattr(juju, 'run_juju', lambda *a, **k: 'not json')
    with pytest.raises(JujuError, match='could not parse'):
        juju.status_json()
