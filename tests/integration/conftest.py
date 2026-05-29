"""Integration fixtures: a real, throwaway Pebble daemon."""

from __future__ import annotations

import shutil
import subprocess
import time

import pytest

LAYER = """\
summary: cascade integration layer
services:
  hello:
    override: replace
    summary: greet in a loop
    command: /bin/sh -c 'while true; do echo hi; sleep 1; done'
    startup: disabled
checks:
  up:
    override: replace
    level: alive
    threshold: 3
    exec:
      command: /bin/true
"""


@pytest.fixture(scope="session")
def pebble_socket(tmp_path_factory):
    pebble = shutil.which("pebble")
    if pebble is None:
        pytest.skip("pebble binary not on PATH")

    pebble_dir = tmp_path_factory.mktemp("pebble")
    (pebble_dir / "layers").mkdir()
    (pebble_dir / "layers" / "001-test.yaml").write_text(LAYER)
    socket = pebble_dir / ".pebble.socket"

    proc = subprocess.Popen(
        [pebble, "run", "--hold"],
        env={"PEBBLE": str(pebble_dir), "PATH": "/usr/bin:/bin"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            if socket.exists():
                break
            time.sleep(0.1)
        else:
            pytest.fail("pebble socket did not appear")
        yield str(socket)
    finally:
        proc.terminate()
        proc.wait(timeout=10)
