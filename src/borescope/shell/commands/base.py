# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Command base class, result type, and the auto-discovery registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from ..context import ShellContext


@dataclass
class Result:
    """The outcome of running a command stage."""

    output: str = ''
    error: str = ''
    code: int = 0

    @classmethod
    def ok(cls, output: str = '') -> Result:
        return cls(output=output, code=0)

    @classmethod
    def fail(cls, error: str, code: int = 1) -> Result:
        return cls(error=error, code=code)


class ExitShell(Exception):  # noqa: N818 - control-flow signal, not an error
    """Raised by ``exit`` to leave the REPL cleanly."""

    def __init__(self, code: int = 0):
        super().__init__(code)
        self.code = code


class Command:
    """Base class for all built-in commands.

    Subclasses set ``name`` (and optionally ``aliases``) and implement
    :meth:`run`. They are auto-discovered by :func:`build_registry`, so adding a
    command is just defining a subclass — no registration boilerplate.
    """

    name: ClassVar[str] = ''
    aliases: ClassVar[tuple[str, ...]] = ()
    summary: ClassVar[str] = ''
    usage: ClassVar[str] = ''
    # Streaming commands write directly to the terminal and cannot appear in a
    # pipe (e.g. `logs --follow`, `tail -f`).
    streaming: ClassVar[bool] = False

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        raise NotImplementedError


def _iter_command_classes(root: type[Command]) -> list[type[Command]]:
    found: list[type[Command]] = []
    for sub in root.__subclasses__():
        found.extend(_iter_command_classes(sub))
        if getattr(sub, 'name', ''):
            found.append(sub)
    return found


def build_registry() -> dict[str, Command]:
    """Instantiate every discovered command, keyed by name and alias."""
    # Importing the package registers all Command subclasses.
    from . import import_all

    import_all()

    registry: dict[str, Command] = {}
    for klass in _iter_command_classes(Command):
        instance = klass()
        registry[klass.name] = instance
        for alias in klass.aliases:
            registry[alias] = instance
    return registry
