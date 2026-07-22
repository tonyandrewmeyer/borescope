# Run one command (no REPL)

_Use borescope from scripts: run a single command and exit, or pipe a sequence of commands in on stdin._

Most of the time borescope is an interactive prompt. For scripts, aliases, and
CI, you can run it non-interactively instead.

{#command}
## Run one command

Pass `--command` to run a single command and exit, without ever entering the
REPL:

<pre><code><span class="prompt">$</span> borescope myapp/0 --command "services"
<span class="prompt">$</span> borescope myapp/0 --command "plan"
<span class="prompt">$</span> borescope myapp/0 --command "logs -n 100 myapp"</code></pre>

The command is parsed and run exactly as if you'd typed it at the prompt,
including pipes:

<pre><code><span class="prompt">$</span> borescope myapp/0 --command "logs -n 500 myapp | grep -i error"</code></pre>

Output goes to stdout, errors to stderr.

{#exit-codes}
## Exit codes

borescope's process exit code reflects what happened:

| Code | Meaning |
|---|---|
| `0` | The command ran and reported success. |
| `1` | The command failed, or discovery/connection failed (`borescope: …` on stderr). |
| `2` | Usage error: no unit reference and no `--here`/`--socket`. |

That makes `--command` safe to use in shell conditionals:

<pre><code><span class="prompt">$</span> if borescope myapp/0 --command "health" >/dev/null; then echo healthy; fi</code></pre>

{#stdin}
## Pipe a script on stdin

When borescope's stdin isn't a terminal and you haven't passed `--command`, it
reads commands from stdin one line at a time, runs each, and exits with the
status of the last:

<pre><code><span class="prompt">$</span> borescope myapp/0 &lt;&lt;'EOF'
services
plan
logs -n 50 myapp
EOF</code></pre>

Or pipe a file:

<pre><code><span class="prompt">$</span> cat checks.borescope | borescope myapp/0</code></pre>

Blank lines are skipped. This is handy for canned diagnostic runbooks you keep
in version control.

{#exec}
## Running container tools

`exec` works the same non-interactively, so you can reach any tool in the
container from a script:

<pre><code><span class="prompt">$</span> borescope myapp/0 --command "exec myapp-ctl reload"
<span class="prompt">$</span> borescope myapp/0 --command "exec /usr/bin/myapp --version"</code></pre>

{#tips}
## Scripting tips

- **Quote the whole command.** `--command "logs -n 100 myapp"` is one argument;
  borescope parses it the same way the REPL does.
- **Pick the model explicitly** in automation with `--model`, rather than
  relying on whatever model happens to be current.
- **Prefer `--snapshot`** when you want structured, machine-readable state
  rather than the human-formatted output of individual commands. See
  [Capture a state snapshot](howto-snapshot.html).
- **One unit per invocation.** borescope targets a single unit; loop in your
  shell to sweep several.
