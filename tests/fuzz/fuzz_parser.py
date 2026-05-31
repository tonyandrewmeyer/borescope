# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Atheris fuzz harness targeting the borescope shell parser.

Entry points covered:
- ``parse_pipeline`` — tokenises and splits on ``|``, raising ParseError on
  unsupported syntax.  This exercises the entire lexer/splitter path.
- ``parse_and_expand`` — the REPL's primary call site; runs the same tokeniser
  then variable- and tilde-expands every word honouring quoting rules.
- ``expand`` — the single-token expansion utility used for completions and
  other callers that already have an unquoted token in hand.

Run locally (requires atheris and a libFuzzer-enabled Python build)::

    uv run python tests/fuzz/fuzz_parser.py                     # indefinite run
    uv run python tests/fuzz/fuzz_parser.py -atheris_runs=10000  # bounded run
    uv run python tests/fuzz/fuzz_parser.py tests/fuzz/corpus/  # with seed corpus

See tests/fuzz/README.md for full instructions.
"""

from __future__ import annotations

import contextlib
import sys

import atheris

with atheris.instrument_imports():
    from borescope.shell.parser import ParseError, expand, parse_and_expand, parse_pipeline

# Fixed variable names used to build a realistic-looking environment.
# Values are fuzz-derived so expansion paths are exercised with arbitrary data.
_ENV_KEYS = ('HOME', 'PATH', 'USER', 'APP', 'LOG_DIR')


def _fuzz_one_input(data: bytes) -> None:
    """Exercise all three public parser entry points with a single corpus item."""
    fdp = atheris.FuzzedDataProvider(data)

    # Build a small environment with fuzz-derived values.
    env = {key: fdp.ConsumeUnicodeNoSurrogates(32) for key in _ENV_KEYS}

    # Primary target: the full parse-and-expand pipeline used by the REPL.
    line = fdp.ConsumeUnicodeNoSurrogates(256)
    with contextlib.suppress(ParseError):
        parse_pipeline(line)

    with contextlib.suppress(ParseError):
        parse_and_expand(line, env)

    # Secondary target: the single-token expand utility.
    token = fdp.ConsumeUnicodeNoSurrogates(64)
    expand(token, env)


if __name__ == '__main__':
    atheris.Setup(sys.argv, _fuzz_one_input)
    atheris.Fuzz()
