"""Pebble-binary discovery for the local-socket relay."""

from __future__ import annotations

from cascade.transport import relay


def test_local_pebble_binary_prefers_path(monkeypatch, tmp_path):
    fake = tmp_path / "pebble"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert relay._local_pebble_binary() == str(fake)


def test_local_pebble_binary_falls_back_to_charm_bin(monkeypatch, tmp_path):
    # Empty PATH so `which` finds nothing.
    monkeypatch.setenv("PATH", str(tmp_path / "nope"))
    juju_pebble = tmp_path / "juju_pebble"
    juju_pebble.write_text("")
    monkeypatch.setattr(relay, "_JUJU_PEBBLE", str(juju_pebble))
    assert relay._local_pebble_binary() == str(juju_pebble)


def test_local_pebble_binary_falls_back_to_bare_name(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path / "nope"))
    monkeypatch.setattr(relay, "_JUJU_PEBBLE", str(tmp_path / "also-nope"))
    assert relay._local_pebble_binary() == "pebble"
