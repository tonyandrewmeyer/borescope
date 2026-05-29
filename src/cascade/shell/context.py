"""Per-session shell state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..discovery import Target
    from ..transport import Transport


def _default_env() -> dict[str, str]:
    return {"HOME": "/root", "PWD": "/"}


@dataclass
class ShellContext:
    """The mutable state a command may read or update during a session."""

    transport: Transport
    target: Target
    cwd: str = "/"
    env: dict[str, str] = field(default_factory=_default_env)
    last_exit: int = 0

    @property
    def home(self) -> str:
        return self.env.get("HOME", "/root")

    def chdir(self, path: str) -> None:
        self.cwd = path
        self.env["PWD"] = path
