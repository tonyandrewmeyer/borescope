# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""JujuSshRunner argv construction — the charm-container relay (no juju needed).

borescope reaches a workload's Pebble *through the charm container* (which always has
a shell and mounts the workload's socket), not via ``juju ssh --container=<workload>``
(which execs ``sh`` in the workload and so fails on shell-less rocks).
"""

from __future__ import annotations

import base64
import subprocess
from typing import Any
from unittest.mock import patch

import pytest
from shimmer import FileTransferRunner

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


def test_wrap_shlex_quotes_argv_with_shell_metacharacters():
    # juju ssh joins argv with spaces and `sh -c`s the result, so any shell
    # metachar in the user's argv (here, a `;` inside `pebble exec -- sh -c
    # '...'`) would split the command before reaching the inner sh. wrap must
    # shlex-quote each piece so the outer sh-c sees one literal token.
    runner = JujuSshRunner('a/0', 'c')
    argv = runner.wrap(['/charm/bin/pebble', 'exec', '--', 'sh', '-c', 'echo a; echo b'])
    # The dangerous arg is quoted; safe tokens (paths, plain words) are not.
    assert "'echo a; echo b'" in argv
    assert '/charm/bin/pebble' in argv
    assert 'exec' in argv
    # The env shim's KEY=/path has no metachars, so it survives unchanged
    # (still parseable as a single env-var assignment by the outer sh).
    assert 'PEBBLE_SOCKET=/charm/containers/c/pebble.socket' in argv


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


# --------------------------------------------------------------------------- #
# FileTransferRunner: stage push/pull temp files in the charm container, not
# locally. The base impl pipes base64-encoded bytes through the runner's own
# juju channel (which executes as root) so Pebble's same-owner check passes
# and the same code path works for ssh and exec.
# --------------------------------------------------------------------------- #


def _fake_completed(stdout: bytes = b'', stderr: bytes = b'', returncode: int = 0):
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


def test_runners_satisfy_filetransferrunner_protocol():
    # Runtime-checkable protocol — both runners must look like FileTransferRunners
    # so PebbleCliClient.push/pull take the remote-staging path, not the local
    # temp-file fallback.
    assert isinstance(JujuSshRunner('a/0', 'c'), FileTransferRunner)
    assert isinstance(JujuExecRunner('a/0', 'c'), FileTransferRunner)


def test_upload_temp_pipes_base64_via_charm_channel():
    runner = JujuSshRunner('a/0', 'c', model='m')
    captured: dict[str, Any] = {}

    def fake_run(argv, **kwargs):
        captured['argv'] = argv
        return _fake_completed()

    with patch.object(subprocess, 'run', side_effect=fake_run):
        path = runner.upload_temp(b'hello world')

    assert path.startswith('/tmp/cascade-upload-')  # noqa: S108 (remote path, not local)
    # juju ssh prefix is preserved; argv ends in `sh -c '<base64 pipeline>'`.
    assert captured['argv'][:4] == ['juju', 'ssh', '-m', 'm']
    assert captured['argv'][-2] == 'sh' or captured['argv'][-3] == 'sh'
    inner = captured['argv'][-1]
    assert isinstance(inner, str)
    assert 'base64 -d' in inner
    assert path in inner
    # The encoded content is in there verbatim.
    expected = base64.b64encode(b'hello world').decode('ascii')
    assert expected in inner


def test_upload_temp_raises_on_juju_failure():
    runner = JujuSshRunner('a/0', 'c')
    with (
        patch.object(
            subprocess, 'run', return_value=_fake_completed(stderr=b'boom', returncode=1)
        ),
        pytest.raises(RuntimeError, match=r'upload_temp.*boom'),
    ):
        runner.upload_temp(b'x')


def test_download_temp_reverses_base64():
    runner = JujuSshRunner('a/0', 'c')
    payload = b'\x00\x01binary stuff\xff'
    encoded = base64.b64encode(payload)
    with patch.object(subprocess, 'run', return_value=_fake_completed(stdout=encoded)):
        out = runner.download_temp('/tmp/cascade-upload-xyz')  # noqa: S108 (remote path)
    assert out == payload


def test_download_temp_uses_base64_command_via_charm_channel():
    runner = JujuExecRunner('a/0', 'c', model='m')
    captured: dict[str, Any] = {}

    def fake_run(argv, **kwargs):
        captured['argv'] = argv
        return _fake_completed(stdout=base64.b64encode(b''))

    with patch.object(subprocess, 'run', side_effect=fake_run):
        runner.download_temp('/tmp/foo')  # noqa: S108 (remote path)

    # juju exec prefix + `base64 /tmp/foo` (no env shim — this isn't a pebble call).
    assert captured['argv'][:4] == ['juju', 'exec', '-m', 'm']
    assert '--' in captured['argv']
    assert captured['argv'][-2:] == ['base64', '/tmp/foo']  # noqa: S108 (remote path)


def test_download_temp_raises_on_juju_failure():
    runner = JujuSshRunner('a/0', 'c')
    with (
        patch.object(
            subprocess, 'run', return_value=_fake_completed(stderr=b'no such file', returncode=1)
        ),
        pytest.raises(RuntimeError, match=r'download_temp.*no such file'),
    ):
        runner.download_temp('/tmp/missing')  # noqa: S108 (remote path)


def test_cleanup_temp_runs_rm_f_and_swallows_errors():
    runner = JujuSshRunner('a/0', 'c')
    captured: dict[str, Any] = {}

    def fake_run(argv, **kwargs):
        captured['argv'] = argv
        captured['check'] = kwargs.get('check')
        return _fake_completed(returncode=1)  # simulate failure

    with patch.object(subprocess, 'run', side_effect=fake_run):
        # Must NOT raise even though rm returned non-zero.
        runner.cleanup_temp('/tmp/foo')  # noqa: S108 (remote path)

    assert captured['argv'][-3:] == ['rm', '-f', '/tmp/foo']  # noqa: S108 (remote path)
    assert captured['check'] is False
