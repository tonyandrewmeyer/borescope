"""End-to-end against a real Pebble over the socket transport."""

from __future__ import annotations

import pytest

from cascade.discovery import Target
from cascade.shell import ShellContext
from cascade.shell.repl import Shell
from cascade.transport import open_transport

pytestmark = pytest.mark.integration


@pytest.fixture
def shell(pebble_socket):
    transport = open_transport(unit="local", container=None, socket_path=pebble_socket)
    target = Target(
        unit="local",
        app="local",
        container=None,
        model=None,
        socket_path=pebble_socket,
    )
    return Shell(ShellContext(transport=transport, target=target))


def test_services_lists_hello(shell):
    result = shell.run_line("services")
    assert "hello" in result.output
    assert result.code == 0


def test_start_then_status_active(shell):
    shell.run_line("start hello")
    result = shell.run_line("services")
    assert "active" in result.output


def test_plan_is_yaml(shell):
    result = shell.run_line("plan")
    assert "services:" in result.output
    assert "hello:" in result.output


def test_checks(shell):
    result = shell.run_line("checks")
    assert "up" in result.output


def test_filesystem_over_socket(shell):
    result = shell.run_line("ls /")
    assert "etc" in result.output.split("\n")


def test_pipe_over_socket(shell):
    result = shell.run_line("cat /etc/passwd | grep root")
    assert "root" in result.output
