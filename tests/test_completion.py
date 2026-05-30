"""Tab completion smoke tests — command names and container paths."""

from __future__ import annotations

from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document

from borescope.shell.completion import BorescopeCompleter


def _completions(completer: BorescopeCompleter, text: str) -> list[tuple[str, int]]:
    doc = Document(text=text, cursor_position=len(text))
    return [
        (c.text, c.start_position)
        for c in completer.get_completions(doc, CompleteEvent())
    ]


def test_complete_command_names_empty(ctx):
    completer = BorescopeCompleter(["ls", "cat", "services"], ctx)
    completions = _completions(completer, "")
    assert {c[0] for c in completions} == {"ls", "cat", "services"}


def test_complete_command_names_prefix(ctx):
    completer = BorescopeCompleter(["ls", "cat", "services", "start"], ctx)
    assert sorted(c[0] for c in _completions(completer, "s")) == ["services", "start"]


def test_complete_path_top_level(transport, ctx):
    transport.add_file("/etc/hostname")
    transport.add_dir("/var")
    completer = BorescopeCompleter(["ls"], ctx)
    names = {c[0] for c in _completions(completer, "ls /")}
    # entries are returned with a trailing "/" for directories
    assert "etc/" in names
    assert "var/" in names


def test_complete_path_with_prefix(transport, ctx):
    transport.add_file("/etc/hostname")
    transport.add_file("/etc/hosts")
    transport.add_file("/etc/passwd")
    completer = BorescopeCompleter(["cat"], ctx)
    # "ho" should match "hostname" and "hosts" (both files; no trailing /)
    names = {c[0] for c in _completions(completer, "cat /etc/ho")}
    assert names == {"hostname", "hosts"}


def test_complete_path_no_raise_on_bad_dir(ctx):
    completer = BorescopeCompleter(["ls"], ctx)
    # /does-not-exist isn't in FakeTransport — completer must silently yield nothing
    assert _completions(completer, "ls /does-not-exist/foo") == []
