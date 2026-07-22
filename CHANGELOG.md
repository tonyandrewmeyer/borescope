# Changelog

All notable changes to borescope are documented here.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- When the reader of borescope's piped output exits early
  (`borescope … --command 'cat big' | head`), borescope now dies the way
  a SIGPIPE'd tool does — exit status 141, nothing on stderr — instead of
  spilling a `BrokenPipeError` traceback. See
  [#87](https://github.com/tonyandrewmeyer/borescope/issues/87).

- `notice <id>` renders the notice's data payload as indented YAML instead
  of a Python dict repr. The Data row interpolated the dict straight into
  an f-string, so `dict.__repr__` leaked into the output
  (`Data:        {'k': 'v'}`). It now matches `plan`'s YAML rendering, and
  `pebble notice`'s quoting. See
  [#37](https://github.com/tonyandrewmeyer/borescope/issues/37).
- `logs` and `--snapshot` no longer require a `pebble` binary on the host
  when running against a directly-reachable socket (`--socket`, `--here`).
  `ops.pebble.Client` has no log API, so these used to shell out to a real
  Pebble client, and `--socket` failed with
  `logs: [Errno 2] No such file or directory: 'pebble'` if none was
  installed. borescope now reads Pebble's `/v1/logs` endpoint over the
  socket itself, rendering entries identically to the Pebble CLI. See
  [#75](https://github.com/tonyandrewmeyer/borescope/issues/75).

## [1.0.2] — 2026-06-05

Snap release. Replaces 1.0.1, which was withdrawn from the store review
queue.

### Changed

- Snap now uses the auto-connecting `juju-client-observe` plug instead
  of a `personal-files` plug for ``$HOME/.local/share/juju``. The
  `personal-files` interface triggers manual store review on every
  revision until an auto-connect declaration is granted; falling back
  to `juju-client-observe` keeps releases ungated. The trade-off is
  read-only host access — to give the bundled juju a writable JUJU_DATA
  (it refreshes cookies/macaroons on the fly), borescope now copies
  the host directory into `$SNAP_USER_COMMON/juju` at startup and
  points `JUJU_DATA` at the copy. See
  [#31](https://github.com/tonyandrewmeyer/borescope/issues/31)
  for the plan to request the auto-connect declaration and drop the
  staging.

### Added

- `borescope.snap` module with `stage_juju_data()`, the startup hook
  that copies host JUJU_DATA into the snap's writable home.

### Limitations introduced by the staging

- `juju login` / `juju switch` done *inside* a borescope session do
  not propagate back to the host. Run them with the host's juju.
- Macaroon refreshes inside borescope are session-local; if a macaroon
  expires on the host, refresh it there.

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
