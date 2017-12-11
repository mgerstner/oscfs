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

	def __init__(self, parent, name, project, package, revision = None):

		super(Package, self).__init__(parent, name)
		self.m_revision = revision
		self.m_project = project
		self.m_package = package

	def getObs(self):

		return self.m_parent.getObs()

	def getProject(self):

		return self.m_project

	def getPackage(self):

		return self.m_package

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
			self.getProject(), self.getPackage(),
			revision = self.m_revision
		):
			if ft == types.regular:
				node = oscfs.file.File(
					self, name, size, mtime,
					revision = self.m_revision
				)
			elif ft == types.symlink:
				node = oscfs.link.Link(self, name, target)
			else:
				raise Exception("Unexpected type")
			self.m_entries[name] = node

		if not self.m_revision:
			# only add the API dir for the current version of the
			# package, the pkg meta data is not versioned.
			self._addApiDir()

		self.setCacheFresh()

class LogNode(oscfs.types.Node):
	"""This node type contains the commit log for the package it resides
	in."""

	def __init__(self, parent, package, name):

		super(LogNode, self).__init__(parent, name)
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

		super(NumRevisionsNode, self).__init__(parent, name)
		self.m_package = package

		self.m_revisions = self.fetchRevisions()
		self.getStat().setSize(len(self.m_revisions))

	def fetchRevisions(self):

		package = self.m_package
		infos = self.m_parent.getCommitInfos()

		return str(len(infos))

	def read(self, length, offset):

		return self.m_revisions[offset:length]

	def getNumRevs(self):

		return int(self.m_revisions)

class ApiDir(oscfs.types.DirNode):
	"""This type provides access to additional meta data for a package.
	This is just the root directory for this which adds individual file
	and directory nodes that represent actual API features."""

	def __init__(self, parent, name):

		super(ApiDir, self).__init__(parent, name)
		self.m_log_name = "log"
		self.m_num_revs_name = "num_revisions"
		self.m_commits_dir_name = "commits"
		self.m_rev_dir_name = "revisions"
		self.m_commit_infos = None

	def getCommitInfos(self):
		# centrally keep the commit infos for the package here to
		# avoid multiple queries for the same data in child nodes

		if not self.m_commit_infos:
			obs = self.m_parent.getObs()
			self.m_commit_infos = obs.getCommitInfos(
				self.m_parent.getProject(),
				self.m_parent.getName()
			)

		return self.m_commit_infos

	def getNumRevsNode(self):

		return self.m_entries[self.m_num_revs_name]

	def update(self):
		if not self.isCacheStale():
			return

		self.m_commit_infos = None
		self.clearEntries()

		for name, _type in (
			(self.m_log_name, LogNode),
			(self.m_num_revs_name, NumRevisionsNode),
			(self.m_commits_dir_name, CommitsDir),
			(self.m_rev_dir_name, RevisionsDir)
		):
			node = _type(self, self.m_parent, name)
			self.m_entries[name] = node

		self.setCacheFresh()

class CommitNode(oscfs.types.Node):
	"""This node contains the specific commit info for a revision."""

	def __init__(self, parent, info, name):

		super(CommitNode, self).__init__(parent, name)
		self.m_info = info
		self.m_commit = self.buildCommit()
		stat = self.getStat()
		stat.setSize(len(self.m_commit))
		stat.setModTime(self.m_info.getDate())

	def buildCommit(self):

		ret = "revision {r} | {user} | {date} | {req}\n".format(
			r = self.m_info.getRevision(),
			user = self.m_info.getAuthor(),
			date = self.m_info.getDate().strftime("%X %x"),
			req = self.m_info.getReqId()
		)

		ret += "-" * (len(ret) - 1)
		ret += "\n"
		ret += self.m_info.getMessage()
		return ret

	def read(self, length, offset):
		return self.m_commit[offset:length]

class CommitsDir(oscfs.types.DirNode):
	"""This types provides access to each individual commit for a
	package. Each commit is represented as an individual file."""

	def __init__(self, parent, package, name):

		super(CommitsDir, self).__init__(parent, name)
		self.m_package = package

	def update(self):
		if not self.isCacheStale():
			return

		self.clearEntries()

		package = self.m_package
		infos = self.m_parent.getCommitInfos()

		for rev in range(len(infos)):
			info = infos[rev]

			commit = "{}".format(rev+1)
			self.m_entries[commit] = CommitNode(self, info, commit)

		self.setCacheFresh()

class RevisionsDir(oscfs.types.DirNode):
	"""This type provides access to all revisions that exist for a
	package. It allows to inspect individual revisions directly and to
	diff files directly."""

	def __init__(self, parent, package, name):

		super(RevisionsDir, self).__init__(parent, name)
		self.m_package = package

	def getObs(self):

		return self.m_parent.m_parent.getObs()

	def update(self):
		if not self.isCacheStale():
			return

		self.clearEntries()

		package = self.m_package

		for info in self.m_parent.getCommitInfos():
			name = str(info.getRevision())
			self.m_entries[name] = Package(
				self, name,
				project = self.m_parent.m_parent.getProject(),
				package = self.m_package.getPackage(),
				revision = info.getRevision()
			)

		self.setCacheFresh()

