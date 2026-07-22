# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Native ``/v1/logs`` client for the direct-socket transport.

``ops.pebble.Client`` doesn't expose Pebble's log endpoint, so for a long time
``logs`` (and ``--snapshot``) shelled out to a real ``pebble`` binary even in
``--socket`` mode — which meant ``--socket`` silently required Pebble on the host.
This module speaks the endpoint directly over the unix socket instead: stdlib
HTTP, no ``pebble`` binary, no ``ops`` import on the path.

The wire format is newline-delimited JSON, one object per entry::

    {"time":"2026-07-22T08:37:54.39Z","service":"ticker","message":"tick 49"}

which we render exactly as the Pebble CLI does::

    2026-07-22T08:37:54.390Z [ticker] tick 49
"""

from __future__ import annotations

import datetime
import http.client
import json
import socket
import urllib.parse
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

# Pebble's own default for `logs -n` (see `pebble logs --help`).
DEFAULT_LOG_LINES = 30

# `-n all` on the CLI; the API takes -1 to mean "everything buffered".
ALL_LOGS = -1


class LogsError(Exception):
    """The Pebble log endpoint could not be read."""


def parse_n(value: str) -> int:
    """Parse a ``-n`` value the way the Pebble CLI does (an int, or ``all``)."""
    if value == 'all':
        return ALL_LOGS
    try:
        n = int(value)
    except ValueError:
        raise LogsError(
            f'expected n to be a non-negative integer or "all", not "{value}"'
        ) from None
    if n < 0:
        raise LogsError(f'expected n to be a non-negative integer or "all", not "{value}"')
    return n


class _UnixHTTPConnection(http.client.HTTPConnection):
    """An ``HTTPConnection`` that dials a unix socket instead of a TCP port."""

    def __init__(self, socket_path: str, timeout: float | None = None):
        # The host is arbitrary — it only ends up in the Host header — but Pebble
        # rejects requests that look cross-origin, so keep it boring.
        super().__init__('localhost')
        self.socket_path = socket_path
        self.timeout = timeout  # type: ignore[assignment]  # None means "no timeout"

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if self.timeout is not None:
            sock.settimeout(self.timeout)
        try:
            sock.connect(self.socket_path)
        except OSError as exc:
            sock.close()
            raise LogsError(f'could not connect to Pebble at {self.socket_path!r}: {exc}') from exc
        self.sock = sock


def _format_time(raw: str) -> str:
    """Render Pebble's RFC 3339 timestamp with the CLI's fixed millisecond width.

    Go trims trailing zeros when marshalling (``...54.39Z``); the CLI prints three
    decimal places (``...54.390Z``). Match the CLI, since that's what users diff
    against.
    """
    try:
        parsed = datetime.datetime.fromisoformat(raw)
    except ValueError:
        return raw
    stamp = parsed.strftime('%Y-%m-%dT%H:%M:%S') + f'.{parsed.microsecond // 1000:03d}'
    offset = parsed.utcoffset()
    if offset is None:
        return stamp
    if not offset:
        return stamp + 'Z'
    return stamp + parsed.strftime('%z')[:3] + ':' + parsed.strftime('%z')[3:]


def _format_entry(entry: dict[str, Any]) -> str:
    return f'{_format_time(entry.get("time", ""))} [{entry.get("service", "")}] {entry.get("message", "")}'


def _error_from(response: http.client.HTTPResponse) -> LogsError:
    body = response.read().decode('utf-8', 'replace')
    try:
        message = json.loads(body)['result']['message']
    except (ValueError, KeyError, TypeError):
        message = body.strip() or f'HTTP {response.status}'
    return LogsError(f'cannot fetch logs: {message}')


def iter_logs(
    socket_path: str,
    *,
    services: Iterable[str] = (),
    n: int = DEFAULT_LOG_LINES,
    follow: bool = False,
    timeout: float | None = 30.0,
) -> Generator[str, None, None]:
    """Yield formatted log lines from the Pebble at *socket_path*.

    Lines carry no trailing newline. With *follow* the generator blocks until the
    connection is closed — close the generator (or break out of the loop) to hang
    up. Raises :class:`LogsError` if the socket or the endpoint is unhappy.
    """
    query: list[tuple[str, str]] = [('n', str(n))]
    if follow:
        query.append(('follow', 'true'))
    query += [('services', service) for service in services]
    path = '/v1/logs?' + urllib.parse.urlencode(query)

    # Following has no natural deadline, so drop the socket timeout entirely
    # rather than tripping over a quiet service.
    conn = _UnixHTTPConnection(socket_path, timeout=None if follow else timeout)
    try:
        try:
            conn.request('GET', path)
            response = conn.getresponse()
        except LogsError:
            raise
        except OSError as exc:
            raise LogsError(f'cannot fetch logs: {exc}') from exc
        if response.status != 200:
            raise _error_from(response)
        for raw in response:
            line = raw.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                # Not something we know how to render; pass it through rather
                # than losing it.
                yield line.decode('utf-8', 'replace')
                continue
            yield _format_entry(entry)
    finally:
        conn.close()
