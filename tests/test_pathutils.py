"""Container-side path resolution."""

from __future__ import annotations

from cascade.shell import pathutils


def test_absolute_passthrough():
    assert pathutils.resolve("/cwd", "/etc/hosts") == "/etc/hosts"


def test_relative_joins_cwd():
    assert pathutils.resolve("/var", "log/app") == "/var/log/app"


def test_dotdot_normalised():
    assert pathutils.resolve("/var/log", "../lib") == "/var/lib"


def test_dot_is_cwd():
    assert pathutils.resolve("/var/log", ".") == "/var/log"


def test_tilde_expands_home():
    assert pathutils.resolve("/cwd", "~", home="/root") == "/root"
    assert pathutils.resolve("/cwd", "~/x", home="/home/u") == "/home/u/x"


def test_empty_path_is_cwd():
    assert pathutils.resolve("/here", "") == "/here"
