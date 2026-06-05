#!/usr/bin/env bash
set -u
. /home/ubuntu/scenes/_lib.sh
clear
echo "# Dump container state as JSON: services, plan, checks, system info"
echo "# (also includes pebble notices and recent_logs, not shown)."
sleep 1.2
say "borescope bareshell/0 --snapshot | jq ."
SNAP=$(borescope bareshell/0 --snapshot)
echo "$SNAP" | jq . | head -75
sleep 2.5
