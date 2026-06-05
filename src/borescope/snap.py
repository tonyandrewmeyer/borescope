# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Snap-environment helpers.

Under strict confinement, the snap can only *read* the host's Juju
configuration directory via the ``juju-client-observe`` interface — it
cannot write to it. Borescope's bundled juju, however, refreshes
macaroons and cookies on the fly and will fail the moment it tries to
update ``cookies.yaml`` or ``accounts.yaml``.

Personal-files would grant write access but pushes the snap into manual
store review on every revision until an auto-connect declaration is
granted. To stay on auto-connecting interfaces, we instead stage a copy
of the host's ``~/.local/share/juju`` into the snap's writable
``$SNAP_USER_COMMON/juju`` on every invocation, point ``JUJU_DATA`` at
the copy, and let the bundled juju write freely to it.

Trade-offs of staging:

* The copy is one-way (host → snap). Logins/model-switches you do
  *inside* a borescope session never write back to the host, so they
  vanish at the end of the session. Do ``juju login`` / ``juju
  switch`` *outside* borescope.
* The copy happens at every borescope invocation, so host-side changes
  are picked up on the next run. For typical use (debug a workload,
  exit, move on) this is invisible.

This module is a no-op outside the snap, so unit tests and PyPI
installs are unaffected.
"""

from __future__ import annotations

import os
import pwd
import shutil


def stage_juju_data() -> None:
    """If running inside the borescope snap, copy host JUJU_DATA into writable storage.

    The snap's ``apps.borescope.environment`` block sets
    ``JUJU_DATA=$SNAP_USER_COMMON/juju``; this function populates that
    directory by copying ``~/.local/share/juju`` (read-only via
    ``juju-client-observe``) into it on every invocation. The bundled
    juju then reads and writes the copy freely.

    No-op outside the snap, and no-op if the host has no JUJU_DATA
    (the bundled juju will surface "no controllers registered" itself).
    """
    if os.environ.get('SNAP_NAME') != 'borescope':
        return
    snap_user_common = os.environ.get('SNAP_USER_COMMON')
    if not snap_user_common:
        return
    real_home = pwd.getpwuid(os.getuid()).pw_dir
    source = os.path.join(real_home, '.local', 'share', 'juju')
    if not os.path.isdir(source):
        return
    target = os.path.join(snap_user_common, 'juju')
    shutil.copytree(source, target, dirs_exist_ok=True, symlinks=True)
