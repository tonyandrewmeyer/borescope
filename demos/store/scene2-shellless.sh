#!/usr/bin/env bash
set -u
. /home/ubuntu/scenes/_lib.sh
clear
echo "# Distroless workload: no shell, no busybox."
echo "# \"juju ssh --container=workload\" cannot help here."
sleep 1
say "juju ssh --container workload bareshell/0 -- ls /"
juju ssh --container workload bareshell/0 -- ls / 2>&1 || true
sleep 2
echo
echo "# borescope drives the Pebble socket instead."
sleep 1
say "borescope bareshell/0 --command \"ls /\""
borescope bareshell/0 --command "ls /"
sleep 2
