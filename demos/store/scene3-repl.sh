#!/usr/bin/env bash
set -u
. /home/ubuntu/scenes/_lib.sh
clear
say "borescope bareshell/0"
borescope bareshell/0 <<EOF
services
checks
ls /usr/local/bin
EOF
sleep 2.5
