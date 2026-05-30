# Agent Instructions

## Package Manager
Use **uv**: `uv sync --group dev`, `uv run <cmd>`

## File-Scoped Commands
| Task | Command |
|------|---------|
| Lint | `uv run ruff check path/to/file.py` |
| Format | `uv run ruff format path/to/file.py` |
| Typecheck | `uv run ty check path/to/file.py` |
| Test | `uv run pytest tests/test_file.py` |

Full suite: `tox -e lint`, `tox -e unit`, `tox -e integration` (integration requires a local `pebble` binary).

POSIX-conformance suite (real VM, real Pebble): `spread lxd:ubuntu-24.04:tests/spread/` — see [`tests/spread/`](tests/spread/) and the top-level [`spread.yaml`](spread.yaml).

## Commit Attribution
AI commits MUST include a `Co-Authored-By` trailer using your own model name. For example:
```
Co-Authored-By: Claude <noreply@anthropic.com>
```
Replace `Claude` with your actual model name (e.g. `Claude Opus 4.8`, `Claude Sonnet 4.6`, `Gemini 2.5 Pro`).

## Key Conventions
- New shell commands go in `src/borescope/shell/commands/` — subclass `Command`, auto-discovered.
- Keep the `Transport` interface narrow; it's the only code that touches Pebble.
- Before adding a command, check whether `exec <tool>` already covers it.
- See `CONTRIBUTING.md` for setup details.

## Spec-Based Tests
Any new or changed command, built-in, or shell-language feature MUST add one or more
spread tasks under `tests/spread/<name>/task.yaml` that pin the behaviour against
the POSIX specification. Each task should cite the specific clause it covers:

> POSIX.1-2017, Shell and Utilities (XCU) — https://pubs.opengroup.org/onlinepubs/9699919799/utilities/contents.html

If a change intentionally diverges from POSIX (v1 design choices, Pebble-API limits),
name the task `…-divergence` and include a comment explaining *why* the divergence
exists, so a future reconciliation flips the task green by reversal.
