#!/usr/bin/env python2

from __future__ import with_statement, print_function

from setuptools import setup
import os, sys


pkg_root = os.path.abspath(os.path.dirname(__file__))
readme_rst = os.path.join( pkg_root, "README.rst" )
remove_rst = False

def getLongDesc():
	global remove_rst

	if not os.path.exists(readme_rst):
		# dynamically generate a restructured text formatted long description
		# from markdown for setuptools to use
		import subprocess
		subprocess.check_call(
			[ "/usr/bin/pandoc", "-f", "markdown", "-t", "rst", "-o", "README.rst", "README.md" ]
		)
		remove_rst = True

	with open(readme_rst, 'r') as rst_file:
		long_desc = rst_file.read()

	return long_desc

long_desc = getLongDesc()

try:
	setup(
		name = 'oscfs',
		version = '0.5.0',
		description = 'A FUSE based file system to access Open Build Service (OBS) instances',
		long_description = long_desc,
		author = 'Matthias Gerstner',
		author_email = 'mgerstner@suse.de',
		license = 'GPL2',
		keywords = 'fuse obs osc openSUSE',
		packages = ['oscfs'],
		install_requires = ['osc', 'fusepy'],
		#url = 'https://github.com/mgerstner/oscfs',
		classifiers = [
			'Intended Audience :: Developers',
			'License :: OSI Approved :: GPL-2',
			'Programming Language :: Python :: 2.7',
			'Topic :: System :: Filesystems'
		],
		scripts = [ 'bin/oscfs' ]
	)
finally:
	try:
		if remove_rst:
			os.remove(readme_rst)
	except:
		pass
