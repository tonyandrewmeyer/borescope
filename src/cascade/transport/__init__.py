"""Transport layer (A) — "talk to a Pebble".

A narrow interface the shell layer talks to, with two thin backends over an
``ops.pebble.Client``-shaped object:

- :func:`~cascade.transport.cli_transport.build_cli_transport` (v1 primary) — runs
  the workload container's ``pebble`` via ``juju ssh``.
- :func:`~cascade.transport.socket_transport.build_socket_transport` (secondary) —
  the real ``ops.pebble.Client`` on a directly-reachable socket.

The shell layer only ever sees :class:`Transport`, so the backend choice — and a
future Go reimplementation of just this layer — stays contained.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import datetime
    from typing import BinaryIO, TextIO

    import ops


class Transport(Protocol):
    """The subset of ``ops.pebble.Client`` cascade uses.

    Both backends (``shimmer.PebbleCliClient`` and ``ops.pebble.Client``) satisfy
    this structurally; it exists to document and contain the only surface that ever
    touches Pebble.
    """

    # -- system / liveness -------------------------------------------------
    def get_system_info(self) -> ops.pebble.SystemInfo: ...

    # -- services ----------------------------------------------------------
    def get_services(
        self, names: Iterable[str] | None = None
    ) -> list[ops.pebble.ServiceInfo]: ...
    def start_services(
        self, services: Iterable[str], timeout: float = 30.0, delay: float = 0.1
    ) -> ops.pebble.ChangeID: ...
    def stop_services(
        self, services: Iterable[str], timeout: float = 30.0, delay: float = 0.1
    ) -> ops.pebble.ChangeID: ...
    def restart_services(
        self, services: Iterable[str], timeout: float = 30.0, delay: float = 0.1
    ) -> ops.pebble.ChangeID: ...
    def replan_services(
        self, timeout: float = 30.0, delay: float = 0.1
    ) -> ops.pebble.ChangeID: ...
    def send_signal(self, sig: int | str, services: Iterable[str]) -> None: ...

    # -- plan / changes ----------------------------------------------------
    def get_plan(self) -> ops.pebble.Plan: ...
    def get_changes(
        self,
        select: ops.pebble.ChangeState = ...,
        service: str | None = None,
    ) -> list[ops.pebble.Change]: ...
    def get_change(self, change_id: ops.pebble.ChangeID) -> ops.pebble.Change: ...

    # -- checks ------------------------------------------------------------
    def get_checks(
        self,
        level: ops.pebble.CheckLevel | None = None,
        names: Iterable[str] | None = None,
    ) -> list[ops.pebble.CheckInfo]: ...

    # -- notices -----------------------------------------------------------
    def get_notices(
        self,
        *,
        users: Any = None,
        user_id: int | None = None,
        types: Iterable[Any] | None = None,
        keys: Iterable[str] | None = None,
    ) -> list[ops.pebble.Notice]: ...
    def get_notice(self, id: str) -> ops.pebble.Notice: ...
    def notify(
        self,
        type: ops.pebble.NoticeType,
        key: str,
        *,
        data: dict[str, str] | None = None,
        repeat_after: datetime.timedelta | None = None,
    ) -> str: ...

    # -- filesystem --------------------------------------------------------
    def pull(
        self, path: str, *, encoding: str | None = "utf-8"
    ) -> BinaryIO | TextIO: ...
    def push(
        self,
        path: str,
        source: Any,
        *,
        encoding: str = "utf-8",
        make_dirs: bool = False,
        permissions: int | None = None,
        user_id: int | None = None,
        user: str | None = None,
        group_id: int | None = None,
        group: str | None = None,
    ) -> None: ...
    def list_files(
        self, path: str, *, pattern: str | None = None, itself: bool = False
    ) -> list[ops.pebble.FileInfo]: ...
    def make_dir(
        self,
        path: str,
        *,
        make_parents: bool = False,
        permissions: int | None = None,
        user_id: int | None = None,
        user: str | None = None,
        group_id: int | None = None,
        group: str | None = None,
    ) -> None: ...
    def remove_path(self, path: str, *, recursive: bool = False) -> None: ...

    # -- exec --------------------------------------------------------------
    def exec(
        self, command: list[str], **kwargs: Any
    ) -> ops.pebble.ExecProcess[Any]: ...


def open_transport(
    *,
    unit: str,
    container: str | None,
    model: str | None = None,
    juju_binary: str = "juju",
    socket_path: str | None = None,
) -> Transport:
    """Open the appropriate transport.

    If *socket_path* is given (a directly-reachable Pebble socket), use the fast
    ``SocketTransport``; otherwise use the ``CliTransport`` relay over ``juju ssh``,
    which is the v1 default for laptop-to-remote-cluster use.
    """
    if socket_path:
        from .socket_transport import build_socket_transport

        return build_socket_transport(socket_path)

    from .cli_transport import build_cli_transport

    return build_cli_transport(
        unit=unit, container=container, model=model, juju_binary=juju_binary
    )


__all__ = ["Transport", "open_transport"]
