#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "poms_app.settings")

    sys.setrecursionlimit(10000)

    try:

        from django.core.management import execute_from_command_line

    except ImportError as exc:
        raise ImportError(
            f"Couldn't import Django. Are you sure it's installed and "
            f"available on your PYTHONPATH={sys.path} environment variable?"
            f" Did you forget to activate a virtual environment?"
        ) from exc

    execute_from_command_line(sys.argv)
