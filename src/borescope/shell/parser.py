# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Line parsing for the v1 shell.

Deliberately tiny: one command at a time, with at most a single ``|`` between two
stages. No subshells, ``&&``/``||``/``;``, redirection, or background jobs — that
covers ~95% of debug-shell use at a fraction of the complexity, and the ``exec``
escape hatch handles the rest by running a real binary in the container.

The lexer tracks how each slice of a word was quoted so expansion can honour shell
rules: single quotes keep ``$VAR`` / ``~`` literal, double quotes expand ``$VAR``
but not ``~``, and an unquoted leading ``~`` expands to ``$HOME``.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from ..errors import BorescopeError

_UNSUPPORTED = {
    ';': 'sequencing (;)',
    '&': 'background jobs (&)',
    '&&': "'&&'",
    '||': "'||'",
    '>': 'output redirection (>)',
    '>>': 'output redirection (>>)',
    '<': 'input redirection (<)',
    '(': 'subshells',
    ')': 'subshells',
}

# Characters shlex would treat as punctuation; the lexer emits runs of them as
# standalone operator tokens (so ``&&``/``>>`` group, ``a|b`` splits).
_PUNCT = set('();<>|&')

# Backslash escapes recognised inside double quotes (matching POSIX sh).
_DQ_ESCAPES = {'"', '\\', '$', '`'}

_VAR = re.compile(r'\$(\w+)|\$\{(\w+)\}')


class ParseError(BorescopeError):
    """Raised when a line cannot be parsed under the v1 grammar."""


# A quoting mode for a slice of a word: single-quoted (fully literal),
# double-quoted (``$VAR`` expands, ``~`` does not), or unquoted (both expand).
_SQ, _DQ, _UNQ = 'sq', 'dq', 'unq'


@dataclass(frozen=True)
class _Word:
    """A shell word as quote-tagged segments, e.g. ``a'$b'"$c"`` → three segments."""

    segments: tuple[tuple[str, str], ...]

    def literal(self) -> str:
        """Join segments verbatim (quotes already stripped), without expansion."""
        return ''.join(text for text, _ in self.segments)


def _lex(line: str) -> list[_Word | str]:
    """Split *line* into word and operator tokens, preserving per-slice quoting.

    Words become :class:`_Word`; shell operators (``|``, ``&&``, ``>>``, …) become
    plain ``str`` tokens. Raises :class:`ParseError` on an unbalanced quote.
    """
    tokens: list[_Word | str] = []
    segments: list[tuple[str, str]] = []
    has_word = False
    i, n = 0, len(line)

    def flush() -> None:
        nonlocal segments, has_word
        if has_word:
            tokens.append(_Word(tuple(segments)))
        segments = []
        has_word = False

    while i < n:
        ch = line[i]
        if ch.isspace():
            flush()
            i += 1
        elif ch in _PUNCT:
            flush()
            j = i
            while j < n and line[j] in _PUNCT:
                j += 1
            tokens.append(line[i:j])
            i = j
        elif ch == "'":
            end = line.find("'", i + 1)
            if end == -1:
                raise ParseError('no closing quotation')
            has_word = True
            segments.append((line[i + 1 : end], _SQ))
            i = end + 1
        elif ch == '"':
            has_word = True
            buf: list[str] = []
            i += 1
            while i < n and line[i] != '"':
                if line[i] == '\\' and i + 1 < n and line[i + 1] in _DQ_ESCAPES:
                    buf.append(line[i + 1])
                    i += 2
                else:
                    buf.append(line[i])
                    i += 1
            if i >= n:
                raise ParseError('no closing quotation')
            segments.append((''.join(buf), _DQ))
            i += 1
        elif ch == '\\':
            has_word = True
            if i + 1 < n:
                segments.append((line[i + 1], _SQ))  # escaped char is literal
                i += 2
            else:
                i += 1
        else:
            has_word = True
            j = i
            while (
                j < n
                and not line[j].isspace()
                and line[j] not in _PUNCT
                and line[j] not in '\'"\\'
            ):
                j += 1
            segments.append((line[i:j], _UNQ))
            i = j

    flush()
    return tokens


def _split_stages(tokens: list[_Word | str]) -> list[list[_Word]]:
    """Reject unsupported operators and split on ``|`` into stages of words."""
    for tok in tokens:
        if isinstance(tok, str) and tok != '|':
            message = _UNSUPPORTED.get(tok, f"'{tok}'")
            raise ParseError(
                f'{message} is not supported in v1. '
                "Use one command at a time (with at most a single '|')."
            )

    stages: list[list[_Word]] = []
    current: list[_Word] = []
    for tok in tokens:
        if tok == '|':
            stages.append(current)
            current = []
        else:
            assert isinstance(tok, _Word)
            current.append(tok)
    stages.append(current)

    if len(stages) > 2:
        raise ParseError("only a single pipe ('cmd1 | cmd2') is supported in v1.")
    if any(not stage for stage in stages):
        raise ParseError("syntax error near '|' (empty pipe stage).")
    return stages


def parse_pipeline(line: str) -> list[list[str]]:
    """Parse *line* into a list of stages, each a list of (unexpanded) argv tokens.

    Returns ``[]`` for a blank line. Raises :class:`ParseError` for unsupported
    syntax or more than one pipe. Quotes are stripped but variables are *not*
    expanded; use :func:`parse_and_expand` for that.
    """
    tokens = _lex(line)
    if not tokens:
        return []
    return [[word.literal() for word in stage] for stage in _split_stages(tokens)]


def parse_and_expand(line: str, env: Mapping[str, str]) -> list[list[str]]:
    """Like :func:`parse_pipeline`, but expand each word honouring its quoting."""
    tokens = _lex(line)
    if not tokens:
        return []
    return [[_expand_word(word, env) for word in stage] for stage in _split_stages(tokens)]


def _expand_vars(text: str, env: Mapping[str, str]) -> str:
    """Substitute ``$VAR`` / ``${VAR}`` from *env* (unknown names → empty)."""

    def _sub(match: re.Match[str]) -> str:
        return env.get(match.group(1) or match.group(2), '')

    return _VAR.sub(_sub, text)


def _expand_word(word: _Word, env: Mapping[str, str]) -> str:
    """Expand a quote-tagged word: ``$VAR`` per quoting, leading unquoted ``~``."""
    parts: list[str] = []
    for index, (text, mode) in enumerate(word.segments):
        if mode == _SQ:
            parts.append(text)  # single quotes: fully literal
        elif mode == _DQ:
            parts.append(_expand_vars(text, env))  # no tilde inside double quotes
        else:
            # A leading ``~`` expands only at the very start of an unquoted word.
            if index == 0 and (text == '~' or text.startswith('~/')):
                home = env.get('HOME', '/root')
                text = home if text == '~' else home + text[1:]
            parts.append(_expand_vars(text, env))
    return ''.join(parts)


def expand(token: str, env: Mapping[str, str]) -> str:
    """Expand a leading ``~`` and ``$VAR`` / ``${VAR}`` in an *unquoted* token."""
    if token == '~':  # noqa: S105 - shell token, not a credential
        token = env.get('HOME', '/root')
    elif token.startswith('~/'):
        token = env.get('HOME', '/root') + token[1:]
    return _expand_vars(token, env)
