#!/usr/bin/env python2
# vim: ts=8 sw=8 sts=8 :

from __future__ import with_statement, print_function
import os, sys
import argparse
import subprocess
import signal
import tempfile
import time
import datetime

def eprint(*args, **kwargs):

	kwargs["file"] = sys.stderr
	print(*args, **kwargs)

class OscFsRegtest(object):
	"""This program performs a couple of regression tests against the
	openSUSE OBS instance which is publicly accessible."""

	def __init__(self):

		self.m_parser = argparse.ArgumentParser(
			description = "Regression tests for oscfs"
		)

		self.m_api_url = "https://api.opensuse.org"

		# subprocess object used by mount(), umount()
		self.m_oscfs_proc = None

		import osc.conf
		# determines the active oscrc configuration file
		self.m_oscrc_config = os.path.expanduser(
				osc.conf.identify_conf())

	def _lookupOscFsBin(self):

		dn = os.path.dirname

		oscfs_root_dir = dn(dn(os.path.realpath(__file__)))
		oscfs_bin = os.path.join(oscfs_root_dir, "bin", "oscfs")

		if not os.path.isfile(oscfs_bin):
			eprint("Failed to find oscfs executable at", oscfs_bin)
			sys.exit(1)

		self.m_oscfs_bin = oscfs_bin

	def _setupMountDir(self):

		self.m_mnt_dir = tempfile.mkdtemp(prefix = "oscfs-regtest-")

	def _cleanupMountDir(self):

		os.rmdir(self.m_mnt_dir)

	def _moveOscConfig(self):
		"""Renames all osc configuration files to allow writing new
		ones for testing."""

		back_config = self.m_oscrc_config + ".back"
		os.rename(self.m_oscrc_config, back_config)

	def _restoreOscConfig(self):
		"""Restores osc configuration files previously renamed by
		_moveOscConfig()."""
		back_config = self.m_oscrc_config + ".back"
		os.rename(back_config, self.m_oscrc_config)

	def mount(self, args = [], foreground = True, stderr_pipe = False):

		# first umount previous instance, if necessary
		self.umount()
		foreground = ["-f"] if foreground else []

		self.m_oscfs_proc = subprocess.Popen(
			[ self.m_oscfs_bin ] + foreground + args +\
				[ self.m_mnt_dir ],
			close_fds = True,
			shell = False,
			stdout = subprocess.PIPE,
			stderr = subprocess.PIPE if stderr_pipe else None
		)

		while foreground:
			line = self.m_oscfs_proc.stdout.readline()

			if not line:
				raise Exception("Mounting file system failed")
			elif line.strip() == "file system initialized":
				break

		# TODO: should we close the pipe from here? This could cause
		# exceptions in the subprocess upon writing. Keeping it open
		# could cause a blocking child process when the pipe is full
		# ...

	def umount(self):

		if not self.m_oscfs_proc:
			return

		rc = self.m_oscfs_proc.poll()

		if rc is None:
			self.m_oscfs_proc.terminate()
			rc = self.m_oscfs_proc.wait()
			if rc == - signal.SIGTERM:
				rc = 0

		self.m_oscfs_proc = None

		if rc != 0:
			raise Exception("oscfs exited with non-zero exit state of {}".format(rc))

	def performMountTests(self):
		"""This test checks whether basic mounting works and whether
		influencing parameters work as expected."""

		def checkTopDirs(homes, maintenance):

			print("Testing mount with homes = {} and maintenance = {}".format(homes, maintenance))

			top_dirs = os.listdir(self.m_mnt_dir)
			if len(top_dirs) == 0:
				raise Exception("mounted file system is empty")

			home_users = set()
			maint_dirs = set()
			for d in top_dirs:
				if d.startswith("home:"):
					home_users.add( d.split(':')[1] )

					if not homes and len(home_users) > 1:
						raise Exception("mounted without --homes but found more than one user's home project")

				if d.startswith("openSUSE:Maintenance"):
					maint_dirs.add(d)

					if not maintenance:
						raise Exception("mounted without --maintenance but found maintenance project")

			# only our own home projects should there
			if homes and len(home_users) <= 1:
				raise Exception("mounted with --homes but found <= 1 home projects")

			if maintenance and len(maint_dirs) == 0:
				raise Exception("mounted with --maintenance but foudn no maintenance projects")

		# NOTE: testing the --ptf parameter is difficult, because on
		# OBS there are not PTFs.
		self.mount()
		checkTopDirs(False, False)

		self.mount(["--homes"])
		checkTopDirs(True, False)

		self.mount(["--maintenance"])
		checkTopDirs(False, True)

		self.mount(["--homes", "--maintenance"])
		checkTopDirs(True, True)

	def performCacheTests(self):
		"""This test checks whether a cache effect can be observed
		when listing a large package the first time and a subsequent
		time. Also the refresh node is checked for its effect."""

		self.mount()
		test_package = os.path.join(self.m_mnt_dir, "openSUSE:Factory", "zlib")

		def doWalk(label, cmp_fnc):
			print("Testing", label, "... ", end = '')
			sys.stdout.flush()
			start = datetime.datetime.now()
			for root, dirs, files in os.walk( test_package ):
				pass
			end = datetime.datetime.now()
			diff = end - start
			print("took", diff, "({} seconds)".format(int(diff.total_seconds())))

			if cmp_fnc(diff.total_seconds()):
				raise Exception("Access Time for {} is not within the expected time frame".format(label))

		doWalk("uncached package access", lambda d: d < 1.0)
		doWalk("cached package access", lambda d: d > 1.0)

		refresh_ctrl = os.path.join(test_package, ".oscfs", "refresh")
		with open(refresh_ctrl, 'w') as ctrl_fd:
			ctrl_fd.write('1')

		doWalk("refreshed uncached package access", lambda d: d < 1.0)

	def performAuthErrorTest(self):
		"""The purpose of this test is to see whether bad
		authentication at the remote server immediately leads to an
		error, even without '-f'."""

		self._moveOscConfig()

		min_config = """
[general]
apirul = {url}

[{url}]
user={user}
pass={_pass}
"""

		with open(self.m_oscrc_config, 'w') as oscrc:
			print(min_config.format(
					url = self.m_api_url,
					user = "somebody",
					_pass = "somepass"
				), file = oscrc
			)

		# this is actually more complex, osc chokes on various other
		# conditions like config file not being there, config for
		# apiurl missing etc.
		#
		# we need to setup a minimum configuration file without
		# password

		try:
			print("Testing for early authentication error")
			# temporarily remove any osc authentication
			self.mount(foreground = False, stderr_pipe = True)

			found_auth_error = False

			while True:
				line = self.m_oscfs_proc.stderr.readline()

				if not line:
					break
				elif line.lower().find("authorization at the remote server failed") != -1:
					found_auth_error = True

			res = self.m_oscfs_proc.wait()
			self.m_oscfs_proc = None

			if res != 1 or not found_auth_error:
				raise Exception("No authentication error code or message was reported: code = {}".format(res))
		finally:
			self._restoreOscConfig()

	def performTests(self):

		self.performMountTests()
		self.performAuthErrorTest()
		self.performCacheTests()

	def run(self):

		# NOTE: currently no arguments are used
		self.m_args = self.m_parser.parse_args()
		self._lookupOscFsBin()
		self._setupMountDir()
		print("Using", self.m_mnt_dir, "for mounting oscfs")

		try:
			self.performTests()
		finally:
			self.umount()
			self._cleanupMountDir()

osc_fs_regtest = OscFsRegtest()
try:
	osc_fs_regtest.run()
except Exception as e:
	eprint("Error:", e)
	sys.exit(1)

