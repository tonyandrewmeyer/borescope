# Contributing to cascade

Thanks for your interest in cascade. It's an early-stage project with a deliberately
small surface area; the guiding principle is **ship a minimal core and grow on
request** rather than reimplement every shell utility.

## Development setup

cascade uses [`uv`](https://docs.astral.sh/uv/):

```console
uv venv
uv pip install -e '.[dev]'
pre-commit install
```

## Running checks

```console
tox -e lint            # ruff + ty
tox -e unit            # unit tests (no pebble binary / juju needed)
tox -e integration     # integration tests (needs a local `pebble` binary)
```

The unit suite must pass with neither `juju` nor a real cluster present —
`JujuSshRunner` argv construction and discovery parsing are covered with mocks.
Integration tests run against a local `pebble` binary.

## Design notes

- Keep the **Transport** interface narrow; it's the only code that touches Pebble,
  and the seam behind which a future Go reimplementation would sit.
- New commands go in `src/cascade/shell/commands/`. They subclass `Command` and are
  auto-discovered — adding one should be small and self-contained.
- Before adding a command, ask whether `exec <tool>` already covers it. Most things
  do.

## License

By contributing, you agree your contributions are licensed under Apache-2.0.
