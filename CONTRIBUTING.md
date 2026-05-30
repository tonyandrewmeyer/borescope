# Contributing to borescope

Thanks for your interest in borescope. It's an early-stage project with a deliberately
small surface area; the guiding principle is **ship a minimal core and grow on
request** rather than reimplement every shell utility.

## Development setup

borescope uses [`uv`](https://docs.astral.sh/uv/):

```console
uv sync --group dev
pre-commit install
```

### Co-developing shimmer

borescope depends on the published [`pebble-shimmer`](https://pypi.org/project/pebble-shimmer/).
If you need to change shimmer and borescope together, install your local checkout
editable *into borescope's venv* (don't commit a path override — it breaks CI and
fresh clones):

```console
uv pip install -e ../shimmer    # re-run after any `uv sync`, which resets it
```

## Running checks

```console
tox -e lint            # ruff + ty
tox -e unit            # unit tests (no pebble binary / juju needed)
tox -e integration     # integration tests (needs a local `pebble` binary)
spread lxd:            # POSIX-conformance suite (real VM, real Pebble; needs LXD)
```

The unit suite must pass with neither `juju` nor a real cluster present —
`JujuSshRunner` argv construction and discovery parsing are covered with mocks.
Integration tests run against a local `pebble` binary. The spread suite spins up
a throwaway Ubuntu VM via LXD, installs Pebble (pinned by `PEBBLE_VERSION` in
[`spread.yaml`](spread.yaml)), and drives borescope through one isolated task per
spec clause; on GitHub Actions the same matrix runs on the `github-ci` backend.

## Spec-based tests

Any change to a command, built-in, or shell-language feature MUST be accompanied
by one or more spread tasks under `tests/spread/<name>/task.yaml` that pin the
behavior against the POSIX specification. Each task should cite the specific
clause it covers, by linking the relevant page under:

> POSIX.1-2017, Shell and Utilities (XCU) — https://pubs.opengroup.org/onlinepubs/9699919799/utilities/contents.html

The existing tasks (echo, ls, cat, head, tail, grep, …) are the templates;
re-use `tests/spread/lib.sh` for the per-task Pebble bring-up.

When borescope intentionally diverges from POSIX — v1 grammar choices, Pebble
API limits — name the task `…-divergence` and pin the *current* behavior with a
comment explaining why. A future reconciliation then flips the task green by
reversal (red/green workflow), so divergences stay visible rather than rotting
into forgotten gaps.

## Design notes

- Keep the **Transport** interface narrow; it's the only code that touches Pebble,
  and the seam behind which a future Go reimplementation would sit.
- New commands go in `src/borescope/shell/commands/`. They subclass `Command` and are
  auto-discovered — adding one should be small and self-contained.
- Before adding a command, ask whether `exec <tool>` already covers it. Most things
  do.

## License

By contributing, you agree your contributions are licensed under Apache-2.0.
