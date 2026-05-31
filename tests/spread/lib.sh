# Shared helpers for borescope spread tasks. Source this from a task's
# execute: block, then drive borescope via the `borescope_run` wrapper.
#
#   source "${SPREAD_PATH}/tests/spread/lib.sh"
#   pebble_up
#   borescope_run --command 'ls /etc' | MATCH hostname
#   pebble_down

# Bring up a fresh Pebble in a temporary directory and export PEBBLE/PEBBLE_SOCK.
pebble_up() {
    PEBBLE="$(mktemp -d)"
    export PEBBLE
    PEBBLE_SOCK="${PEBBLE}/.pebble.socket"
    export PEBBLE_SOCK
    mkdir -p "${PEBBLE}/layers"

    # --hold keeps services declared but not auto-started, so a task can
    # populate the layer config without races against running services.
    pebble run --hold >"${PEBBLE}/pebble.log" 2>&1 &
    PEBBLE_PID=$!
    export PEBBLE_PID

    # Wait for the socket to appear (up to 10s).
    for _ in $(seq 1 100); do
        if [ -S "${PEBBLE_SOCK}" ]; then
            return 0
        fi
        sleep 0.1
    done
    echo "pebble_up: socket did not appear at ${PEBBLE_SOCK}" >&2
    cat "${PEBBLE}/pebble.log" >&2 || true
    return 1
}

# Tear down the Pebble started by pebble_up.
pebble_down() {
    if [ -n "${PEBBLE_PID:-}" ]; then
        kill "${PEBBLE_PID}" 2>/dev/null || true
        wait "${PEBBLE_PID}" 2>/dev/null || true
        unset PEBBLE_PID
    fi
    if [ -n "${PEBBLE:-}" ] && [ -d "${PEBBLE}" ]; then
        rm -rf "${PEBBLE}"
        unset PEBBLE PEBBLE_SOCK
    fi
}

# spread runs task scripts in a non-login shell, so /etc/profile.d/* isn't
# sourced. Make sure uv (and the pebble binary) are reachable from PATH.
export PATH="/root/.local/bin:/usr/local/bin:${PATH}"

# Path to the borescope entry point inside the synced venv. Invoking the binary
# directly (rather than `uv run borescope`) avoids uv's stderr chatter
# polluting per-task "stderr should be empty" assertions.
BORESCOPE="${SPREAD_PATH}/.venv/bin/borescope"

# Run borescope against the per-task Pebble socket. Forwards all args.
borescope_run() {
    "${BORESCOPE}" --socket "${PEBBLE_SOCK}" "$@"
}

# Drive multiple commands through a single REPL session by piping them on
# stdin. Shell-side state (cwd, env) persists across lines, which the v1
# pipeline grammar can't otherwise express within a single -c invocation.
# Feed lines via printf; YAML block scalars indent heredocs, which breaks
# bash's "EOF must be at column 0" rule.
#
#   printf 'cd /etc\npwd\n' | borescope_script
borescope_script() {
    "${BORESCOPE}" --socket "${PEBBLE_SOCK}"
}

# Seed a file inside the Pebble-visible filesystem. Pebble's pull/push talks to
# the host filesystem, so we just write the file directly under the tmp PEBBLE
# root unless the task wants a real path elsewhere.
seed_file() {
    local path="$1"
    local contents="$2"
    mkdir -p "$(dirname "${path}")"
    printf '%s' "${contents}" > "${path}"
}
