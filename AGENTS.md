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

## Commit Attribution
AI commits MUST include:
```
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

## Key Conventions
- New shell commands go in `src/borescope/shell/commands/` — subclass `Command`, auto-discovered.
- Keep the `Transport` interface narrow; it's the only code that touches Pebble.
- Before adding a command, check whether `exec <tool>` already covers it.
- See `CONTRIBUTING.md` for setup details.
