#!/usr/bin/env bash
set -u
. /home/ubuntu/scenes/_lib.sh
clear
say "sudo snap install borescope"
echo "borescope 1.0.2 from Tony Meyer installed"
sleep 0.5
say "sudo snap connect borescope:juju-client-observe"
sleep 0.3
say "sudo snap connect borescope:ssh-keys"
sleep 0.5
say "borescope --version"
borescope --version
sleep 1.2
say "borescope bareshell/0 --command services"
borescope bareshell/0 --command services
sleep 2
