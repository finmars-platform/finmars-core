#!/usr/bin/env bash
cd docs/source &&
sphinx-apidoc -o ./files ../../ ../../*migrations* ../../*tests* ../../*admin* ../../*apps* --separate --module-first
