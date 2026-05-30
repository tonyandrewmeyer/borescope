"""File-backed command history, keyed per controller/model/unit."""

from __future__ import annotations

import os
import pathlib
from typing import TYPE_CHECKING

from prompt_toolkit.history import FileHistory, History, InMemoryHistory

if TYPE_CHECKING:
    from ..discovery import Target


def history_path(target: Target) -> pathlib.Path:
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(
        pathlib.Path.home(), ".local", "state"
    )
    return pathlib.Path(base, "borescope", "history", target.history_key)


def history_for(target: Target) -> History:
    """Return a per-target :class:`History`, falling back to in-memory on error."""
    try:
        path = history_path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        return FileHistory(str(path))
    except OSError:  # pragma: no cover - unwritable home dir
        return InMemoryHistory()
