"""Pebble-native subcommands, first-class (not hidden behind a ``pebble`` prefix).

These are the operational value-add over a plain shell: ``services``, ``logs``,
``plan``, ``checks``, ``notices`` and friends, as thin wrappers over the transport
(an ``ops.pebble.Client``-shaped object).
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from ops import pebble

from ._args import parse_args
from .base import Command, Result

if TYPE_CHECKING:
    from ..context import ShellContext


def _table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    def fmt(row: list[str]) -> str:
        return "  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row))

    return "\n".join([fmt(headers), *(fmt(r) for r in rows)])


def _enum_value(value: object) -> str:
    return getattr(value, "value", str(value))


# --------------------------------------------------------------------------- #
# Services
# --------------------------------------------------------------------------- #
class Services(Command):
    name = "services"
    summary = "List services and their status"
    usage = "services [name...]"

    def run(
        self, ctx: ShellContext, args: list[str], stdin: str | None = None
    ) -> Result:
        _, _, names = parse_args(args)
        infos = ctx.transport.get_services(names or None)
        if not infos:
            return Result.ok("(no services)")
        rows = [[i.name, _enum_value(i.startup), _enum_value(i.current)] for i in infos]
        return Result.ok(_table(["Service", "Startup", "Current"], rows))


class _ServiceAction(Command):
    verb = ""
    # English past tense — declared per subclass so we don't have to encode
    # consonant-doubling rules ("stop" -> "Stopped", not "Stoped").
    past = ""

    def run(
        self, ctx: ShellContext, args: list[str], stdin: str | None = None
    ) -> Result:
        _, _, names = parse_args(args)
        if not names:
            return Result.fail(f"{self.name}: usage: {self.name} <service...>")
        method = getattr(ctx.transport, f"{self.verb}_services")
        method(names)
        return Result.ok(f"{self.past}: {', '.join(names)}")


class Start(_ServiceAction):
    name = "start"
    verb = "start"
    past = "Started"
    summary = "Start services"
    usage = "start <service...>"


class Stop(_ServiceAction):
    name = "stop"
    verb = "stop"
    past = "Stopped"
    summary = "Stop services"
    usage = "stop <service...>"


class Restart(_ServiceAction):
    name = "restart"
    verb = "restart"
    past = "Restarted"
    summary = "Restart services"
    usage = "restart <service...>"


class Replan(Command):
    name = "replan"
    summary = "Apply the plan: stop/start services as the plan requires"

    def run(
        self, ctx: ShellContext, args: list[str], stdin: str | None = None
    ) -> Result:
        ctx.transport.replan_services()
        return Result.ok("Replanned.")


# --------------------------------------------------------------------------- #
# Plan
# --------------------------------------------------------------------------- #
class Plan(Command):
    name = "plan"
    summary = "Show the merged Pebble plan (YAML)"

    def run(
        self, ctx: ShellContext, args: list[str], stdin: str | None = None
    ) -> Result:
        plan = ctx.transport.get_plan()
        return Result.ok(plan.to_yaml().rstrip("\n"))


# --------------------------------------------------------------------------- #
# Logs (CLI-shaped: driven over the relay, not the ops API)
# --------------------------------------------------------------------------- #
class Logs(Command):
    name = "logs"
    summary = "Show service logs (-f / --follow to stream)"
    usage = "logs [-f|--follow] [-n N] [service...]"

    def run(
        self, ctx: ShellContext, args: list[str], stdin: str | None = None
    ) -> Result:
        flags, values, services = parse_args(args, valued=("n",))
        follow = "f" in flags or "follow" in flags
        pebble_args = ["logs"]
        if follow:
            pebble_args.append("--follow")
        if "n" in values:
            pebble_args += ["-n", values["n"]]
        pebble_args += services

        argv, env, runner = self._relay(ctx)
        argv = [*argv, *pebble_args]
        if not follow:
            result = runner.run(argv, env=env, timeout=30.0, check=False)
            return Result(
                output=result.stdout or "",
                error=result.stderr or "",
                code=result.returncode,
            )
        return self._follow(runner, argv, env)

    @staticmethod
    def _relay(ctx: ShellContext):
        from ...transport.relay import pebble_relay

        return pebble_relay(ctx.target)

    @staticmethod
    def _follow(runner, argv: list[str], env: dict[str, str]) -> Result:
        process = runner.popen(
            argv, stdin=None, stdout=sys.stdout, stderr=sys.stdout, text=True, env=env
        )
        try:
            process.wait()
        except KeyboardInterrupt:
            process.terminate()
            sys.stdout.write("\n")
        return Result()


# --------------------------------------------------------------------------- #
# Checks / health
# --------------------------------------------------------------------------- #
class Checks(Command):
    name = "checks"
    summary = "List health checks and their status"
    usage = "checks [name...]"

    def run(
        self, ctx: ShellContext, args: list[str], stdin: str | None = None
    ) -> Result:
        _, _, names = parse_args(args)
        infos = ctx.transport.get_checks(names=names or None)
        if not infos:
            return Result.ok("(no checks)")
        rows = [
            [
                i.name,
                _enum_value(i.level),
                _enum_value(i.status),
                f"{i.failures}/{i.threshold}",
            ]
            for i in infos
        ]
        return Result.ok(_table(["Check", "Level", "Status", "Failures"], rows))


class Health(Command):
    name = "health"
    summary = "Report overall health (all checks up?)"

    def run(
        self, ctx: ShellContext, args: list[str], stdin: str | None = None
    ) -> Result:
        infos = ctx.transport.get_checks()
        failing = [i.name for i in infos if _enum_value(i.status).lower() != "up"]
        if not infos:
            return Result.ok("healthy (no checks configured)")
        if failing:
            return Result(output=f"unhealthy: {', '.join(failing)} not up", code=1)
        return Result.ok("healthy")


# --------------------------------------------------------------------------- #
# Notices
# --------------------------------------------------------------------------- #
class Notices(Command):
    name = "notices"
    summary = "List recent notices"

    def run(
        self, ctx: ShellContext, args: list[str], stdin: str | None = None
    ) -> Result:
        notices = ctx.transport.get_notices()
        if not notices:
            return Result.ok("(no notices)")
        rows = [
            [
                n.id,
                _enum_value(n.type),
                n.key,
                str(n.occurrences),
                n.last_repeated.isoformat() if n.last_repeated else "",
            ]
            for n in notices
        ]
        return Result.ok(_table(["ID", "Type", "Key", "Count", "Last"], rows))


class Notice(Command):
    name = "notice"
    summary = "Show a single notice by ID"
    usage = "notice <id>"

    def run(
        self, ctx: ShellContext, args: list[str], stdin: str | None = None
    ) -> Result:
        if not args:
            return Result.fail("notice: usage: notice <id>")
        notice = ctx.transport.get_notice(args[0])
        lines = [
            f"ID:          {notice.id}",
            f"Type:        {_enum_value(notice.type)}",
            f"Key:         {notice.key}",
            f"Occurrences: {notice.occurrences}",
            f"First:       {notice.first_occurred.isoformat() if notice.first_occurred else ''}",
            f"Last:        {notice.last_occurred.isoformat() if notice.last_occurred else ''}",
        ]
        if notice.last_data:
            lines.append(f"Data:        {notice.last_data}")
        return Result.ok("\n".join(lines))


class Notify(Command):
    name = "notify"
    summary = "Record a custom notice"
    usage = "notify <key> [data-key=value...]"

    def run(
        self, ctx: ShellContext, args: list[str], stdin: str | None = None
    ) -> Result:
        if not args:
            return Result.fail("notify: usage: notify <key> [data-key=value...]")
        key, *rest = args
        data: dict[str, str] = {}
        for item in rest:
            name, _, value = item.partition("=")
            data[name] = value
        notice_id = ctx.transport.notify(
            pebble.NoticeType.CUSTOM, key, data=data or None
        )
        return Result.ok(f"Recorded notice {notice_id}")


# --------------------------------------------------------------------------- #
# Changes / tasks
# --------------------------------------------------------------------------- #
def _all_changes(transport) -> list:
    state = getattr(pebble.ChangeState, "ALL", None)
    return transport.get_changes(select=state) if state else transport.get_changes()


class Changes(Command):
    name = "changes"
    summary = "List recent changes"

    def run(
        self, ctx: ShellContext, args: list[str], stdin: str | None = None
    ) -> Result:
        changes = _all_changes(ctx.transport)
        if not changes:
            return Result.ok("(no changes)")
        rows = [
            [
                c.id,
                _enum_value(c.status),
                "ready" if c.ready else "doing",
                c.summary,
            ]
            for c in changes
        ]
        return Result.ok(_table(["ID", "Status", "State", "Summary"], rows))


class Tasks(Command):
    name = "tasks"
    summary = "Show tasks for a change (defaults to the most recent)"
    usage = "tasks [change-id]"

    def run(
        self, ctx: ShellContext, args: list[str], stdin: str | None = None
    ) -> Result:
        if args:
            change = ctx.transport.get_change(pebble.ChangeID(args[0]))
        else:
            changes = _all_changes(ctx.transport)
            if not changes:
                return Result.ok("(no changes)")
            change = changes[-1]
        rows = [
            [_enum_value(t.status), t.summary] for t in getattr(change, "tasks", [])
        ]
        if not rows:
            return Result.ok(f"Change {change.id}: (no tasks)")
        header = f"Change {change.id}: {change.summary}"
        return Result.ok(header + "\n" + _table(["Status", "Summary"], rows))


# --------------------------------------------------------------------------- #
# push / pull (explicit transfer, complementing cp/cat)
# --------------------------------------------------------------------------- #
class Pull(Command):
    name = "pull"
    summary = "Copy a file from the container to the local host"
    usage = "pull <remote> <local>"

    def run(
        self, ctx: ShellContext, args: list[str], stdin: str | None = None
    ) -> Result:
        _, _, paths = parse_args(args)
        if len(paths) != 2:
            return Result.fail("pull: usage: pull <remote> <local>")
        from .. import pathutils

        remote = pathutils.resolve(ctx.cwd, paths[0], home=ctx.home)
        try:
            with ctx.transport.pull(remote, encoding=None) as handle:
                data = handle.read()
            with open(paths[1], "wb") as out:
                out.write(data if isinstance(data, bytes) else data.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            return Result.fail(f"pull: {exc}")
        return Result.ok(f"Pulled {paths[0]} -> {paths[1]}")


class Push(Command):
    name = "push"
    summary = "Copy a local file into the container"
    usage = "push <local> <remote>"

    def run(
        self, ctx: ShellContext, args: list[str], stdin: str | None = None
    ) -> Result:
        _, _, paths = parse_args(args)
        if len(paths) != 2:
            return Result.fail("push: usage: push <local> <remote>")
        from .. import pathutils

        remote = pathutils.resolve(ctx.cwd, paths[1], home=ctx.home)
        try:
            with open(paths[0], "rb") as handle:
                data = handle.read()
            ctx.transport.push(remote, data, make_dirs=True)
        except Exception as exc:  # noqa: BLE001
            return Result.fail(f"push: {exc}")
        return Result.ok(f"Pushed {paths[0]} -> {paths[1]}")
