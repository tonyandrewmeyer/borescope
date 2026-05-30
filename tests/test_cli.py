# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""CLI entry point: argument handling and mode selection."""

from __future__ import annotations

import io

import pytest

from borescope import cli
from borescope.errors import DiscoveryError


def test_no_target_is_usage_error(capsys):
    assert cli.main([]) == 2
    assert 'unit reference is required' in capsys.readouterr().err


def test_rejects_unsafe_container(capsys):
    code = cli.main(['--container', 'bad;rm -rf', 'app/0'])
    assert code == 1
    assert 'not a valid container name' in capsys.readouterr().err


def test_version_exits(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(['--version'])
    assert excinfo.value.code == 0
    assert 'borescope' in capsys.readouterr().out


# -- _build_target -----------------------------------------------------------
def test_build_target_socket_mode():
    args = cli.build_parser().parse_args(['--socket', '/run/pebble.socket', 'app/0'])
    target = cli._build_target(args)
    assert target.socket_path == '/run/pebble.socket'
    assert target.unit == 'app/0'
    assert target.app == 'app'


def test_build_target_socket_without_unit_defaults_to_local():
    args = cli.build_parser().parse_args(['--socket', '/run/pebble.socket'])
    target = cli._build_target(args)
    assert target.unit == 'local'
    assert target.app == 'local'


# -- main flow (transport mocked) --------------------------------------------
def _mock_transport(monkeypatch, transport):
    monkeypatch.setattr('borescope.transport.open_transport', lambda **kw: transport)
    monkeypatch.setattr('borescope.discovery.sanity_check', lambda t, tgt: None)


def test_command_one_shot(monkeypatch, capsys, transport):
    _mock_transport(monkeypatch, transport)
    code = cli.main(['--socket', '/x', 'app/0', '--command', 'pwd'])
    assert code == 0
    assert capsys.readouterr().out.strip() == '/'


def test_batch_from_stdin(monkeypatch, capsys, transport):
    _mock_transport(monkeypatch, transport)
    monkeypatch.setattr(cli.sys, 'stdin', io.StringIO('pwd\n\ncd /etc\npwd\n'))
    code = cli.main(['--socket', '/x', 'app/0'])
    assert code == 0
    out = capsys.readouterr().out.splitlines()
    assert out == ['/', '/etc']


def test_snapshot_flow(monkeypatch, capsys, transport):
    _mock_transport(monkeypatch, transport)
    monkeypatch.setattr('borescope.snapshot.snapshot_json', lambda t, tgt: '{"ok": 1}')
    code = cli.main(['--socket', '/x', 'app/0', '--snapshot'])
    assert code == 0
    assert capsys.readouterr().out.strip() == '{"ok": 1}'


def test_borescope_error_returns_1(monkeypatch, capsys):
    def boom(**kw):
        raise DiscoveryError('cannot reach unit')

    monkeypatch.setattr('borescope.transport.open_transport', boom)
    code = cli.main(['--socket', '/x', 'app/0'])
    assert code == 1
    assert 'cannot reach unit' in capsys.readouterr().err
