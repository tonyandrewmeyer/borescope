"""The auto-discovery command registry."""

from __future__ import annotations

from borescope.shell.commands.base import build_registry

EXPECTED = {
    # shell-state / trivial
    "cd",
    "pwd",
    "echo",
    "env",
    "exit",
    "clear",
    "help",
    # filesystem
    "ls",
    "cat",
    "head",
    "tail",
    "find",
    "stat",
    "grep",
    "cp",
    "mv",
    "rm",
    "mkdir",
    "touch",
    # escape hatch
    "exec",
    # pebble-native
    "services",
    "start",
    "stop",
    "restart",
    "replan",
    "plan",
    "logs",
    "notices",
    "notice",
    "notify",
    "checks",
    "health",
    "tasks",
    "changes",
    "push",
    "pull",
}


def test_expected_commands_present():
    registry = build_registry()
    missing = EXPECTED - set(registry)
    assert not missing, f"missing commands: {missing}"


def test_alias_resolves_to_same_instance():
    registry = build_registry()
    assert registry["quit"] is registry["exit"]


def test_every_command_has_a_summary():
    registry = build_registry()
    for name, command in registry.items():
        assert command.summary, f"{name} has no summary"
