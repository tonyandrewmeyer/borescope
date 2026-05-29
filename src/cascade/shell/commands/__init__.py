"""Built-in commands and the registry that discovers them."""

from __future__ import annotations

from .base import Command, ExitShell, Result, build_registry


def import_all() -> None:
    """Import every command module so its ``Command`` subclasses register."""
    from . import basic, execcmd, filesystem, pebble  # noqa: F401


__all__ = ["Command", "ExitShell", "Result", "build_registry", "import_all"]
