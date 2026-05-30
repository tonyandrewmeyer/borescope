# Copyright 2026 Tony Meyer
# SPDX-License-Identifier: Apache-2.0

"""``python -m borescope`` entry point."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == '__main__':
    sys.exit(main())
