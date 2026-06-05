#!/usr/bin/env bash
set -u
. /home/ubuntu/scenes/_lib.sh
clear
say "borescope bareshell/0"
expect -c '
set send_human {.04 .06 .1 .04 .1}
spawn -noecho borescope bareshell/0
expect "pebble:/# "
sleep 0.6
send -h "services\r"
expect "pebble:/# "
sleep 0.9
send -h "checks\r"
expect "pebble:/# "
sleep 0.9
send -h "ls /usr/local/bin\r"
expect "pebble:/# "
sleep 0.9
send -h "exit\r"
expect eof
'
sleep 1.5
