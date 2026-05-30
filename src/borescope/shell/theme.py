# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""A single small theme module: prompt shape and colours."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style

if TYPE_CHECKING:
    from .context import ShellContext

_STYLE = Style.from_dict(
    {
        'prompt.pebble': 'ansicyan bold',
        'prompt.path': 'ansiblue',
        'prompt.mark': 'ansiyellow bold',
    }
)


def style() -> Style:
    """Return the prompt_toolkit style used by the REPL."""
    return _STYLE


def prompt_fragments(ctx: ShellContext) -> FormattedText:
    """Render a bash-like prompt: ``pebble:<cwd>#``."""
    return FormattedText(
        [
            ('class:prompt.pebble', 'pebble'),
            ('', ':'),
            ('class:prompt.path', ctx.cwd),
            ('class:prompt.mark', '# '),
        ]
    )
