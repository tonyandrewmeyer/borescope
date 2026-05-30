---
title: "How to copy files in and out — borescope"
description: "Pull files out of a shell-less Juju Kubernetes workload container, or push files in, with borescope's pull and push commands."
h1: "Copy files in and out"
subtitle: "Get a log or config file off a shell-less container, or push a patched file back in, over Pebble's files API."
section: howto
breadcrumb_label: "Copy files in and out"
on_this_page:
  - { anchor: "pull", label: "Pull a file out" }
  - { anchor: "push", label: "Push a file in" }
  - { anchor: "vs-cat", label: "pull/push vs cat/cp" }
  - { anchor: "limits", label: "What works, what doesn't" }
see_also:
  - { label: "Command reference", href: "reference-commands.html" }
  - { label: "Capture a state snapshot", href: "howto-snapshot.html" }
---

Because the workload rock often has no shell, you can't `scp` out of it the way
you might a machine. borescope moves files over Pebble's files API instead, with
two commands that cross the boundary between the container and your local host.

{#pull}
## Pull a file out

`pull <remote> <local>` copies a file *from the container* to your local
filesystem:

<pre><code><span class="prompt">pebble:/#</span> pull /var/log/myapp/error.log ./error.log
Pulled /var/log/myapp/error.log -&gt; ./error.log</code></pre>

The remote path is resolved relative to your current directory in the session,
so this works too:

<pre><code><span class="prompt">pebble:/#</span> cd /var/log/myapp
<span class="prompt">pebble:/var/log/myapp#</span> pull error.log ~/error.log</code></pre>

{#push}
## Push a file in

`push <local> <remote>` copies a local file *into the container*:

<pre><code><span class="prompt">pebble:/#</span> push ./fixed-config.yaml /etc/myapp/config.yaml
Pushed ./fixed-config.yaml -&gt; /etc/myapp/config.yaml</code></pre>

`push` creates any missing parent directories on the remote side, so you don't
need to `mkdir` first.

> Pushing a file changes the running container. Pebble won't restart a service
> for you — use [`restart`](reference-commands.html#pebble-native) afterwards if
> the workload needs to re-read the file.

{#vs-cat}
## pull/push vs cat/cp

borescope has a few overlapping ways to move bytes; pick by intent:

| Want to… | Use |
|---|---|
| Copy a file between the container and the host | `pull` / `push` |
| Read a file's contents to the terminal | `cat` |
| Copy a file *within* the container | `cp` |
| Save terminal output locally | redirect borescope's own stdout in your shell |

`pull`/`push` always cross the host/container boundary; `cp`, `mv`, `cat`,
`head`, and `tail` operate inside the container.

{#limits}
## What works, what doesn't

- **Single files.** `pull` and `push` move one file at a time. Loop in a script
  for several, or `exec tar` in the container to bundle a tree first.
- **Binary-safe.** Files are transferred as raw bytes, so binaries and archives
  survive the round trip intact.
- **Permissions follow Pebble.** A `push` writes with Pebble's defaults; the
  workload must have permission to read the destination path.
- **No globbing.** Paths are literal — `pull /var/log/*.log` won't expand. Use
  `find` to locate files, then pull them by name.
