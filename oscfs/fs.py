# vim: ts=8 sw=8 sts=8 :

from __future__ import with_statement, print_function

import os
import sys
import errno

import fuse

import oscfs.root

class OscFs(fuse.Fuse):
	"""The main class implementing the fuse operations and python-fuse
	setup."""

	def __init__(self):

		self.m_default_url = "https://api.opensuse.org"
		self.url = self.m_default_url

		super(OscFs, self).__init__(
			version = "%prog 0.1",
			usage = "SUSE open build service file system",
			# this is about the handling of the '-s' option for
			# requiring single threaded operation. we don't
			# support multi-threading at the moment so we don't
			# care if the option's there or not
			dash_s_do = 'setsingle'
		)

		self.parser.add_option(
			mountopt = "url",
			metavar = "API_URL",
			default = self.m_default_url,
			help = "Access the OBS instance located at the given URL",
		)

		# disable multithreading by default
		self.multithreaded = False

	def main(self, *args, **kwargs):

		self.parse(values=self, errex=1)
		fuse.Fuse.main(self, *args, **kwargs)

	def _configureOsc(self):

		import osc.conf
		osc.conf.get_config()
		osc.conf.config["apiurl"] = self.url

	# global file system methods

	def fsinit(self):

		try:
			self._configureOsc()
			self.m_root = oscfs.root.Root()
		except Exception as e:
			print("Failed to configure osc:", e)
			sys._exit(1)

	def getattr(self, path):
		try:
			ret = self.m_root.getStat()
		except Exception as e:
			print(e)
		return ret

	def readdir(self, path, fh):
		full_path = self._full_path(path)

		dirents = ['.', '..']
		if os.path.isdir(full_path):
			dirents.extend(os.listdir(full_path))
		for r in dirents:
			yield fuse.Direntry(r)

	def readlink(self, path):
		pathname = os.readlink(self._full_path(path))
		if pathname.startswith("/"):
			# Path name is absolute, sanitize it.
			return os.path.relpath(pathname, self.root)
		else:
			return pathname

	# File methods
	# ============

	def open(self, path, flags):
		print(path)

		fd = os.open(full_path, flags)

		return OpenContext(fd)

	def read(self, path, length, offset, filehandle):

		fd = filehandle.m_fd
		os.lseek(fd, offset, os.SEEK_SET)

		return os.read(fd, length)

def getInstance():

	ret = OscFs()

	return ret


