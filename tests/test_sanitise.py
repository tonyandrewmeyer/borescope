# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Defanging of untrusted container-sourced names."""

from __future__ import annotations

from borescope.shell.sanitise import safe_name


def test_plain_name_unchanged():
    assert safe_name('error.log') == 'error.log'


def test_spaces_and_unicode_kept():
    assert safe_name('my file.txt') == 'my file.txt'
    assert safe_name('café.log') == 'café.log'


def test_escape_sequence_defanged():
    # A filename that tries to start an ANSI colour sequence.
    assert safe_name('\x1b[31mboom') == '\\x1b[31mboom'


def test_newline_and_tab_escaped():
    assert safe_name('a\nb\tc') == 'a\\x0ab\\x09c'
