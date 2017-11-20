# vim: ts=8 sw=8 sts=8 :

from __future__ import with_statement, print_function

# standard modules
import os
import sys
import errno
import argparse

# third party modules
import fuse

# local modules
import oscfs.root
import oscfs.obs

class OscFs(fuse.LoggingMixIn, fuse.Operations):
	"""The main class implementing the fuse operations and python-fuse
	setup."""

	def __init__(self):

		self.m_default_url = "https://api.opensuse.org"
		self.m_obs = oscfs.obs.Obs()
		# stores file handle -> node mappings
		# (file handles need to be integers)
		self.m_handles = [None] * 1024
		self._setupParser()

	def _setupParser(self):

		self.m_parser = argparse.ArgumentParser(
			description = "SUSE open build service file system"
		)

		self.m_parser.add_argument(
			"-f", action = 'store_true',
			help = "Run the file system in the foreground"
		)
		self.m_parser.add_argument(
			"--apiurl", type = str, default = self.m_default_url,
			help = "The API URL of the OBS instance. OpenSUSE build service is used by default"
		)
		self.m_parser.add_argument(
			"--homes", action = 'store_true',
			help = "If set then home projects will be included which is not the default"
		)
		self.m_parser.add_argument(
			"--maintenance", action = 'store_true',
			help = "If set then maintenance projects will be included which is not the default"
		)
		self.m_parser.add_argument(
			"mountpoint", type = str,
			help = "Path where to mount the file system"
		)

		self.m_parser.add_argument(
			"--cache-time", type = int,
			default = None,
			help = """Specifies the time in seconds the contents
				of the file system will be cached. Default: {}
				seconds. Set to zero to disable caching.""".format(
					oscfs.types.Node.max_cache_time.seconds
			)
		)

	def _getNode(self, path, fh = None):

		if fh != None:
			return self._getFileHandle(fh)
		else:
			try:
				return self.m_root.getNode(path)
			except KeyError:
				raise fuse.FuseOSError(errno.ENOENT)

	def run(self):

		self.m_args = self.m_parser.parse_args()
		self.m_obs.configure(self.m_args.apiurl)
		self.m_root = oscfs.root.Root(self.m_obs, self.m_args)
		if self.m_args.cache_time != None:
			oscfs.types.Node.setMaxCacheTime(self.m_args.cache_time)

		fuse.FUSE(
			self,
			self.m_args.mountpoint,
			foreground = self.m_args.f,
			nothreads = True
		)

	# global file system methods

	def getattr(self, path, fh = None):

		node = self._getNode(path, fh)

		ret = node.getStat()

		return ret.toDict()

	def readdir(self, path, fh = None):

		node = self._getNode(path, fh)

		ret = node.getNames()

		return ret

	def readlink(self, path):
		node = self._getNode(path)
		return node.readlink()

	# per file handle methods

	def _allocFileHandle(self, node):

		for i in range(len(self.m_handles)):

			if self.m_handles[i] == None:
				self.m_handles[i] = node
				return i

		raise fuse.FuseOSError(errno.EMFILE)

	def _freeFileHandle(self, fh):

		self.m_handles[fh] = None

	def _getFileHandle(self, fh):

		return self.m_handles[fh]

	def opendir(self, path):

		node = self._getNode(path)
		return self._allocFileHandle(node)

	def release(self, path, fh):

		if fh != None:
			self._freeFileHandle(fh)

	def releasedir(self, path, fh):

		if fh != None:
			self._freeFileHandle(fh)

	def open(self, path, flags):

		# deny writing
		for badflag in (os.O_RDWR, os.O_WRONLY, os.O_CREAT):
			if (flags & badflag) != 0:
				raise fuse.FuseOSError(errno.EPERM)

		node = self._getNode(path)
		return self._allocFileHandle(node)

	def read(self, path, length, offset, fh):

		node = self._getNode(path, fh)

		return node.read(length, offset)

