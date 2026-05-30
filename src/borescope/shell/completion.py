"""Tab completion: built-in command names, and container-side filesystem paths."""

from __future__ import annotations

import shlex
from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING

from prompt_toolkit.completion import Completer, Completion

from . import pathutils

if TYPE_CHECKING:
    from prompt_toolkit.completion import CompleteEvent
    from prompt_toolkit.document import Document

    from .context import ShellContext


class BorescopeCompleter(Completer):
    """Complete the first token as a command name, later tokens as paths.

    Path completion lists files inside the container via the transport. It only
    fires on an explicit Tab (the session is created with
    ``complete_while_typing=False``), so the ``juju ssh`` round-trip per request is
    acceptable.
    """

    def __init__(self, command_names: Iterable[str], ctx: ShellContext):
        self.command_names = sorted(set(command_names))
        self.ctx = ctx

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterator[Completion]:
        text = document.text_before_cursor
        try:
            tokens = shlex.split(text)
        except ValueError:
            tokens = text.split()

        ends_with_space = text[-1:].isspace()
        if ends_with_space:
            word = ""
            tokens_before = len(tokens)
        else:
            word = tokens[-1] if tokens else ""
            tokens_before = len(tokens) - 1

        if tokens_before <= 0:
            for name in self.command_names:
                if name.startswith(word):
                    yield Completion(name, start_position=-len(word))
            return

        yield from self._complete_path(word)

    def _complete_path(self, word: str) -> Iterator[Completion]:
        ctx = self.ctx
        if "/" in word:
            dir_part, _, prefix = word.rpartition("/")
            base = pathutils.resolve(ctx.cwd, dir_part or "/", home=ctx.home)
        else:
            prefix = word
            base = ctx.cwd
        try:
            entries = ctx.transport.list_files(base)
        except Exception:  # noqa: BLE001 - completion must never raise
            return
        for info in entries:
            name = info.name
            if not name.startswith(prefix):
                continue
            is_dir = getattr(getattr(info, "type", None), "name", "") == "DIRECTORY"
            yield Completion(
                name + ("/" if is_dir else ""), start_position=-len(prefix)
            )
