#!/usr/bin/env bash
cd docs/source &&
sphinx-apidoc -o ./files ../../ ../../*migrations* ../../*tests* --separate --module-first
