# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Defang untrusted container-sourced names before they reach the terminal.

A workload container is, by definition, the thing you reach for borescope to
debug — and possibly the thing that's been compromised. Filenames it controls are
printed by ``ls``/``find`` and offered as tab completions; an embedded ANSI/OSC
escape (or a newline) could rewrite the screen, spoof the prompt, or smuggle a
line break past line-oriented output. As coreutils ``ls`` does for a terminal, we
render control characters visibly rather than emitting them raw.

This covers *names*. File contents (``cat``/``head``/``tail``) and the streamed
output of ``logs -f`` / ``exec`` are passed through verbatim, matching the
universal behaviour of ``cat`` and a real shell.
"""

from __future__ import annotations


def safe_name(name: str) -> str:
    r"""Return *name* with non-printable characters escaped as ``\xHH`` / ``\uHHHH``.

    Printable characters (including spaces and non-ASCII letters) are kept as-is;
    only control characters — ``ESC``, ``CR``, ``LF``, ``TAB``, C1 codes, ``DEL`` —
    are made visible, so a hostile filename cannot drive the terminal.
    """
    if name.isprintable():
        return name
    return ''.join(_escape(ch) for ch in name)


def _escape(ch: str) -> str:
    if ch.isprintable():
        return ch
    code = ord(ch)
    return f'\\x{code:02x}' if code <= 0xFF else f'\\u{code:04x}'
