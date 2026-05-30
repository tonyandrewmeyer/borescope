# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""JujuSshRunner argv construction — the charm-container relay (no juju needed).

borescope reaches a workload's Pebble *through the charm container* (which always has
a shell and mounts the workload's socket), not via ``juju ssh --container=<workload>``
(which execs ``sh`` in the workload and so fails on shell-less rocks).
"""

from __future__ import annotations

from borescope.transport.runner import JujuExecRunner, JujuSshRunner


def test_wrap_targets_charm_container_with_workload_socket():
    runner = JujuSshRunner('myapp/0', 'workload')
    argv = runner.wrap(['/charm/bin/pebble', 'services'])
    assert argv == [
        'juju',
        'ssh',
        # NB: no --container (land in the charm container) and no -- separator.
        'myapp/0',
        'env',
        'PEBBLE_SOCKET=/charm/containers/workload/pebble.socket',
        'PEBBLE=/charm/containers/workload',
        '/charm/bin/pebble',
        'services',
    ]


def test_pebble_socket_path():
    assert JujuSshRunner('a/0', 'agent').pebble_socket == '/charm/containers/agent/pebble.socket'


def test_wrap_has_no_dashdash_and_no_container_flag():
    argv = JujuSshRunner('a/0', 'c').wrap(['/charm/bin/pebble', 'ls'])
    assert '--' not in argv
    assert '--container' not in argv


def test_wrap_includes_model_and_juju_binary():
    runner = JujuSshRunner('a/1', 'c', model='foo', juju_binary='/snap/bin/juju')
    argv = runner.wrap(['/charm/bin/pebble', 'plan'])
    assert argv[:4] == ['/snap/bin/juju', 'ssh', '-m', 'foo']
    assert argv[-2:] == ['/charm/bin/pebble', 'plan']


def test_wrap_no_socket_shim_without_container():
    runner = JujuSshRunner('a/0', None)
    argv = runner.wrap(['/charm/bin/pebble', 'ls'])
    assert 'env' not in argv
    assert runner.pebble_socket is None


# --------------------------------------------------------------------------- #
# JujuExecRunner: the --via exec relay alternative.
# --------------------------------------------------------------------------- #


def test_exec_wrap_uses_juju_exec_with_unit_flag_and_dashdash():
    runner = JujuExecRunner('myapp/0', 'workload')
    argv = runner.wrap(['/charm/bin/pebble', 'services'])
    # `juju exec` (unlike k8s ssh) accepts -- as a normal arg separator, and
    # takes the unit via -u rather than as a positional after a subcommand.
    assert argv == [
        'juju',
        'exec',
        '-u',
        'myapp/0',
        '--',
        'env',
        'PEBBLE_SOCKET=/charm/containers/workload/pebble.socket',
        'PEBBLE=/charm/containers/workload',
        '/charm/bin/pebble',
        'services',
    ]


def test_exec_wrap_includes_model_before_unit():
    runner = JujuExecRunner('a/1', 'c', model='foo', juju_binary='/snap/bin/juju')
    argv = runner.wrap(['/charm/bin/pebble', 'plan'])
    assert argv[:6] == ['/snap/bin/juju', 'exec', '-m', 'foo', '-u', 'a/1']
    assert '--' in argv
    assert argv[-2:] == ['/charm/bin/pebble', 'plan']


def test_exec_wrap_no_socket_shim_without_container():
    runner = JujuExecRunner('a/0', None)
    argv = runner.wrap(['/charm/bin/pebble', 'ls'])
    assert 'env' not in argv
    assert runner.pebble_socket is None
