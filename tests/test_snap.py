# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Tests for the snap startup hook that stages JUJU_DATA."""

from __future__ import annotations

import pwd

import pytest

from borescope.snap import stage_juju_data


@pytest.fixture
def in_snap(monkeypatch, tmp_path):
    """Pretend we're running inside the borescope snap."""
    real_home = tmp_path / 'home'
    snap_common = tmp_path / 'snap-common'
    source = real_home / '.local' / 'share' / 'juju'
    target = snap_common / 'juju'

    source.mkdir(parents=True)
    snap_common.mkdir()
    (source / 'controllers.yaml').write_text('controllers:\n  k8s: {}\n')
    (source / 'cookies.yaml').write_text('cookies: []\n')

    monkeypatch.setenv('SNAP_NAME', 'borescope')
    monkeypatch.setenv('SNAP_USER_COMMON', str(snap_common))
    monkeypatch.setattr(
        pwd,
        'getpwuid',
        lambda _uid: pwd.struct_passwd(('u', 'x', 0, 0, '', str(real_home), '/bin/sh')),
    )
    return source, target


def test_noop_outside_snap(monkeypatch, tmp_path):
    monkeypatch.delenv('SNAP_NAME', raising=False)
    target = tmp_path / 'juju'
    stage_juju_data()
    assert not target.exists()


def test_noop_when_snap_name_is_something_else(monkeypatch):
    monkeypatch.setenv('SNAP_NAME', 'jhack')
    stage_juju_data()  # must not raise


def test_stages_when_host_juju_data_exists(in_snap):
    source, target = in_snap
    stage_juju_data()
    assert (target / 'controllers.yaml').read_text() == (source / 'controllers.yaml').read_text()
    assert (target / 'cookies.yaml').read_text() == (source / 'cookies.yaml').read_text()


def test_noop_when_host_juju_data_missing(monkeypatch, tmp_path):
    real_home = tmp_path / 'home'
    snap_common = tmp_path / 'snap-common'
    real_home.mkdir()
    snap_common.mkdir()
    monkeypatch.setenv('SNAP_NAME', 'borescope')
    monkeypatch.setenv('SNAP_USER_COMMON', str(snap_common))
    monkeypatch.setattr(
        pwd,
        'getpwuid',
        lambda _uid: pwd.struct_passwd(('u', 'x', 0, 0, '', str(real_home), '/bin/sh')),
    )
    stage_juju_data()
    assert not (snap_common / 'juju').exists()


def test_subsequent_runs_pick_up_host_changes(in_snap):
    source, target = in_snap
    stage_juju_data()
    assert (target / 'controllers.yaml').read_text().startswith('controllers:\n  k8s')
    (source / 'controllers.yaml').write_text('controllers:\n  prod: {}\n')
    stage_juju_data()
    assert 'prod' in (target / 'controllers.yaml').read_text()


def test_inside_snap_writes_bundled_juju_cookies_to_copy(in_snap):
    """Writes by the bundled juju into the snap copy must not leak back to host."""
    source, target = in_snap
    stage_juju_data()
    (target / 'cookies.yaml').write_text('cookies:\n  - inside-snap\n')
    # Re-run: host source is unchanged, target gets overwritten with host data.
    stage_juju_data()
    assert (source / 'cookies.yaml').read_text() == 'cookies: []\n'
    assert (target / 'cookies.yaml').read_text() == 'cookies: []\n'
