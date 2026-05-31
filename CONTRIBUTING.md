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
behaviour against the POSIX specification. Each task should cite the specific
clause it covers, by linking the relevant page under:

> POSIX.1-2017, Shell and Utilities (XCU) — https://pubs.opengroup.org/onlinepubs/9699919799/utilities/contents.html

The existing tasks (echo, ls, cat, head, tail, grep, …) are the templates;
re-use `tests/spread/lib.sh` for the per-task Pebble bring-up.

When borescope intentionally diverges from POSIX — v1 grammar choices, Pebble
API limits — name the task `…-divergence` and pin the *current* behaviour with a
comment explaining why. A future reconciliation then flips the task green by
reversal (red/green workflow), so divergences stay visible rather than rotting
into forgotten gaps.

## Documentation

The docs site lives under `docs/`. Sources are Markdown in `docs/src/*.md`;
the committed HTML under `docs/docs/` is generated and checked in (GitHub Pages
serves it directly). After editing any source, rebuild and commit both:

```console
uv run python docs/src/_build.py     # or: tox -e docs
uv run python docs/src/_build.py --check   # what CI runs
```

See `docs/README.md` for frontmatter and authoring conventions.

## Design notes

- Keep the **Transport** interface narrow; it's the only code that touches Pebble,
  and the seam behind which a future Go reimplementation would sit.
- New commands go in `src/borescope/shell/commands/`. They subclass `Command` and are
  auto-discovered — adding one should be small and self-contained.
- Before adding a command, ask whether `exec <tool>` already covers it. Most things
  do.

## Releases

Releases are tag-driven: pushing a `v*` tag to `main` triggers
[`publish.yaml`](.github/workflows/publish.yaml), which gates on CI and then
publishes to PyPI (Trusted Publishing + Sigstore attestations), the snap store
(`latest/edge`), and creates a GitHub release with the build artefacts.

### Where the version lives

The same version is repeated in four places — bump all of them in one commit:

| File | Format | Example |
|---|---|---|
| `pyproject.toml` (`version = "..."`) | [PEP 440](https://peps.python.org/pep-0440/) | `0.1.0b2` |
| `snap/snapcraft.yaml` (`version: '...'`) | snapcraft `MAJOR.MINOR.PATCH-PRERELEASE` | `0.1.0-b2` |
| `docs/src/tutorial.md` (`borescope --version` output) | PEP 440 | `borescope 0.1.0b2` |
| `docs/src/howto-snapshot.md` (`borescope_version` field in the snapshot JSON) | PEP 440 | `0.1.0b2` |

The two snap shapes differ by a single hyphen: snapcraft rejects `0.1.0b2` and
PyPI rejects `0.1.0-b2`. `borescope --version` reads from the installed package
metadata, so the docs literals are illustrative — they need manual updating to
match.

### Steps

1. Create a release branch: `git checkout -b release/<version>`.
2. Bump the version in all four files above.
3. Rebuild the docs (the committed HTML must match): `uv run python docs/src/_build.py`.
4. Verify: `tox -e lint && tox -e unit && uv run python docs/src/_build.py --check`.
5. Commit, push, open a PR. Per the repo's branch-protection rules a release
   PR still goes through CI like any other change.
6. After the PR merges, tag the merge commit on `main` and push the tag — that
   fires the publish workflow:
   ```console
   git checkout main && git pull
   git tag v<version>             # e.g. v0.1.0b2; matches the PEP 440 form
   git push origin v<version>
   ```

### Retrying a failed publish

If the snap (or any other job) fails after PyPI has already accepted the
artefact, the same workflow can be re-run via `workflow_dispatch` against
`main` — PyPI's `skip-existing` swallows the duplicate, and only the failing
job re-runs. The GitHub-release job is skipped on workflow_dispatch (it only
fires on actual tag pushes), so it has to be created manually if the tag-push
run failed before reaching it.

## License

By contributing, you agree your contributions are licensed under Apache-2.0.
