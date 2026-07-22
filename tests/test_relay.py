# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""The Juju relay used for Pebble subcommands the ops client doesn't expose."""

from __future__ import annotations

import dataclasses

from borescope.transport import relay
from borescope.transport.runner import JujuExecRunner, JujuSshRunner


def test_relay_uses_the_charm_injected_binary(target):
    prefix, env, runner = relay.pebble_relay(target)
    # Juju injects pebble here in every k8s charm container, but does not put it
    # on $PATH — so the absolute path, not a bare name.
    assert prefix == ['/charm/bin/pebble']
    # The runner supplies PEBBLE_SOCKET itself via the charm container.
    assert env is None
    assert isinstance(runner, JujuSshRunner)


def test_relay_honours_via_exec(target):
    _, _, runner = relay.pebble_relay(dataclasses.replace(target, via='exec'))
    assert isinstance(runner, JujuExecRunner)


def test_relay_falls_back_to_ssh_for_an_unknown_via(target):
    _, _, runner = relay.pebble_relay(dataclasses.replace(target, via='telepathy'))
    assert isinstance(runner, JujuSshRunner)
