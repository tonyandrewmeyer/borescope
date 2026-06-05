# Changelog

All notable changes to borescope are documented here.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] — 2026-06-05

Snap-only release. PyPI and Snap Store contents are otherwise identical
to 1.0.0.

### Fixed

- **Snap was broken on every invocation in 1.0.0.** `bin/borescope`'s
  `#!/usr/bin/env python3.12` shebang resolved against the snap's PATH
  (`$SNAP/usr/sbin:$SNAP/usr/bin:...`) and picked the bare stage-package
  interpreter at `$SNAP/usr/bin/python3.12` instead of the venv'd one at
  `$SNAP/bin/python3.12`; the wrong interpreter never saw `pyvenv.cfg`
  and so couldn't find the `borescope` module. Fixed by prepending
  `$SNAP/bin` to the app's `PATH` so the venv interpreter wins.
- **Snap couldn't talk to Juju.** Under strict confinement, snap-to-snap
  exec of `/snap/bin/juju` is blocked, and the snap's mount namespace
  hides any non-snap juju binary on the host. Bundled Juju 4 inside the
  snap via `stage-snaps: [juju/4/stable]` (same pattern as
  [jhack](https://github.com/canonical/jhack)) so the relay transport
  execs an in-snap juju. Juju 4 clients talk to both 3.x and 4.x
  controllers, so this is forward- and backward-compatible.

### Added

- `network` and `network-bind` plugs (the bundled juju's k8s API proxy
  binds a local ephemeral port).
- `dot-local-share-juju` `personal-files` plug for write access to
  `$HOME/.local/share/juju` (JUJU_DATA). Needs a manual
  `sudo snap connect borescope:dot-local-share-juju` after install.
- Snap metadata fields previously only present on the store side:
  `title`, `contact`, `license`, `issues`, `source-code`, `website`.

### Removed

- `juju-client-observe` plug, superseded by `dot-local-share-juju` (the
  bundled juju needs write access to JUJU_DATA, not just read).

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
