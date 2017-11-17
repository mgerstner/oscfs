from __future__ import with_statement, print_function

import os

our_uid = None
our_gid = None

def getUid():

	global our_uid

	if our_uid is None:
		our_uid = os.getuid()

	return our_uid

def getGid():

	global our_gid

	if our_gid is None:
		our_gid = os.getgid()

	return our_gid

