# Command reference

_The complete built-in command set, plus the grammar the REPL understands._

borescope ships a deliberately small command set. Pebble's own vocabulary is
first-class, the familiar file commands are implemented over Pebble's files API,
and [`exec`](#exec) runs anything else that's already in the container. Run
[`help`](#help) at the prompt for a live list.

{#grammar}
## Line grammar

The REPL parser is intentionally tiny: **one command at a time, with at most a
single `|` pipe between two stages.** Variables (`$VAR`, `${VAR}`) expand from
the session's tracked environment.

These shell features are **not** supported, and borescope reports a clear error
rather than doing something surprising:

- sequencing (`;`)
- background jobs (`&`)
- `&&` and `||`
- redirection (`>`, `>>`, `<`)
- subshells (`( … )`)

That covers the overwhelming majority of debug-shell use; for anything that
needs a real shell, [`exec`](#exec) a binary in the container.

{#builtins}
## Shell built-ins

State and session commands.

| Command | Usage | Description |
|---|---|---|
| `cd` | `cd [dir]` | Change the current directory (defaults to `~`). |
| `pwd` | `pwd` | Print the current directory. |
| `echo` | `echo [args…]` | Write arguments to output. |
| `env` | `env` | Show the shell's tracked environment. |
| `clear` | `clear` | Clear the screen. |
| `help`, `?` | `help` | List available commands. |
| `exit`, `quit` | `exit [code]` | Leave borescope (optionally with an exit code). <kbd>Ctrl-D</kbd> also exits. |

{#files}
## File commands

These are built in, rather than left to `exec`, because they need either
session state (paths relative to the current directory) or Pebble's files API,
so they work against a rock with no shell and no coreutils.

| Command | Usage | Description |
|---|---|---|
| `ls` | `ls [-l] [-a] [path…]` | List directory contents. |
| `cat` | `cat [file…]` | Concatenate and print files. |
| `head` | `head [-n N] [file]` | Print the first lines of input. |
| `tail` | `tail [-n N] [-f] [file]` | Print the last lines of input; `-f` follows. |
| `find` | `find [path] [-name PATTERN] [-type f\|d]` | Walk the tree, filtering by name/type. |
| `stat` | `stat <path…>` | Show file metadata. |
| `grep` | `grep [-i] [-v] [-n] [-c] PATTERN [file…]` | Search input for a pattern. |
| `cp` | `cp <src> <dst>` | Copy a file within the container. |
| `mv` | `mv <src> <dst>` | Move or rename a file. |
| `rm` | `rm [-r] [-f] <path…>` | Remove files or directories. |
| `mkdir` | `mkdir [-p] <path…>` | Create directories. |
| `touch` | `touch <path…>` | Create an empty file if it doesn't exist. |
| `pull` | `pull <remote> <local>` | Copy a file from the container to the local host. |
| `push` | `push <local> <remote>` | Copy a local file into the container. |

`pull` and `push` cross the host/container boundary; the rest operate inside the
container. See [Copy files in and out](howto-files.html).

{#pebble-native}
## Pebble-native commands

Pebble's operational vocabulary, exposed directly, no `pebble` prefix.

| Command | Usage | Description |
|---|---|---|
| `services` | `services [--format=json\|yaml] [--no-headers] [name…]` | List services and their status. |
| `start` | `start <service…>` | Start services. |
| `stop` | `stop <service…>` | Stop services. |
| `restart` | `restart <service…>` | Restart services. |
| `replan` | `replan` | Apply the plan: stop/start services as the plan requires. |
| `plan` | `plan` | Show the merged Pebble plan (YAML). |
| `logs` | `logs [-f\|--follow] [-n N] [service…]` | Show service logs; `-f` streams. |
| `checks` | `checks [--format=json\|yaml] [--no-headers] [name…]` | List health checks and their status. |
| `health` | `health` | Report overall health (are all checks up?). |
| `notices` | `notices [--format=json\|yaml] [--no-headers]` | List recent notices. |
| `notice` | `notice <id>` | Show a single notice by ID. |
| `notify` | `notify <key> [data-key=value…]` | Record a custom notice. |
| `changes` | `changes [--format=json\|yaml] [--no-headers]` | List recent changes. |
| `tasks` | `tasks [--format=json\|yaml] [--no-headers] [change-id]` | Show tasks for a change (defaults to the most recent). |

`start`, `stop`, `restart`, and `replan` change the running container. `logs
--follow` and `tail -f` stream until you press <kbd>Ctrl-C</kbd> and can't be
used inside a pipe.

### Tabular output

The list commands above (`services`, `checks`, `notices`, `changes`, `tasks`)
follow the same convention:

- Headers are UPPER CASE and bold; columns are separated by two spaces. Pass
  `--no-headers` to suppress the header line (handy for piping into `awk`,
  `cut`, or `sort`).
- When the listing is empty, a short note goes to **stderr** (`No services
  configured.`, `No checks configured.`, …) and the exit code stays `0`.
  Stdout is empty, so `borescope myapp/0 --command services | wc -l` reports
  `0` when there are no services.
- `--format=json` and `--format=yaml` emit a machine-readable form instead of
  the table. Empty lists render as `[]` (JSON) or `items: []` (YAML), again
  with exit code `0` and no stderr noise.

{#exec}
## exec

```
exec <command> [args…]
```

The escape hatch. `exec` runs a program that is **already present in the
container**, in your current session directory, and reports its stdout, stderr,
and exit code:

<pre><code><span class="prompt">pebble:/#</span> exec ps aux
<span class="prompt">pebble:/#</span> exec cat /proc/1/cmdline
<span class="prompt">pebble:/#</span> exec /usr/bin/myapp --version</code></pre>

If the binary isn't in the rock, `exec` reports that it couldn't run it, which
is expected on a minimal image. borescope doesn't bundle tools into the
container; `exec` only reaches what's there. See
[Scope and philosophy](explanation-scope.html).

{#help}
## Getting help in-session

`help` (or `?`) lists every built-in command with its one-line summary, and
reminds you that anything else can be run with `exec`:

<pre><code><span class="prompt">pebble:/#</span> help
Built-in commands (anything else: 'exec &lt;cmd&gt; ...' runs it in the container):
  cat       Concatenate and print files
  cd        Change the current directory
  …</code></pre>
