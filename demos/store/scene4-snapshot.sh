#!/usr/bin/env bash
set -u
. /home/ubuntu/scenes/_lib.sh
clear
echo "# Dump container state as JSON: services, plan, checks, system info."
sleep 1.2
say "borescope bareshell/0 --snapshot | jq ."
# Two-step to avoid a SIGPIPE on jq if downstream closes early.
SNAPSHOT=$(borescope bareshell/0 --snapshot)
echo "$SNAPSHOT" | jq . 2>/dev/null | sed -n "1,28p"
sleep 2.5
