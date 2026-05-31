# Fuzz Harness

This directory contains an [Atheris](https://github.com/google/atheris) fuzz harness
for the borescope shell parser.

## Entry Points

The harness (`fuzz_parser.py`) targets three public functions from
`borescope.shell.parser`:

| Function | Rationale |
|---|---|
| `parse_pipeline(line)` | Full tokeniser + stage-splitter path; the broadest surface. |
| `parse_and_expand(line, env)` | The REPL's primary call site — adds variable and tilde expansion on top of tokenising. |
| `expand(token, env)` | Single-token expansion utility used by completion and other callers. |

The internal tokeniser (`_lex`) is exercised indirectly through `parse_pipeline` and
`parse_and_expand`.  Targeting the public API is preferred: it tests the contract, not
the implementation detail, and will catch crashes regardless of internal refactors.

## Seed Corpus

`corpus/` contains hand-written seeds covering common patterns:

- Simple commands, pipes, and flags
- Single-quoted, double-quoted, and mixed quoting
- Variable expansion (`$VAR`, `${VAR}`)
- Tilde expansion (`~`, `~/...`)
- Backslash escapes
- Whitespace-only and empty input

Atheris uses these as starting points and mutates them to explore new paths.

## Prerequisites

Atheris requires a **libFuzzer-enabled Python build**.  On Ubuntu/Debian:

```bash
sudo apt-get install clang python3-dev
pip install atheris
```

With `uv` (already in the dev dependency group):

```bash
uv sync --group dev
```

> **Note:** `atheris` links against `libFuzzer`, which ships with Clang.  If your
> system Python was built with GCC you may see a linker error.  Using the Clang-built
> Python from `uv` (e.g. via `pyenv` with `CC=clang`) resolves this.  Alternatively,
> install `atheris` with `pip install atheris` inside a Clang-enabled venv.

## Running Locally

```bash
# Bounded smoke test (100 iterations) — no corpus growth
uv run python tests/fuzz/fuzz_parser.py -atheris_runs=100

# With the seed corpus (recommended starting point)
uv run python tests/fuzz/fuzz_parser.py tests/fuzz/corpus/ -atheris_runs=10000

# Indefinite run — Ctrl-C to stop; interesting inputs are saved to corpus/
uv run python tests/fuzz/fuzz_parser.py tests/fuzz/corpus/

# Reproduce a specific crashing input
uv run python tests/fuzz/fuzz_parser.py path/to/crash_file
```

## CI Integration

The harness is **not** wired into CI.  Running a fuzz harness in CI requires either a
time-bounded job (e.g. 60 s per run with `-atheris_runs=N` capped by a wall-clock
limit) or integration with a dedicated fuzzing service such as
[OSS-Fuzz](https://github.com/google/oss-fuzz).  Both options involve non-trivial
decisions around budget, corpus management, and triage workflow.  That work is tracked
as a follow-up in [#11](https://github.com/tonyandrewmeyer/borescope/issues/11).
