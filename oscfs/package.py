# vim: ts=8 sw=8 sts=8 :

# standard modules
from __future__ import with_statement, print_function

# local modules
import oscfs.types
import oscfs.obs
import oscfs.file
import oscfs.link

class Package(oscfs.types.DirNode):
	"""This type represents a package node of the file system containing
	all package files and metadata as files.
	"""

	def __init__(self, parent, name):

		super(Package, self).__init__(name = name)
		self.m_parent = parent

	def getObs(self):

		return self.m_parent.getObs()

	def getProject(self):

		return self.m_parent.getName()

	def _addApiDir(self):

		api_name = ".oscfs"
		self.m_entries[api_name] = ApiDir(self, api_name)

	def update(self):

		if not self.isCacheStale():
			return

		self.clearEntries()

		obs = self.m_parent.getObs()

		types = oscfs.types.FileType

		for ft, name, size, mtime, target in obs.getPackageFileList(
			self.getProject(), self.getName()
		):
			if ft == types.regular:
				node = oscfs.file.File(self, name, size, mtime)
			elif ft == types.symlink:
				node = oscfs.link.Link(self, name, target)
			else:
				raise Exception("Unexpected type")
			self.m_entries[name] = node

		self._addApiDir()

		self.setCacheFresh()

class LogNode(oscfs.types.Node):
	"""This node type contains the commit log for the package it resides in."""

	def __init__(self, parent, package, name):

		super(LogNode, self).__init__(name = name)
		self.m_parent = parent
		self.m_package = package

		self.m_log = self.fetchLog()
		self.getStat().setSize(len(self.m_log))

	def fetchLog(self):

		package = self.m_package
		obs = package.getObs()

		log = obs.getCommitLog(package.getProject(), package.getName())

		return log

	def read(self, length, offset):

		return self.m_log[offset:length]

class NumRevisionsNode(oscfs.types.Node):
	"""This node type contains the number of commits for the package it
	resides in."""

	def __init__(self, parent, package, name):

		super(NumRevisionsNode, self).__init__(name = name)
		self.m_parent = parent
		self.m_package = package

		self.m_revisions = self.fetchRevisions()
		self.getStat().setSize(len(self.m_revisions))

	def fetchRevisions(self):

		package = self.m_package
		obs = package.getObs()

		infos = obs.getCommitInfos(
			package.getProject(), package.getName()
		)

		return str(len(infos))

	def read(self, length, offset):

		return self.m_revisions[offset:length]

class ApiDir(oscfs.types.DirNode):
	"""This type provides access to additional meta data for a package.
	This is just the root directory for this which adds individual file
	and directory nodes that represent actual API features."""

	def __init__(self, parent, name):

		super(ApiDir, self).__init__(name = name)
		self.m_parent = parent

	def update(self):
		if not self.isCacheStale():
			return

		self.clearEntries()

		log_name = "log"
		self.m_entries[log_name] = LogNode(self, self.m_parent, log_name)
		num_revs_name = "num_revisions"
		self.m_entries[num_revs_name] = NumRevisionsNode(
			self, self.m_parent, num_revs_name
		)

