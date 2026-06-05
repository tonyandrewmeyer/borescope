#!/usr/bin/env bash
set -u
. /home/ubuntu/scenes/_lib.sh
JUJU=/home/ubuntu/juju-build/juju
clear
echo "# snappass-test has two workload containers: redis and snappass."
echo "# Run borescope inside the charm container with --here, pick one with --container."
sleep 1.5
say "juju ssh snappass-test/0 borescope --here --container redis --command services"
$JUJU ssh snappass-test/0 /root/.local/bin/borescope --here --container redis --command services
sleep 1.2
say "juju ssh snappass-test/0 borescope --here --container snappass --command services"
$JUJU ssh snappass-test/0 /root/.local/bin/borescope --here --container snappass --command services
sleep 2
