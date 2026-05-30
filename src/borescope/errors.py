# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""borescope's error hierarchy."""

from __future__ import annotations


class BorescopeError(Exception):
    """Base class for all borescope errors."""


class DiscoveryError(BorescopeError):
    """Raised when a unit/model/container cannot be resolved or reached."""


class JujuError(BorescopeError):
    """Raised when an underlying ``juju`` invocation fails."""

    def __init__(self, message: str, *, returncode: int | None = None, stderr: str = ''):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr
