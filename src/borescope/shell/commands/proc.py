# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""``ps`` implemented over ``/proc`` via the Pebble files API.

A rock usually ships neither a shell nor ``ps``, so ``exec ps`` fails in
exactly the containers borescope exists for. Everything ``ps`` reports lives in
``/proc``, which the files API *can* read — so ``ps`` is a built-in, like the
filesystem commands.

The option surface and output columns follow POSIX.1-2017 XCU ``ps``
(https://pubs.opengroup.org/onlinepubs/9699919799/utilities/ps.html), with one
deliberate divergence: POSIX's default selection is "processes that have the
same effective user ID and the same controlling terminal as the invoker", but
borescope is not a process inside the container — there is no invoker euid or
terminal to match — so a bare ``ps`` selects every process, as if ``-e`` were
given (pinned by ``tests/spread/ps-default-selection-divergence``).

Combining format options is first-match: ``-o`` beats ``-l`` beats ``-f``
(POSIX leaves the combinations unspecified).

Every file read is a Pebble files-API call — over the ``juju ssh`` relay that
is a full round-trip each — so reads are lazy: each column and selector
declares what it needs (``_NEEDS`` tags), and ``_snapshot`` only fetches those
files. The default listing needs nothing beyond ``/proc/<pid>/stat``, so a
bare ``ps`` costs one call per process plus the ``/proc`` listing.
"""

from __future__ import annotations

import contextlib
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..sanitise import safe_name
from .base import Command, Result

if TYPE_CHECKING:
    from ...transport import Transport
    from ..context import ShellContext

# Tick counts in /proc are in USER_HZ units, which Linux fixes at 100 for
# userspace regardless of the kernel's internal HZ (see times(2)).
_CLK_TCK = 100
# -l's SZ column is in pages; 4 KiB everywhere borescope can reach.
_PAGE_SIZE = 4096

_FLAG_OPTS = frozenset('aAdefl')
_VALUED_OPTS = frozenset('gGnoptuU')


class _OptionError(Exception):
    """A bad option, operand, or format/selector value; str(exc) is the message."""


@dataclass
class _Process:
    """One process, parsed from ``/proc/<pid>/{stat,cmdline,status}``."""

    pid: int
    comm: str
    state: str
    ppid: int
    pgid: int
    sid: int
    tty_nr: int
    flags: int
    cpu_ticks: int  # utime + stime
    priority: int
    nice: int
    start_ticks: int  # time of start, in ticks since boot
    vsize: int  # bytes
    args: str = ''  # decoded cmdline; empty for kernel threads
    ruid: int = -1
    euid: int = -1
    rgid: int = -1
    egid: int = -1


@dataclass
class _System:
    """Container-wide context needed to render per-process fields."""

    uptime: float = 0.0  # seconds since boot
    btime: int | None = None  # boot time, epoch seconds (None if unreadable)
    now: float = 0.0  # wall clock, epoch seconds
    users: dict[int, str] = field(default_factory=dict)
    uids: dict[str, int] = field(default_factory=dict)
    groups: dict[int, str] = field(default_factory=dict)
    gids: dict[str, int] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# /proc parsing (pure, unit-testable)
# --------------------------------------------------------------------------- #
def _parse_stat(text: str) -> _Process | None:
    """Parse ``/proc/<pid>/stat``; None if the content is not stat-shaped.

    ``comm`` may contain spaces and parentheses, so it is bracketed by the
    first ``(`` and the *last* ``)`` rather than split on whitespace.
    """
    try:
        lparen = text.index('(')
        rparen = text.rindex(')')
        rest = text[rparen + 1 :].split()
        # rest[0] is field 3 of proc(5) stat; index = field number - 3.
        return _Process(
            pid=int(text[:lparen].strip()),
            comm=text[lparen + 1 : rparen],
            state=rest[0],
            ppid=int(rest[1]),
            pgid=int(rest[2]),
            sid=int(rest[3]),
            tty_nr=int(rest[4]),
            flags=int(rest[6]),
            cpu_ticks=int(rest[11]) + int(rest[12]),
            priority=int(rest[15]),
            nice=int(rest[16]),
            start_ticks=int(rest[19]),
            vsize=int(rest[20]),
        )
    except (ValueError, IndexError):
        return None


def _parse_cmdline(data: str) -> str:
    return data.rstrip('\x00').replace('\x00', ' ')


def _parse_status_ids(text: str) -> tuple[int, int, int, int]:
    """Return (ruid, euid, rgid, egid) from ``/proc/<pid>/status``; -1 if absent."""
    ruid = euid = rgid = egid = -1
    for line in text.splitlines():
        if line.startswith('Uid:'):
            parts = line.split()
            if len(parts) >= 3:
                ruid, euid = int(parts[1]), int(parts[2])
        elif line.startswith('Gid:'):
            parts = line.split()
            if len(parts) >= 3:
                rgid, egid = int(parts[1]), int(parts[2])
    return ruid, euid, rgid, egid


def _parse_id_table(text: str) -> dict[int, str]:
    """Map numeric id -> name from passwd/group-format lines."""
    table: dict[int, str] = {}
    for line in text.splitlines():
        parts = line.split(':')
        if len(parts) >= 3:
            try:
                table[int(parts[2])] = parts[0]
            except ValueError:
                continue
    return table


def _tty_name(tty_nr: int) -> str:
    """Decode stat's ``tty_nr`` device number to a ps-style terminal name."""
    if tty_nr <= 0:
        return '?'
    major = (tty_nr >> 8) & 0xFFF
    minor = (tty_nr & 0xFF) | ((tty_nr >> 12) & 0xFFF00)
    if 136 <= major <= 143:  # Unix98 pty slaves span majors 136-143
        return f'pts/{minor + (major - 136) * 256}'
    if major == 4:
        return f'tty{minor}' if minor < 64 else f'ttyS{minor - 64}'
    return '?'


# --------------------------------------------------------------------------- #
# Field formatting (pure, unit-testable)
# --------------------------------------------------------------------------- #
def _fmt_time(seconds: int) -> str:
    """POSIX ``time``: cumulative CPU time as ``[dd-]hh:mm:ss``."""
    days, rem = divmod(seconds, 86400)
    hh, rem = divmod(rem, 3600)
    mm, ss = divmod(rem, 60)
    base = f'{hh:02d}:{mm:02d}:{ss:02d}'
    return f'{days}-{base}' if days else base


def _fmt_etime(seconds: int) -> str:
    """POSIX ``etime``: elapsed time since start as ``[[dd-]hh:]mm:ss``."""
    days, rem = divmod(seconds, 86400)
    hh, rem = divmod(rem, 3600)
    mm, ss = divmod(rem, 60)
    if days:
        return f'{days}-{hh:02d}:{mm:02d}:{ss:02d}'
    if hh:
        return f'{hh:02d}:{mm:02d}:{ss:02d}'
    return f'{mm:02d}:{ss:02d}'


def _fmt_stime(start_epoch: float, now: float) -> str:
    """-f's STIME: ``HH:MM`` if started today, else ``MmmDD``."""
    started = time.localtime(start_epoch)
    today = time.localtime(now)
    if (started.tm_year, started.tm_yday) == (today.tm_year, today.tm_yday):
        return time.strftime('%H:%M', started)
    return time.strftime('%b%d', started)


def _etime_s(p: _Process, s: _System) -> int:
    return max(0, int(s.uptime - p.start_ticks / _CLK_TCK))


def _pcpu(p: _Process, s: _System) -> float:
    elapsed = _etime_s(p, s)
    return 100.0 * (p.cpu_ticks / _CLK_TCK) / elapsed if elapsed else 0.0


def _name(ident: int, table: dict[int, str]) -> str:
    if ident < 0:
        return '?'
    # Names come from the container's own /etc/passwd — hostile input.
    return safe_name(table.get(ident, str(ident)))


def _args_or_comm(p: _Process) -> str:
    # No cmdline (a kernel thread, or an unreadable one): bracket the stat
    # comm, as every ps implementation does.
    return p.args if p.args else f'[{p.comm}]'


def _stime(p: _Process, s: _System) -> str:
    if s.btime is None:
        return '?'
    return _fmt_stime(s.btime + p.start_ticks / _CLK_TCK, s.now)


def _lflags(p: _Process) -> int:
    # POSIX leaves F implementation-defined; mirror procps: 1 = forked but not
    # yet execed (PF_FORKNOEXEC), 4 = used superuser privileges.
    return (1 if p.flags & 0x40 else 0) | (4 if p.euid == 0 else 0)


# --------------------------------------------------------------------------- #
# Columns
# --------------------------------------------------------------------------- #
_Getter = Callable[[_Process, _System], str]
# Needs tags name the reads a column/selector depends on: 'args' -> cmdline
# per pid, 'ids' -> status per pid, 'unames'/'gnames' -> /etc/passwd//etc/group,
# 'uptime' -> /proc/uptime, 'btime' -> /proc/stat.
_Needs = frozenset[str]
_Column = tuple[str, bool, _Getter, _Needs]  # (header, right-align, getter, needs)

_NONE: _Needs = frozenset()
_USERS: _Needs = frozenset({'ids', 'unames'})
_GROUPS: _Needs = frozenset({'ids', 'gnames'})
_UPTIME: _Needs = frozenset({'uptime'})

# The -o vocabulary, exactly the names POSIX requires, with POSIX's default
# headers ("Variable Names" table in the ps STDOUT section).
_FIELDS: dict[str, _Column] = {
    'ruser': ('RUSER', False, lambda p, s: _name(p.ruid, s.users), _USERS),
    'user': ('USER', False, lambda p, s: _name(p.euid, s.users), _USERS),
    'rgroup': ('RGROUP', False, lambda p, s: _name(p.rgid, s.groups), _GROUPS),
    'group': ('GROUP', False, lambda p, s: _name(p.egid, s.groups), _GROUPS),
    'pid': ('PID', True, lambda p, s: str(p.pid), _NONE),
    'ppid': ('PPID', True, lambda p, s: str(p.ppid), _NONE),
    'pgid': ('PGID', True, lambda p, s: str(p.pgid), _NONE),
    'pcpu': ('%CPU', True, lambda p, s: f'{_pcpu(p, s):.1f}', _UPTIME),
    'vsz': ('VSZ', True, lambda p, s: str(p.vsize // 1024), _NONE),
    'nice': ('NI', True, lambda p, s: str(p.nice), _NONE),
    'etime': ('ELAPSED', True, lambda p, s: _fmt_etime(_etime_s(p, s)), _UPTIME),
    'time': ('TIME', True, lambda p, s: _fmt_time(p.cpu_ticks // _CLK_TCK), _NONE),
    'tty': ('TT', False, lambda p, s: _tty_name(p.tty_nr), _NONE),
    'comm': ('COMMAND', False, lambda p, s: safe_name(p.comm), _NONE),
    'args': ('COMMAND', False, lambda p, s: safe_name(_args_or_comm(p)), frozenset({'args'})),
}


def _col(name: str, header: str | None = None) -> _Column:
    default, right, getter, needs = _FIELDS[name]
    return (default if header is None else header, right, getter, needs)


_DEFAULT_COLUMNS: list[_Column] = [
    _col('pid'),
    _col('tty', 'TTY'),
    _col('time'),
    _col('comm', 'CMD'),
]

_FULL_COLUMNS: list[_Column] = [
    ('UID', False, lambda p, s: _name(p.euid, s.users), _USERS),
    _col('pid'),
    _col('ppid'),
    ('C', True, lambda p, s: str(int(_pcpu(p, s))), _UPTIME),
    ('STIME', True, _stime, frozenset({'btime'})),
    _col('tty', 'TTY'),
    _col('time'),
    _col('args', 'CMD'),
]

_LONG_COLUMNS: list[_Column] = [
    ('F', True, lambda p, s: str(_lflags(p)), frozenset({'ids'})),
    ('S', False, lambda p, s: p.state, _NONE),
    ('UID', True, lambda p, s: str(p.euid) if p.euid >= 0 else '?', frozenset({'ids'})),
    _col('pid'),
    _col('ppid'),
    ('C', True, lambda p, s: str(int(_pcpu(p, s))), _UPTIME),
    ('PRI', True, lambda p, s: str(p.priority), _NONE),
    _col('nice'),
    # ADDR is impl-defined and meaningless outside a kernel debugger; WCHAN
    # would cost one more round-trip per process (/proc/<pid>/wchan).
    ('ADDR', False, lambda p, s: '-', _NONE),
    ('SZ', True, lambda p, s: str(p.vsize // _PAGE_SIZE), _NONE),
    ('WCHAN', False, lambda p, s: '-', _NONE),
    _col('tty', 'TTY'),
    _col('time'),
    _col('comm', 'CMD'),
]


def _parse_format(specs: list[str]) -> list[_Column]:
    """Parse ``-o`` arguments into columns.

    Per POSIX, each argument is a comma/blank-separated list of field names;
    the first ``=`` makes the *remainder of that argument* (commas and all)
    the header of the field it follows — hence multiple ``-o`` options.
    """
    columns: list[_Column] = []
    for spec in specs:
        names_part, sep, header = spec.partition('=')
        names = [n for n in re.split(r'[,\s]+', names_part.strip()) if n]
        if not names:
            raise _OptionError('ps: empty -o format specification')
        for i, nm in enumerate(names):
            if nm not in _FIELDS:
                known = ', '.join(sorted(_FIELDS))
                raise _OptionError(f'ps: unknown -o field {nm!r} (known: {known})')
            custom = header if sep and i == len(names) - 1 else None
            columns.append(_col(nm, custom))
    return columns


def _render(columns: list[_Column], procs: list[_Process], system: _System) -> str:
    headers = [header for header, _, _, _ in columns]
    rows = [[getter(p, system) for _, _, getter, _ in columns] for p in procs]
    # POSIX: if all -o headers are null, no header line is written.
    lines = ([headers] if any(headers) else []) + rows
    if not lines:
        return ''
    widths = [max(len(line[i]) for line in lines) for i in range(len(columns))]
    out = []
    for line in lines:
        cells = [
            cell.rjust(widths[i]) if right else cell.ljust(widths[i])
            for i, (cell, (_, right, _, _)) in enumerate(zip(line, columns, strict=True))
        ]
        out.append(' '.join(cells).rstrip())
    return '\n'.join(out)


def _needed(columns: list[_Column], values: dict[str, list[str]]) -> _Needs:
    """The union of reads the chosen columns and selectors require."""
    needs: set[str] = set()
    for _, _, _, column_needs in columns:
        needs |= column_needs
    if 'u' in values or 'U' in values:
        needs |= _USERS  # status for the uids, passwd to resolve names
    if 'G' in values:
        needs |= _GROUPS
    return frozenset(needs)


# --------------------------------------------------------------------------- #
# Option parsing and selection
# --------------------------------------------------------------------------- #
def _parse_options(args: list[str]) -> tuple[set[str], dict[str, list[str]]]:
    flags: set[str] = set()
    values: dict[str, list[str]] = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if not arg.startswith('-') or arg == '-':
            raise _OptionError(
                f'ps: unexpected operand {arg!r} '
                '(borescope ps is POSIX ps and takes no operands; try -e, -ef, or -o)'
            )
        body = arg[1:]
        j = 0
        while j < len(body):
            ch = body[j]
            if ch in _FLAG_OPTS:
                flags.add(ch)
                j += 1
                continue
            if ch in _VALUED_OPTS:
                rest = body[j + 1 :]
                if not rest:
                    i += 1
                    if i >= len(args):
                        raise _OptionError(f'ps: option -{ch} requires an argument')
                    rest = args[i]
                values.setdefault(ch, []).append(rest)
                break
            raise _OptionError(f'ps: unknown option -{ch}')
        i += 1
    return flags, values


def _split_list(vals: list[str]) -> list[str]:
    """Flatten comma- or blank-separated option-argument lists."""
    return [tok for val in vals for tok in re.split(r'[,\s]+', val.strip()) if tok]


def _numeric_ids(tokens: list[str], what: str) -> set[int]:
    ids: set[int] = set()
    for tok in tokens:
        try:
            ids.add(int(tok))
        except ValueError:
            raise _OptionError(f'ps: invalid {what}: {tok!r}') from None
    return ids


def _resolve_ids(tokens: list[str], by_name: dict[str, int], what: str) -> set[int]:
    """Turn user/group list entries (names or numeric ids) into numeric ids."""
    ids: set[int] = set()
    for tok in tokens:
        if tok.isdigit():
            ids.add(int(tok))
        elif tok in by_name:
            ids.add(by_name[tok])
        else:
            raise _OptionError(f'ps: unknown {what}: {tok!r}')
    return ids


@dataclass
class _Selection:
    explicit: bool = False
    pids: set[int] = field(default_factory=set)
    sids: set[int] = field(default_factory=set)  # -g: session leaders
    ttys: set[str] = field(default_factory=set)
    euids: set[int] = field(default_factory=set)
    ruids: set[int] = field(default_factory=set)
    rgids: set[int] = field(default_factory=set)


def _build_selection(flags: set[str], values: dict[str, list[str]], system: _System) -> _Selection:
    sel = _Selection()
    sel.explicit = bool(flags & {'a', 'A', 'd', 'e'}) or bool(
        values.keys() & {'g', 'G', 'p', 't', 'u', 'U'}
    )
    sel.pids = _numeric_ids(_split_list(values.get('p', [])), 'process ID')
    sel.sids = _numeric_ids(_split_list(values.get('g', [])), 'session leader')
    for term in _split_list(values.get('t', [])):
        name = term.removeprefix('/dev/')
        sel.ttys.add(name)
        if name.isdigit():  # POSIX: a bare number means ttyN
            sel.ttys.add(f'tty{name}')
    sel.euids = _resolve_ids(_split_list(values.get('u', [])), system.uids, 'user')
    sel.ruids = _resolve_ids(_split_list(values.get('U', [])), system.uids, 'user')
    sel.rgids = _resolve_ids(_split_list(values.get('G', [])), system.gids, 'group')
    return sel


def _matches(p: _Process, flags: set[str], sel: _Selection) -> bool:
    if not sel.explicit:
        # DIVERGENCE from POSIX default selection — see module docstring.
        return True
    # POSIX: the selection options are additive (OR).
    if 'A' in flags or 'e' in flags:
        return True
    if 'a' in flags and p.tty_nr > 0 and p.pid != p.sid:
        return True
    if 'd' in flags and p.pid != p.sid:
        return True
    return (
        p.pid in sel.pids
        or p.sid in sel.sids
        or _tty_name(p.tty_nr) in sel.ttys
        or p.euid in sel.euids
        or p.ruid in sel.ruids
        or p.rgid in sel.rgids
    )


# --------------------------------------------------------------------------- #
# Reading /proc through the transport
# --------------------------------------------------------------------------- #
def _try_read(transport: Transport, path: str) -> str | None:
    # procfs files stat as size 0, so this must (and does) stream to EOF
    # rather than trusting the advertised size.
    try:
        with transport.pull(path, encoding=None) as handle:
            data = handle.read()
    except Exception:
        return None
    raw = data if isinstance(data, bytes) else data.encode('utf-8')
    return raw.decode('utf-8', errors='replace')


def _snapshot(transport: Transport, needs: _Needs) -> tuple[list[_Process], _System]:
    """Read what *needs* asks for and nothing more — each read is a round-trip."""
    infos = transport.list_files('/proc')
    pids = sorted(int(info.name) for info in infos if info.name.isdigit())

    procs: list[_Process] = []
    for pid in pids:
        stat_text = _try_read(transport, f'/proc/{pid}/stat')
        if stat_text is None:
            continue  # vanished between the listing and the read
        p = _parse_stat(stat_text)
        if p is None:
            continue
        if 'args' in needs:
            cmdline = _try_read(transport, f'/proc/{pid}/cmdline')
            p.args = _parse_cmdline(cmdline) if cmdline else ''
        if 'ids' in needs:
            status = _try_read(transport, f'/proc/{pid}/status')
            if status:
                p.ruid, p.euid, p.rgid, p.egid = _parse_status_ids(status)
        procs.append(p)

    system = _System(now=time.time())
    if 'uptime' in needs:
        uptime = _try_read(transport, '/proc/uptime')
        if uptime:
            with contextlib.suppress(ValueError, IndexError):
                system.uptime = float(uptime.split()[0])
    if 'btime' in needs:
        stat = _try_read(transport, '/proc/stat')
        if stat:
            for line in stat.splitlines():
                if line.startswith('btime '):
                    with contextlib.suppress(ValueError, IndexError):
                        system.btime = int(line.split()[1])
                    break
    # Distroless images may have no passwd/group at all; ids stay numeric.
    if 'unames' in needs:
        passwd = _try_read(transport, '/etc/passwd')
        if passwd:
            system.users = _parse_id_table(passwd)
            system.uids = {name: uid for uid, name in system.users.items()}
    if 'gnames' in needs:
        group = _try_read(transport, '/etc/group')
        if group:
            system.groups = _parse_id_table(group)
            system.gids = {name: gid for gid, name in system.groups.items()}
    return procs, system


# --------------------------------------------------------------------------- #
# The command
# --------------------------------------------------------------------------- #
class Ps(Command):
    name = 'ps'
    summary = 'Report process status (read from /proc; no ps binary needed)'
    usage = (
        'ps [-aAdefl] [-o format]... [-p pidlist] [-t termlist] [-u|-U userlist] [-g|-G grouplist]'
    )

    def run(self, ctx: ShellContext, args: list[str], stdin: str | None = None) -> Result:
        try:
            flags, values = _parse_options(args)
            if 'n' in values:
                raise _OptionError('ps: -n (alternative namelist) is not supported')
            columns = self._columns(flags, values)
        except _OptionError as exc:
            return Result.fail(str(exc))

        try:
            procs, system = _snapshot(ctx.transport, _needed(columns, values))
        except Exception as exc:
            return Result.fail(f'ps: cannot read /proc: {exc}')

        try:
            sel = _build_selection(flags, values, system)
        except _OptionError as exc:
            return Result.fail(str(exc))

        chosen = [p for p in procs if _matches(p, flags, sel)]
        output = _render(columns, chosen, system)
        if sel.explicit and not chosen:
            return Result(output=output, error='ps: no processes selected', code=1)
        return Result.ok(output)

    @staticmethod
    def _columns(flags: set[str], values: dict[str, list[str]]) -> list[_Column]:
        if 'o' in values:
            return _parse_format(values['o'])
        if 'l' in flags:
            return _LONG_COLUMNS
        if 'f' in flags:
            return _FULL_COLUMNS
        return _DEFAULT_COLUMNS
