#!/usr/bin/python3

import argparse
import os
import subprocess
import sys
from pathlib import Path

python_root = Path(os.path.realpath(os.path.dirname(__file__))) / ".."
bin_dir = python_root / "bin"

parser = argparse.ArgumentParser(description="Runs flake8 against all Python code in this directory. Any passed arguments will be added to the flake8 invocation command line.")
_, extra_args = parser.parse_known_args()

extra_files = []

# flake8 can recursively process a directory with Python files but seems not
# able to determine script files that don't end in *.py, therefore assemble a
# list of extra files to explicitly pass to flake8.
for fl in os.listdir(bin_dir):
    _, ext = os.path.splitext(fl)
    if ext in (".py", ".pyc", ".swp"):
        continue
    elif fl == "__pycache__":
        continue

    extra_files.append(f"bin/{fl}")

# E265: block comments should have one space before the text
#       -> disagree, because I want to be able to comment out code lines
#          without having to add nonsensical spaces in front.
# E501: line too long: let's not be too annoying about that
cmdline = ["flake8", "--max-line-length=120", "--ignore=E265,E501", "."] + extra_files + extra_args
print(' '.join([str(arg) for arg in cmdline]))
print()
sys.stdout.flush()
res = subprocess.call(cmdline, cwd=python_root)

sys.exit(res)
