# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""The native ``/v1/logs`` client — no ``pebble`` binary involved.

Driven against a tiny unix-socket HTTP server standing in for Pebble, so the
connection and streaming paths are exercised for real rather than mocked out.
"""

from __future__ import annotations

import json
import socket
import threading

import pytest

from borescope.transport import logs


class FakeLogServer:
    """Serves one canned response and records the request line it was given."""

    def __init__(self, path: str, body: bytes, *, status: str = '200 OK', hangup: bool = False):
        self.path = path
        self.request_path = ''
        self._body = body
        self._status = status
        self._hangup = hangup
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(path)
        self._sock.listen(1)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        try:
            conn, _ = self._sock.accept()
        except OSError:
            return
        with conn:
            if self._hangup:
                return
            request = b''
            while b'\r\n\r\n' not in request:
                chunk = conn.recv(4096)
                if not chunk:
                    return
                request += chunk
            self.request_path = request.split(b' ')[1].decode()
            conn.sendall(
                f'HTTP/1.1 {self._status}\r\nContent-Length: {len(self._body)}\r\n\r\n'.encode()
                + self._body
            )

    def close(self) -> None:
        self._sock.close()
        self._thread.join(timeout=2)


@pytest.fixture
def serve(tmp_path):
    servers: list[FakeLogServer] = []

    def start(body: bytes, *, status: str = '200 OK', hangup: bool = False) -> FakeLogServer:
        server = FakeLogServer(
            str(tmp_path / f'p{len(servers)}.socket'), body, status=status, hangup=hangup
        )
        servers.append(server)
        return server

    yield start
    for server in servers:
        server.close()


def _entry(time: str, service: str, message: str) -> bytes:
    return json.dumps({'time': time, 'service': service, 'message': message}).encode() + b'\n'


# -- rendering ---------------------------------------------------------------
def test_renders_entries_like_the_pebble_cli(serve):
    server = serve(
        _entry('2026-07-22T08:37:54.39Z', 'ticker', 'tick 49')
        + _entry('2026-07-22T08:37:55.4Z', 'ticker', 'tick 50')
    )
    assert list(logs.iter_logs(server.path)) == [
        # Go trims trailing zeros on the wire; the CLI pads back to milliseconds.
        '2026-07-22T08:37:54.390Z [ticker] tick 49',
        '2026-07-22T08:37:55.400Z [ticker] tick 50',
    ]


def test_blank_lines_are_skipped(serve):
    server = serve(b'\n' + _entry('2026-07-22T08:37:54.390Z', 'web', 'hi') + b'\n')
    assert list(logs.iter_logs(server.path)) == ['2026-07-22T08:37:54.390Z [web] hi']


def test_unparseable_line_is_passed_through(serve):
    server = serve(b'not json at all\n')
    assert list(logs.iter_logs(server.path)) == ['not json at all']


def test_empty_log_buffer(serve):
    assert list(logs.iter_logs(serve(b'').path)) == []


def test_format_time_keeps_non_utc_offset():
    assert logs._format_time('2026-07-22T08:37:54.39+05:30') == '2026-07-22T08:37:54.390+05:30'


def test_format_time_passes_through_junk():
    assert logs._format_time('whenever') == 'whenever'


def test_format_time_naive_timestamp_gets_no_suffix():
    assert logs._format_time('2026-07-22T08:37:54.39') == '2026-07-22T08:37:54.390'


# -- query building ----------------------------------------------------------
def test_query_defaults_to_thirty_lines(serve):
    server = serve(b'')
    list(logs.iter_logs(server.path))
    assert server.request_path == '/v1/logs?n=30'


def test_query_carries_services_and_follow(serve):
    server = serve(b'')
    list(logs.iter_logs(server.path, services=['web', 'worker'], n=5, follow=True))
    assert server.request_path == '/v1/logs?n=5&follow=true&services=web&services=worker'


# -- errors ------------------------------------------------------------------
def test_missing_socket_is_a_clear_error(tmp_path):
    with pytest.raises(logs.LogsError, match='could not connect to Pebble'):
        list(logs.iter_logs(str(tmp_path / 'nope.socket')))


def test_server_hangup_mid_request_is_a_clear_error(serve):
    # Pebble accepted the connection and then went away without answering.
    server = serve(b'', hangup=True)
    with pytest.raises(logs.LogsError, match='cannot fetch logs'):
        list(logs.iter_logs(server.path))


def test_api_error_message_is_surfaced(serve):
    body = json.dumps({'result': {'message': 'no such service'}}).encode()
    server = serve(body, status='400 Bad Request')
    with pytest.raises(logs.LogsError, match='cannot fetch logs: no such service'):
        list(logs.iter_logs(server.path))


def test_non_json_error_body_falls_back_to_the_text(serve):
    server = serve(b'nope', status='500 Internal Server Error')
    with pytest.raises(logs.LogsError, match='cannot fetch logs: nope'):
        list(logs.iter_logs(server.path))


# -- -n parsing (matches the Pebble CLI's wording) ---------------------------
def test_parse_n_all():
    assert logs.parse_n('all') == -1


def test_parse_n_integer():
    assert logs.parse_n('5') == 5


@pytest.mark.parametrize('value', ['bogus', '-3', '', '1.5'])
def test_parse_n_rejects_junk(value):
    with pytest.raises(logs.LogsError, match='non-negative integer'):
        logs.parse_n(value)
