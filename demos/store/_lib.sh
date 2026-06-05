# Shared helpers for borescope demo scenes.
say() {
    printf "\033[1;32m$\033[0m "
    sleep 0.25
    local s=$1
    for ((i=0; i<${#s}; i++)); do
        printf "%s" "${s:i:1}"
        sleep 0.02
    done
    echo
    sleep 0.3
}
run() {
    say "$1"
    eval "$1"
    sleep 0.8
}
pause() { sleep "${1:-1}"; }
