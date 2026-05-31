# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Stream-aware output helpers shared by built-in commands.

Kept tiny on purpose: a single source of truth for "is this stream going to
honour ANSI" so command code never sprouts its own ad-hoc isatty checks.
"""

from __future__ import annotations

import os
import sys
from typing import IO

ANSI_BOLD = '\x1b[1m'
ANSI_RESET = '\x1b[0m'


def supports_ansi(stream: IO[str] | None = None) -> bool:
    """Return whether *stream* (default: stdout) will render ANSI escapes.

    Disabled when ``NO_COLOR`` is set (any non-empty value) or when the stream
    is not a TTY — pipes, redirected files, and test capture all fall through.
    """
    if os.environ.get('NO_COLOR', '') != '':
        return False
    target = stream if stream is not None else sys.stdout
    isatty = getattr(target, 'isatty', None)
    return bool(isatty and isatty())


def bold(text: str) -> str:
    """Wrap *text* in ANSI bold if stdout supports it, else return it unchanged."""
    return f'{ANSI_BOLD}{text}{ANSI_RESET}' if supports_ansi() else text
