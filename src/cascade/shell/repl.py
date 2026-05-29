"""The REPL: one process, one session, one command (or single pipe) at a time."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from ..errors import CascadeError
from . import theme
from .commands.base import ExitShell, Result, build_registry
from .parser import ParseError, expand, parse_pipeline

if TYPE_CHECKING:
    from .context import ShellContext


class Shell:
    """Drives a Pebble through the command registry."""

    def __init__(self, ctx: ShellContext):
        self.ctx = ctx
        self.registry = build_registry()
        self._session = None

    # -- execution ---------------------------------------------------------
    def run_line(self, line: str) -> Result:
        """Parse and run a single input line (may raise :class:`ExitShell`)."""
        try:
            stages = parse_pipeline(line)
        except ParseError as exc:
            return Result.fail(f"cascade: {exc}")
        if not stages:
            return Result()
        return self._execute(stages)

    def _execute(self, stages: list[list[str]]) -> Result:
        if len(stages) == 1:
            return self._run_stage(stages[0], None)

        for stage in stages:
            cmd = self.registry.get(stage[0])
            if cmd is not None and cmd.streaming:
                return Result.fail(f"cascade: '{stage[0]}' cannot be used in a pipe.")

        left = self._run_stage(stages[0], None)
        right = self._run_stage(stages[1], left.output)
        return Result(
            output=right.output, error=left.error + right.error, code=right.code
        )

    def _run_stage(self, tokens: list[str], stdin: str | None) -> Result:
        tokens = [expand(tok, self.ctx.env) for tok in tokens]
        name, *args = tokens
        cmd = self.registry.get(name)
        if cmd is None:
            return Result.fail(
                f"cascade: command not found: {name}\n"
                f"  hint: 'exec {name} ...' runs it inside the container.",
                code=127,
            )
        try:
            return cmd.run(self.ctx, args, stdin)
        except ExitShell:
            raise
        except CascadeError as exc:
            return Result.fail(f"{name}: {exc}")
        except Exception as exc:  # noqa: BLE001 - surface backend errors as output
            return Result.fail(f"{name}: {exc}")

    def execute_and_emit(self, line: str) -> int:
        """Run one line, print its output, and return the exit code (one-shot)."""
        try:
            result = self.run_line(line)
        except ExitShell as exc:
            return exc.code
        self._emit(result)
        return result.code

    def _emit(self, result: Result) -> None:
        if result.output:
            sys.stdout.write(result.output)
            if not result.output.endswith("\n"):
                sys.stdout.write("\n")
            sys.stdout.flush()
        if result.error:
            sys.stderr.write(result.error)
            if not result.error.endswith("\n"):
                sys.stderr.write("\n")
            sys.stderr.flush()
        self.ctx.last_exit = result.code

    # -- interactive loop --------------------------------------------------
    def loop(self) -> int:
        session = self._ensure_session()
        self._print_banner()
        style = theme.style()
        while True:
            try:
                line = session.prompt(theme.prompt_fragments(self.ctx), style=style)
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            if not line.strip():
                continue
            try:
                result = self.run_line(line)
            except ExitShell as exc:
                self.ctx.last_exit = exc.code
                break
            self._emit(result)
        return self.ctx.last_exit

    def _ensure_session(self):
        if self._session is None:
            from prompt_toolkit import PromptSession

            from .completion import CascadeCompleter
            from .history import history_for

            self._session = PromptSession(
                history=history_for(self.ctx.target),
                completer=CascadeCompleter(self.registry.keys(), self.ctx),
                complete_while_typing=False,
            )
        return self._session

    def _print_banner(self) -> None:
        target = self.ctx.target
        where = target.unit + (f" ({target.container})" if target.container else "")
        print(
            f"cascade — connected to {where}. Type 'help' for commands, 'exit' to quit."
        )
