# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""The `ps` built-in (POSIX ps read from /proc) against the fake transport."""

from __future__ import annotations

import pytest

from borescope.shell.commands.base import build_registry
from borescope.shell.commands.proc import (
    _fmt_etime,
    _fmt_time,
    _parse_cmdline,
    _parse_stat,
    _tty_name,
)

PTS0 = 136 << 8  # major 136, minor 0 -> pts/0


@pytest.fixture
def registry():
    return build_registry()


def run(registry, ctx, name, *args, stdin=None):
    return registry[name].run(ctx, list(args), stdin)


def seed_proc(
    transport,
    pid,
    *,
    comm='app',
    state='S',
    ppid=0,
    pgid=None,
    sid=None,
    tty_nr=0,
    utime=0,
    stime=0,
    nice=0,
    start_ticks=0,
    vsize=0,
    cmdline=None,
    uid=0,
    gid=0,
):
    """Write a minimal but stat(5)-shaped /proc/<pid>/ tree into the fake."""
    pgid = pid if pgid is None else pgid
    sid = pid if sid is None else sid
    stat = (
        f'{pid} ({comm}) {state} {ppid} {pgid} {sid} {tty_nr} -1 4194304 '
        f'0 0 0 0 {utime} {stime} 0 0 20 {nice} 1 0 {start_ticks} {vsize} 100 '
        '18446744073709551615 1 1 0 0 0 0 0 0 0 0 0 0 17 0 0 0 0 0 0'
    )
    transport.add_file(f'/proc/{pid}/stat', stat)
    if cmdline is None:
        cmdline = f'{comm}\x00'
    transport.add_file(f'/proc/{pid}/cmdline', cmdline)
    transport.add_file(
        f'/proc/{pid}/status',
        f'Name:\t{comm}\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\nGid:\t{gid}\t{gid}\t{gid}\t{gid}\n',
    )


@pytest.fixture
def proc_ctx(ctx, transport):
    transport.add_file('/proc/uptime', '500.00 400.00\n')
    transport.add_file('/proc/stat', 'cpu  1 2 3 4\nbtime 1700000000\n')
    seed_proc(transport, 1, comm='init', cmdline='init --system\x00')
    seed_proc(transport, 42, comm='myapp', cmdline='myapp\x00--config\x00/etc/app.yaml\x00')
    return ctx


# -- default format ----------------------------------------------------------
def test_ps_default_header_and_rows(registry, proc_ctx):
    result = run(registry, proc_ctx, 'ps')
    lines = result.output.split('\n')
    assert result.code == 0
    assert lines[0].split() == ['PID', 'TTY', 'TIME', 'CMD']
    assert lines[1].split() == ['1', '?', '00:00:00', 'init']
    assert lines[2].split() == ['42', '?', '00:00:00', 'myapp']


def test_ps_default_shows_comm_not_args(registry, proc_ctx):
    result = run(registry, proc_ctx, 'ps')
    assert '--config' not in result.output


def test_ps_default_lists_other_users_divergence(registry, proc_ctx, transport):
    # POSIX default selection is "same euid and controlling terminal as the
    # invoker"; borescope has no invoker in the container, so everything shows.
    seed_proc(transport, 100, comm='other', uid=1000)
    result = run(registry, proc_ctx, 'ps')
    assert 'other' in result.output


def test_ps_pid_column_right_aligned(registry, proc_ctx):
    lines = run(registry, proc_ctx, 'ps').output.split('\n')
    assert lines[1].index('1') == lines[0].index('D')  # PID right-aligns under header


# -- full (-f) and long (-l) formats -----------------------------------------
def test_ps_full_format(registry, proc_ctx):
    result = run(registry, proc_ctx, 'ps', '-ef')
    lines = result.output.split('\n')
    assert lines[0].split() == ['UID', 'PID', 'PPID', 'C', 'STIME', 'TTY', 'TIME', 'CMD']
    # -f resolves the euid via /etc/passwd and shows full args.
    assert lines[1].split()[0] == 'root'
    assert 'myapp --config /etc/app.yaml' in result.output


def test_ps_long_format(registry, proc_ctx):
    lines = run(registry, proc_ctx, 'ps', '-l').output.split('\n')
    assert lines[0].split() == [
        'F', 'S', 'UID', 'PID', 'PPID', 'C', 'PRI', 'NI',
        'ADDR', 'SZ', 'WCHAN', 'TTY', 'TIME', 'CMD',
    ]  # fmt: skip
    row = lines[1].split()
    assert row[1] == 'S'  # state from stat
    assert row[2] == '0'  # numeric UID in -l


# -- -o user-defined format --------------------------------------------------
def test_ps_o_fields_default_headers(registry, proc_ctx):
    result = run(registry, proc_ctx, 'ps', '-o', 'pid,comm')
    lines = result.output.split('\n')
    assert lines[0].split() == ['PID', 'COMMAND']
    assert lines[1].split() == ['1', 'init']


def test_ps_o_custom_header(registry, proc_ctx):
    result = run(registry, proc_ctx, 'ps', '-o', 'pid=MyPid')
    assert result.output.split('\n')[0].strip() == 'MyPid'


def test_ps_o_empty_headers_suppress_header_line(registry, proc_ctx):
    result = run(registry, proc_ctx, 'ps', '-o', 'pid=')
    assert result.output.split('\n')[0].strip() == '1'


def test_ps_o_repeated_options_concatenate(registry, proc_ctx):
    result = run(registry, proc_ctx, 'ps', '-o', 'pid=P', '-o', 'comm=C')
    lines = result.output.split('\n')
    assert lines[0].split() == ['P', 'C']
    assert lines[1].split() == ['1', 'init']


def test_ps_o_unknown_field_errors(registry, proc_ctx):
    result = run(registry, proc_ctx, 'ps', '-o', 'pid,bogus')
    assert result.code == 1
    assert "unknown -o field 'bogus'" in result.error


def test_ps_o_computed_fields(registry, proc_ctx, transport):
    # 120s of CPU over 300s of elapsed time -> 40.0 %CPU; vsize in KiB.
    seed_proc(transport, 7, comm='busy', utime=6000, stime=6000, start_ticks=20000, vsize=10485760)
    result = run(registry, proc_ctx, 'ps', '-o', 'pid,pcpu,vsz,etime,time', '-p', '7')
    assert result.output.split('\n')[1].split() == ['7', '40.0', '10240', '05:00', '00:02:00']


# -- selection ---------------------------------------------------------------
def test_ps_p_selects_pids(registry, proc_ctx):
    result = run(registry, proc_ctx, 'ps', '-p', '42')
    lines = result.output.split('\n')
    assert len(lines) == 2
    assert 'myapp' in lines[1]
    assert 'init' not in result.output


def test_ps_p_no_match_exits_1(registry, proc_ctx):
    result = run(registry, proc_ctx, 'ps', '-p', '999')
    assert result.code == 1
    assert 'no processes selected' in result.error
    assert result.output.split() == ['PID', 'TTY', 'TIME', 'CMD']  # header still written


def test_ps_p_invalid_pid_errors(registry, proc_ctx):
    result = run(registry, proc_ctx, 'ps', '-p', 'abc')
    assert result.code == 1
    assert 'invalid process ID' in result.error


def test_ps_u_by_name_and_uid(registry, proc_ctx, transport):
    seed_proc(transport, 100, comm='workerd', uid=1)
    by_name = run(registry, proc_ctx, 'ps', '-u', 'daemon')
    by_uid = run(registry, proc_ctx, 'ps', '-u', '1')
    assert 'workerd' in by_name.output
    assert 'init' not in by_name.output
    assert by_name.output == by_uid.output


def test_ps_u_unknown_user_errors(registry, proc_ctx):
    result = run(registry, proc_ctx, 'ps', '-u', 'nobody')
    assert result.code == 1
    assert "unknown user: 'nobody'" in result.error


def test_ps_a_terminal_processes_excluding_session_leaders(registry, proc_ctx, transport):
    seed_proc(transport, 10, comm='leader', tty_nr=PTS0)  # session leader with a tty
    seed_proc(transport, 11, comm='child', sid=10, tty_nr=PTS0)
    result = run(registry, proc_ctx, 'ps', '-a')
    assert 'child' in result.output
    assert 'leader' not in result.output
    assert 'init' not in result.output  # no controlling terminal


def test_ps_d_all_but_session_leaders(registry, proc_ctx, transport):
    seed_proc(transport, 11, comm='child', sid=1)
    result = run(registry, proc_ctx, 'ps', '-d')
    assert 'child' in result.output
    assert 'init' not in result.output


def test_ps_t_selects_by_terminal(registry, proc_ctx, transport):
    seed_proc(transport, 11, comm='attached', tty_nr=PTS0)
    result = run(registry, proc_ctx, 'ps', '-t', 'pts/0')
    assert 'attached' in result.output
    assert 'init' not in result.output


def test_ps_selection_options_are_additive(registry, proc_ctx):
    # POSIX: "processes selected by any of them" — OR, not AND.
    result = run(registry, proc_ctx, 'ps', '-p', '1', '-u', 'daemon')
    assert 'init' in result.output


# -- robustness --------------------------------------------------------------
def test_ps_kernel_thread_style_brackets_comm(registry, proc_ctx, transport):
    seed_proc(transport, 2, comm='kthreadd', cmdline='')
    result = run(registry, proc_ctx, 'ps', '-o', 'pid,args', '-p', '2')
    assert '[kthreadd]' in result.output


def test_ps_comm_with_spaces_and_parens(registry, proc_ctx, transport):
    seed_proc(transport, 50, comm='tmux: server) (x')
    result = run(registry, proc_ctx, 'ps', '-o', 'comm', '-p', '50')
    assert 'tmux: server) (x' in result.output


def test_ps_hostile_comm_is_defanged(registry, proc_ctx, transport):
    seed_proc(transport, 66, comm='e\x1b[2Jvil')
    result = run(registry, proc_ctx, 'ps', '-p', '66')
    assert '\x1b' not in result.output
    assert '\\x1b' in result.output


def test_ps_vanished_process_is_skipped(registry, proc_ctx, transport):
    transport.add_dir('/proc/999')  # listed, but its stat is gone
    result = run(registry, proc_ctx, 'ps')
    assert result.code == 0
    assert '999' not in result.output


def test_ps_missing_passwd_falls_back_to_numeric(registry, proc_ctx, transport):
    del transport.files['/etc/passwd']
    seed_proc(transport, 100, comm='other', uid=1000)
    result = run(registry, proc_ctx, 'ps', '-o', 'user,pid', '-p', '100')
    assert result.output.split('\n')[1].split() == ['1000', '100']


def test_ps_rejects_operands(registry, proc_ctx):
    result = run(registry, proc_ctx, 'ps', 'aux')
    assert result.code == 1
    assert 'operand' in result.error


def test_ps_unknown_option_errors(registry, proc_ctx):
    result = run(registry, proc_ctx, 'ps', '-z')
    assert result.code == 1
    assert 'unknown option -z' in result.error


# -- pure helpers ------------------------------------------------------------
def test_tty_name_decoding():
    assert _tty_name(0) == '?'
    assert _tty_name(PTS0) == 'pts/0'
    assert _tty_name((136 << 8) | 3) == 'pts/3'
    assert _tty_name((4 << 8) | 1) == 'tty1'
    assert _tty_name((4 << 8) | 64) == 'ttyS0'


def test_fmt_time():
    assert _fmt_time(0) == '00:00:00'
    assert _fmt_time(3661) == '01:01:01'
    assert _fmt_time(90061) == '1-01:01:01'


def test_fmt_etime():
    assert _fmt_etime(59) == '00:59'
    assert _fmt_etime(3661) == '01:01:01'
    assert _fmt_etime(90061) == '1-01:01:01'


def test_parse_stat_malformed_returns_none():
    assert _parse_stat('not a stat line') is None
    assert _parse_stat('1 (x) S 0') is None  # too few fields


def test_parse_cmdline():
    assert _parse_cmdline('a\x00b c\x00') == 'a b c'
    assert _parse_cmdline('') == ''
