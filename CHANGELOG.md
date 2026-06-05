# Changelog

All notable changes to borescope are documented here.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-06-05

First stable release. The public API surface (the `Transport` protocol,
`open_transport()`, `Shell`, `ShellContext`, and the CLI) is committed to
semantic-versioning compatibility from this release on; breaking changes
will require a 2.0.

### Added

- Initial Pebble-version compatibility reference under
  [`docs/src/reference-pebble.md`](docs/src/reference-pebble.md): the
  ssh/exec (shimmer) transports require Pebble ≥ 1.31; the direct socket
  path likely works against older Pebbles but is currently only tested
  against 1.31.0.

### Changed

- Bumped the `pebble-shimmer` floor to `>=1.0.0` (was `>=1.0.0b3`).
- PyPI classifier bumped to `Development Status :: 5 - Production/Stable`.
- Snap grade bumped to `stable`.
- Dropped the snap's `personal-files` plug. Shell history now lives in the
  snap-private `$HOME` (`~/snap/borescope/current/.local/state/borescope/`)
  rather than the real `~/.local/state/borescope/`. The trade-off is that
  history is per-installation: uninstalling the snap discards it, and snap
  vs pipx installs do not share a history file. In return, snap revisions
  no longer require Snap Store manual review.

## [0.1.0b2] — 2026-05-31

- First strict-confinement snap (`personal-files` for per-target shell
  history under `$HOME/.local/state/borescope`).

## [0.1.0b1] — 2026-05-31

- File transfer (`push`/`pull`) wired through the CLI relay.

## [0.1.0.dev1] — 2026-05-30

- Early development build.

## [0.1.0.dev0] — 2026-05-30

- Initial development build.
