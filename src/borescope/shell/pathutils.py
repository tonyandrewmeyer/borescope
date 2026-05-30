# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Container-side path helpers (POSIX semantics, regardless of the host OS)."""

from __future__ import annotations

import posixpath


def resolve(cwd: str, path: str, *, home: str = '/root') -> str:
    """Resolve *path* (relative to *cwd*) to an absolute, normalised path.

    Handles ``~`` / ``~/…`` (against *home*), relative paths, and ``.`` / ``..``.
    """
    if not path:
        return cwd
    if path == '~':
        path = home
    elif path.startswith('~/'):
        path = home + path[1:]
    if not path.startswith('/'):
        path = posixpath.join(cwd, path)
    return posixpath.normpath(path)
