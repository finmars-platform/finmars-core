#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "poms_app.settings")

    sys.setrecursionlimit(10000)

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
