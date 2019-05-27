from __future__ import with_statement, print_function

import os, sys

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

def importUrllib():
	"""Imports the urllib2 module in a Python2/3 agnostic way."""

	try:
		import urllib2 as urllib_req
	except ModuleNotFoundError:
		import urllib.request as urllib_req

	return urllib_req

def importHttplib():
	"""Imports the httplib module in a Python2/3 agnostic way."""
	try:
		import httplib as http_client
	except ModuleNotFoundError:
		import http.client as http_client

	return http_client

def isPython2():
	"""Returns whether the current interpreter is of major version 2."""
	return sys.version_info.major == 2

def isPython3():
	"""Returns whether the current interpreter is of major version 2."""
	return sys.version_info.major == 3
