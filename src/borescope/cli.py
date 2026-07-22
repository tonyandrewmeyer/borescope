# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""Command-line entry point for borescope.

Deliberately *out* of scope for v1, and worth marking explicitly: borescope has
no Canonical-spec verbosity ladder (`--quiet` / `--verbose` /
`--verbosity=debug|trace`). The tool's primary output is the REPL or a single
command's result, neither of which benefits from a five-level taxonomy, so we
stay minimal until a concrete need shows up.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys

from . import __version__

# How a shell reports a process killed by SIGPIPE (128 + signal 13).
_SIGPIPE_EXIT = 141


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level ``argparse`` parser."""
    parser = argparse.ArgumentParser(
        prog='borescope',
        description=('A natural shell for debugging Juju Kubernetes workload containers.'),
    )
    parser.add_argument('unit', nargs='?', help="unit reference, for example 'myapp/0'")
    parser.add_argument('--container', help='workload container name (default: first declared)')
    # Canonical CLI guidance is "don't offer both short and long" for the same
    # flag — `-m/--model` deliberately diverges to match `juju`'s own convention
    # (`juju ssh -m <model> …`), which is what users muscle-memory their way to
    # when reaching for borescope.
    parser.add_argument('-m', '--model', help='Juju model (default: current)')
    parser.add_argument(
        '--command',
        help='run a single command and exit (no REPL)',
    )
    parser.add_argument(
        '--snapshot',
        action='store_true',
        help='dump container state as JSON and exit',
    )
    parser.add_argument(
        '--socket',
        help='talk directly to a Pebble unix socket (skip juju)',
    )
    parser.add_argument(
        '--here',
        action='store_true',
        help=(
            "run inside the charm container: auto-detect a workload's mounted "
            'Pebble socket (use --container to pick when there are several)'
        ),
    )
    parser.add_argument('--juju', default='juju', help='juju binary to invoke (default: juju)')
    parser.add_argument(
        '--via',
        choices=('ssh', 'exec'),
        default='ssh',
        help=(
            "Juju relay for Mode B: 'ssh' (default, streaming) or 'exec' "
            '(request/response — for sites where ssh is disabled)'
        ),
    )
    parser.add_argument('--version', action='version', version=f'borescope {__version__}')
    return parser


def _build_target(args: argparse.Namespace):
    from .discovery import Target, resolve_local_target, resolve_target, validate_container_name

    if args.container is not None:
        validate_container_name(args.container)
    if args.here:
        return resolve_local_target(container=args.container)
    if args.socket:
        unit = args.unit or 'local'
        app = unit.split('/')[0]
        return Target(
            unit=unit,
            app=app,
            container=args.container,
            model=args.model,
            juju_binary=args.juju,
            socket_path=args.socket,
        )
    return resolve_target(
        args.unit,
        container=args.container,
        model=args.model,
        juju_binary=args.juju,
        via=args.via,
    )


def main(argv: list[str] | None = None) -> int:
    """Run borescope from the command line and return the exit code."""
    try:
        return _main(argv)
    except BrokenPipeError:
        # stdout's reader went away mid-write (`borescope … | head`). Die the
        # way a tool killed by SIGPIPE does — quietly, with the conventional
        # exit status — after pointing stdout at devnull so the interpreter's
        # exit-time flush cannot raise a second, unhandled BrokenPipeError.
        with contextlib.suppress(Exception):
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return _SIGPIPE_EXIT


def _main(argv: list[str] | None = None) -> int:
    # Accept Canonical-style `help` / `version` subcommands as aliases for the
    # Python-default `--help` / `--version`. Awkward to support both, but it
    # means the tool matches the standard *and* what `argparse` users expect.
    cli_args = sys.argv[1:] if argv is None else argv
    if cli_args[:1] == ['help']:
        build_parser().print_help()
        return 0
    if cli_args[:1] == ['version']:
        print(f'borescope {__version__}')
        return 0

    args = build_parser().parse_args(argv)

    # When running as a snap, stage the host's JUJU_DATA into the snap's
    # writable home so the bundled juju can refresh macaroons/cookies. No-op
    # outside the snap. See borescope.snap for the trade-offs.
    from .snap import stage_juju_data

    stage_juju_data()

    if not args.unit and not args.socket and not args.here:
        print(
            "borescope: A unit reference is required (for example 'borescope myapp/0'), "
            'or use --here when running inside a charm container.',
            file=sys.stderr,
        )
        return 2

    # Heavy imports happen only past argument parsing, keeping --help/--version fast.
    from .errors import BorescopeError
    from .shell import ShellContext
    from .transport import open_transport

    try:
        target = _build_target(args)
        transport = open_transport(
            unit=target.unit,
            container=target.container,
            model=target.model,
            juju_binary=target.juju_binary,
            socket_path=target.socket_path,
            via=target.via,
        )
        if args.snapshot:
            from .snapshot import snapshot_json

            print(snapshot_json(transport, target))
            return 0

        from .discovery import sanity_check

        sanity_check(transport, target)
    except BorescopeError as exc:
        print(f'borescope: {exc}', file=sys.stderr)
        return 1

    from .shell import Shell

    shell = Shell(ShellContext(transport=transport, target=target))

    if args.command is not None:
        return shell.execute_and_emit(args.command)

    if not sys.stdin.isatty():
        code = 0
        for line in sys.stdin:
            if line.strip():
                code = shell.execute_and_emit(line.rstrip('\n'))
        return code

    return shell.loop()


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
