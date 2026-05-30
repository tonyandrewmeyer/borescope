"""A tiny getopt-ish argument splitter shared by the built-in commands.

Not a full argparse — these are debug-shell commands, so we want forgiving,
familiar behaviour (``-la``, ``-n10``, ``-n 10``, ``--follow``) without per-command
boilerplate.
"""

from __future__ import annotations


def parse_args(
    args: list[str], valued: tuple[str, ...] = ()
) -> tuple[set[str], dict[str, str], list[str]]:
    """Split *args* into ``(flags, values, positionals)``.

    *valued* names flags that take a value (e.g. ``("n",)`` for ``-n N`` /
    ``("name",)`` for ``--name X``). Everything after ``--`` is positional.
    """
    flags: set[str] = set()
    values: dict[str, str] = {}
    positionals: list[str] = []

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            positionals.extend(args[i + 1 :])
            break
        if arg.startswith("--"):
            name = arg[2:]
            if name in valued:
                i += 1
                values[name] = args[i] if i < len(args) else ""
            else:
                flags.add(name)
        elif len(arg) > 1 and arg[0] == "-" and not arg[1].isdigit():
            body = arg[1:]
            j = 0
            while j < len(body):
                ch = body[j]
                if ch in valued:
                    rest = body[j + 1 :]
                    if rest:
                        values[ch] = rest
                    else:
                        i += 1
                        values[ch] = args[i] if i < len(args) else ""
                    break
                flags.add(ch)
                j += 1
        else:
            positionals.append(arg)
        i += 1
    return flags, values, positionals
