# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""CLI entry point: argument handling and mode selection."""

from __future__ import annotations

from borescope import cli


def test_no_target_is_usage_error(capsys):
    assert cli.main([]) == 2
    assert 'unit reference is required' in capsys.readouterr().err


def test_rejects_unsafe_container(capsys):
    code = cli.main(['--container', 'bad;rm -rf', 'app/0'])
    assert code == 1
    assert 'not a valid container name' in capsys.readouterr().err
