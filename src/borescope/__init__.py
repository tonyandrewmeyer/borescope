# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""borescope - a natural shell for debugging Juju Kubernetes workload containers."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version('borescope')
except PackageNotFoundError:  # pragma: no cover - running from an uninstalled tree
    __version__ = '0.0.0+unknown'

__all__ = ['__version__']
