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

def fixSigInt():
	"""The fuse-python module has got some trouble with correctly handling
	CTRL-C (KeyboardInterrupt), because python takes control of it but the
	libfuse needs to install its own handler for gracefully exiting.

	This function reinstates the default signal handler such that libfuse
	will install its own signal handler."""
	import signal
	signal.signal(signal.SIGINT, signal.SIG_DFL)

