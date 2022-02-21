#!/usr/bin/env python

import os
import sys
import pkgutil


def tryFindModule(module):
    """Adds .. to the current module path, tries to import $module and exits if it is not found."""
    # get the full path of the parent directory and append the name
    parent_dir = os.path.realpath(os.path.dirname(os.path.dirname(__file__)))
    sys.path.append(parent_dir)

    # check if the module can be loaded now
    if pkgutil.find_loader(module) is None:
        print("The module %s could not be found in '%s'!" % (module, parent_dir))
        sys.exit(4)


tryFindModule("oscfs")
