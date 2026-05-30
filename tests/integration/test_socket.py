"""End-to-end against a real Pebble over the socket transport."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from borescope.discovery import Target
from borescope.shell import ShellContext
from borescope.shell.repl import Shell
from borescope.transport import open_transport

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


# --------------------------------------------------------------------------- #
# Entrypoint smoke: exercise the actual `borescope` CLI subprocess.
# These catch breakage in argparse, exit codes, JSON serialization, and the
# Shell -> stdout glue that the Shell-class tests above don't see.
# --------------------------------------------------------------------------- #


def _run_borescope(*args: str, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "borescope", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def test_entrypoint_version():
    result = _run_borescope("--version")
    assert result.returncode == 0
    assert "borescope" in result.stdout.lower()


def test_entrypoint_no_unit_or_socket_errors_clearly():
    result = _run_borescope()
    assert result.returncode == 2
    assert "unit reference is required" in result.stderr


def test_entrypoint_snapshot_against_real_pebble(pebble_socket):
    result = _run_borescope("--socket", pebble_socket, "--snapshot")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["unit"] == "local"
    assert data["system"]["version"]
    assert any(s["name"] == "hello" for s in data["services"])


def test_entrypoint_oneshot_command_against_real_pebble(pebble_socket):
    result = _run_borescope("--socket", pebble_socket, "-c", "services")
    assert result.returncode == 0, result.stderr
    assert "hello" in result.stdout
