"""Discovery: unit-ref parsing, container discovery, target resolution (juju mocked)."""

from __future__ import annotations

import pytest

from borescope import discovery
from borescope.errors import DiscoveryError

CAAS_STATUS = {
    "model": {"name": "testmodel", "type": "caas"},
    "applications": {"app": {"units": {"app/0": {}, "app/1": {}}}},
}

METADATA_YAML = """
name: app
containers:
  workload:
    resource: app-image
  sidecar:
    resource: sidecar-image
"""


def _patch_juju(monkeypatch, *, status=CAAS_STATUS, metadata=METADATA_YAML):
    monkeypatch.setattr(
        discovery.juju,
        "current_controller_model",
        lambda *a, **k: ("ctrl", "testmodel"),
    )
    monkeypatch.setattr(discovery.juju, "status_json", lambda *a, **k: status)
    monkeypatch.setattr(discovery.juju, "run_juju", lambda *a, **k: metadata)


def test_parse_unit_ref_valid():
    assert discovery.parse_unit_ref("myapp/0") == ("myapp", "0")


@pytest.mark.parametrize("bad", ["myapp", "myapp/", "/0", "MyApp/0", "app/x"])
def test_parse_unit_ref_invalid(bad):
    with pytest.raises(DiscoveryError):
        discovery.parse_unit_ref(bad)


def test_discover_containers_parses_metadata(monkeypatch):
    _patch_juju(monkeypatch)
    containers = discovery.discover_containers(
        "app/0", "app", "0", model=None, juju_binary="juju"
    )
    assert containers == ["workload", "sidecar"]


def test_resolve_target_defaults_to_first_container(monkeypatch):
    _patch_juju(monkeypatch)
    target = discovery.resolve_target("app/0")
    assert target.container == "workload"
    assert target.app == "app"
    assert target.model == "testmodel"
    assert target.controller == "ctrl"


def test_resolve_target_honours_explicit_container(monkeypatch):
    _patch_juju(monkeypatch)
    target = discovery.resolve_target("app/0", container="sidecar")
    assert target.container == "sidecar"


def test_resolve_target_rejects_machine_model(monkeypatch):
    status = {
        "model": {"type": "iaas"},
        "applications": {"app": {"units": {"app/0": {}}}},
    }
    _patch_juju(monkeypatch, status=status)
    with pytest.raises(DiscoveryError, match="Kubernetes"):
        discovery.resolve_target("app/0")


def test_resolve_target_unknown_unit(monkeypatch):
    _patch_juju(monkeypatch)
    with pytest.raises(DiscoveryError, match="not found"):
        discovery.resolve_target("app/9")


def test_resolve_target_unknown_app(monkeypatch):
    _patch_juju(monkeypatch)
    with pytest.raises(DiscoveryError, match="not found"):
        discovery.resolve_target("other/0")


class _OldPebble:
    def get_system_info(self):
        from ops import pebble

        return pebble.SystemInfo("v1.26.0")

    def get_services(self, names=None):
        raise Exception("error: unknown flag `format'")


class _NewPebble:
    def get_system_info(self):
        from ops import pebble

        return pebble.SystemInfo("v1.31.0")

    def get_services(self, names=None):
        return []


def _target():
    return discovery.Target(unit="a/0", app="a", container="c", model="m")


def test_sanity_check_rejects_old_pebble_without_format_json():
    with pytest.raises(DiscoveryError, match="too old"):
        discovery.sanity_check(_OldPebble(), _target())


def test_sanity_check_passes_on_new_pebble():
    discovery.sanity_check(_NewPebble(), _target())  # must not raise


def test_history_key():
    target = discovery.Target(
        unit="app/0", app="app", container="c", model="m", controller="ctrl"
    )
    assert target.history_key == "ctrl_m_app_0"


def _make_socket(base, name):
    """Create a fake ``<base>/<name>/pebble.socket`` (a plain file satisfies the
    existence check) and return its path."""
    sock_dir = base / name
    sock_dir.mkdir()
    sock = sock_dir / "pebble.socket"
    sock.touch()
    return str(sock)


def test_discover_local_sockets_finds_mounted(tmp_path):
    _make_socket(tmp_path, "workload")
    _make_socket(tmp_path, "redis")
    assert discovery.discover_local_sockets(str(tmp_path)) == {
        "redis": str(tmp_path / "redis" / "pebble.socket"),
        "workload": str(tmp_path / "workload" / "pebble.socket"),
    }


def test_discover_local_sockets_missing_dir(tmp_path):
    assert discovery.discover_local_sockets(str(tmp_path / "nope")) == {}


def test_resolve_local_target_single(tmp_path):
    _make_socket(tmp_path, "workload")
    target = discovery.resolve_local_target(base=str(tmp_path))
    assert target.container == "workload"
    assert target.socket_path == str(tmp_path / "workload" / "pebble.socket")
    assert target.model is None


def test_resolve_local_target_named(tmp_path):
    _make_socket(tmp_path, "workload")
    _make_socket(tmp_path, "redis")
    target = discovery.resolve_local_target(container="redis", base=str(tmp_path))
    assert target.container == "redis"


def test_resolve_local_target_ambiguous(tmp_path):
    _make_socket(tmp_path, "workload")
    _make_socket(tmp_path, "redis")
    with pytest.raises(DiscoveryError, match="multiple workload containers"):
        discovery.resolve_local_target(base=str(tmp_path))


def test_resolve_local_target_unknown_container(tmp_path):
    _make_socket(tmp_path, "workload")
    with pytest.raises(DiscoveryError, match="no Pebble socket for container"):
        discovery.resolve_local_target(container="nope", base=str(tmp_path))


def test_resolve_local_target_none_present(tmp_path):
    with pytest.raises(DiscoveryError, match="no Pebble sockets found"):
        discovery.resolve_local_target(base=str(tmp_path))
