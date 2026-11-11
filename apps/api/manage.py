#!/usr/bin/env python
"""Django management entry point for the Groupy API."""

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - env setup hint only
        raise ImportError(
            "Couldn't import Django. Is the virtualenv active and the "
            "package installed? (pip install -e '.[dev]')"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
