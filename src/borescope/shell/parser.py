"""Line parsing for the v1 shell.

Deliberately tiny: one command at a time, with at most a single ``|`` between two
stages. No subshells, ``&&``/``||``/``;``, redirection, or background jobs — that
covers ~95% of debug-shell use at a fraction of the complexity, and the ``exec``
escape hatch handles the rest by running a real binary in the container.
"""

from __future__ import annotations

import re
import shlex
from collections.abc import Mapping

from ..errors import BorescopeError

_UNSUPPORTED = {
    ";": "sequencing (;)",
    "&": "background jobs (&)",
    "&&": "'&&'",
    "||": "'||'",
    ">": "output redirection (>)",
    ">>": "output redirection (>>)",
    "<": "input redirection (<)",
    "(": "subshells",
    ")": "subshells",
}

_VAR = re.compile(r"\$(\w+)|\$\{(\w+)\}")


class ParseError(BorescopeError):
    """Raised when a line cannot be parsed under the v1 grammar."""


def tokenize(line: str) -> list[str]:
    """Split *line* into tokens, keeping shell operators as their own tokens."""
    lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError as exc:  # e.g. unbalanced quotes
        raise ParseError(str(exc)) from exc


def parse_pipeline(line: str) -> list[list[str]]:
    """Parse *line* into a list of stages, each a list of argv tokens.

    Returns ``[]`` for a blank line. Raises :class:`ParseError` for unsupported
    syntax or more than one pipe.
    """
    tokens = tokenize(line)
    if not tokens:
        return []

    for tok in tokens:
        if tok in _UNSUPPORTED:
            raise ParseError(
                f"{_UNSUPPORTED[tok]} is not supported in v1. "
                "Use one command at a time (with at most a single '|')."
            )

    stages: list[list[str]] = []
    current: list[str] = []
    for tok in tokens:
        if tok == "|":
            stages.append(current)
            current = []
        else:
            current.append(tok)
    stages.append(current)

    if len(stages) > 2:
        raise ParseError("only a single pipe ('cmd1 | cmd2') is supported in v1.")
    if any(not stage for stage in stages):
        raise ParseError("syntax error near '|' (empty pipe stage).")
    return stages


def expand(token: str, env: Mapping[str, str]) -> str:
    """Expand a leading ``~`` and ``$VAR`` / ``${VAR}`` references using *env*."""
    if token == "~":
        token = env.get("HOME", "/root")
    elif token.startswith("~/"):
        token = env.get("HOME", "/root") + token[1:]

    def _sub(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2)
        return env.get(name, "")

    return _VAR.sub(_sub, token)
