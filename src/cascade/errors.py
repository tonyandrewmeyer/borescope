"""cascade's error hierarchy."""

from __future__ import annotations


class CascadeError(Exception):
    """Base class for all cascade errors."""


class DiscoveryError(CascadeError):
    """Raised when a unit/model/container cannot be resolved or reached."""


class TransportError(CascadeError):
    """Raised when the chosen transport cannot talk to a Pebble."""


class JujuError(CascadeError):
    """Raised when an underlying ``juju`` invocation fails."""

    def __init__(
        self, message: str, *, returncode: int | None = None, stderr: str = ""
    ):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr
