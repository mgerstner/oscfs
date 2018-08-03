# vim: ts=8 sw=8 sts=8 :

# standard modules
from __future__ import with_statement, print_function

# local modules
import oscfs.types
import oscfs.obs
import oscfs.obsfile
import oscfs.link
import oscfs.refreshtrigger

class Package(oscfs.types.DirNode):
	"""This type represents a package node of the file system containing
	all package files and metadata as files.
	"""

	def __init__(self, parent, name, project, package, revision = None):

		super(Package, self).__init__(parent, name)
		self.m_revision = revision
		self.m_project = project
		self.m_package = package
		self.m_api_name = ".oscfs"
		# we have special update logic and only want to clear
		# explicitly
		self._setAutoClearOnUpdate(False)

	def getRevision(self):

		return self.m_revision

	def getCommitInfos(self):
		obs = self.getRoot().getObs()
		return obs.getCommitInfos(
			self.getProject().getName(),
			self.getName()
		)

	def _addApiDir(self):

		api_name = self.m_api_name
		self.m_entries[api_name] = PkgApiDir(self, api_name)

	def getApiDir(self):
		return self.m_entries[self.m_api_name]

	def _existsNewRevision(self):

		if not self.wasEverUpdated():
			return True

		api_dir = self.m_entries[self.m_api_name]

		infos = self.getCommitInfos()
		if len(infos) == len(api_dir.getCachedCommitInfos()):
			# nothing new was commited
			return True

		return False

	def _addPackageFiles(self):

		obs = self.getRoot().getObs()

		types = oscfs.types.FileType

		for ft, name, size, mtime, target in obs.getPackageFileList(
			self.getProject().getName(), self.m_package,
			revision = self.m_revision
		):
			if ft == types.regular:
				node = oscfs.obsfile.ObsFile(
					self, name, size, mtime,
					revision = self.m_revision
				)
			elif ft == types.symlink:
				node = oscfs.link.Link(self, name, target)
			else:
				raise Exception("Unexpected type")

			self.m_entries[name] = node

	def isCacheStale(self):

		if not super(Package, self).isCacheStale():
			return False

		if not self.wasEverUpdated():
			return True

		# if we are fixed to a certain revision then there is no need
		# to update anything
		return self.m_revision is None

	def update(self):
		if self._existsNewRevision():
			self.clearEntries()
			self._addPackageFiles()

		if not self.m_revision:
			# only add the API dir for the current version of the
			# package, the pkg meta data is not versioned.
			self._addApiDir()

class PkgApiDir(oscfs.types.DirNode):
	"""This type provides access to additional meta data for a package.
	This is just the root directory for this which adds individual file
	and directory nodes that represent actual API features."""

	def __init__(self, parent, name):

		super(PkgApiDir, self).__init__(parent, name)
		self.m_meta_name = "meta"
		self.m_log_name = "log"
		self.m_desc_name = "description"
		self.m_maintainers_name = "maintainers"
		self.m_bugowners_name = "bugowners"
		self.m_num_revs_name = "num_revisions"
		self.m_commits_dir_name = "commits"
		self.m_rev_dir_name = "revisions"
		self.m_req_dir_name = "requests"
		self.m_refresh_trigger = "refresh"
		self.m_buildlogs_name = "buildlogs"
		self.m_buildresults_name = "buildresults"
		self.m_binaries_dir_name = "binaries"
		self.m_commit_infos = None
		self.m_pkg_meta = None

	def getCachedCommitInfos(self):
		# centrally keep the commit infos for the package here to
		# avoid multiple queries for the same data in child nodes

		if not self.m_commit_infos:
			self.m_commit_infos = self.m_parent.getCommitInfos()

		return self.m_commit_infos

	def getPkgMeta(self):

		if not self.m_pkg_meta:
			obs = self.getRoot().getObs()
			self.m_pkg_meta = obs.getPackageMeta(
				self.getProject().getName(),
				self.getPackage().getName()
			)

		return self.m_pkg_meta

	def getPkgInfo(self):

		return oscfs.obs.PackageInfo(self.getPkgMeta())

	def getNumRevsNode(self):

		return self.m_entries[self.m_num_revs_name]

	def update(self):
		self.m_commit_infos = None
		self.m_pkg_meta = None

		for name, _type in (
			(self.m_log_name, LogNode),
			(self.m_num_revs_name, NumRevisionsNode),
			(self.m_commits_dir_name, CommitsDir),
			(self.m_rev_dir_name, RevisionsDir),
			(self.m_req_dir_name, RequestsDir),
			(self.m_meta_name, MetaNode),
			(self.m_desc_name, DescriptionNode),
			(self.m_maintainers_name, MaintainersNode),
			(self.m_bugowners_name, BugownersNode),
			(self.m_refresh_trigger,
				oscfs.refreshtrigger.RefreshTrigger),
			(self.m_buildlogs_name, BuildlogsDir),
			(self.m_buildresults_name, BuildresultsNode),
			(self.m_binaries_dir_name, BinariesDir)
		):
			try:
				node = _type(self, self.m_parent, name)
				self.m_entries[name] = node
			except Exception as e:
				print("Failed to add", name, "entry:", e)

		devel_proj = self.getPkgInfo().getDevelProject()
		if devel_proj:
			devel_link = "develproject"
			target = "{}/{}".format(
					devel_proj,
					self.getPackage().getName()
			)
			self.m_entries[devel_link] = \
				oscfs.link.Link(self, devel_link, target)

		prj_info = self.getProject().getApiDir().getPrjInfo()
		incident = self.getPkgInfo().getMaintenanceIncident(prj_info)

		if incident:
			# add a symlink to the maintenance indicent where this
			# package was built
			incident_link = "incident"
			target = incident
			self.m_entries[incident_link] = \
				oscfs.link.Link(self, incident_link, target)

class CommitsDir(oscfs.types.DirNode):
	"""This types provides access to each individual commit for a
	package. Each commit is represented as an individual file."""

	def __init__(self, parent, package, name):

		super(CommitsDir, self).__init__(parent, name)
		self.m_package = package

	def update(self):
		package = self.m_package
		infos = self.m_parent.getCachedCommitInfos()

		for rev in range(len(infos)):
			info = infos[rev]

			commit = "{}".format(rev+1)
			self.m_entries[commit] = CommitNode(self, info, commit)

class RevisionsDir(oscfs.types.DirNode):
	"""This type provides access to all revisions that exist for a
	package. It allows to inspect individual revisions directly and to
	diff files directly."""

	def __init__(self, parent, package, name):

		super(RevisionsDir, self).__init__(parent, name)
		self.m_package = package

	def update(self):
		package = self.m_package

		for info in self.m_parent.getCachedCommitInfos():
			name = str(info.getRevision())
			self.m_entries[name] = Package(
				self, name,
				project = self.getProject().getName(),
				package = self.getPackage().getName(),
				revision = info.getRevision()
			)

class LogNode(oscfs.types.FileNode):
	"""This node type contains the commit log for the package it resides
	in."""

	def __init__(self, parent, package, name):

		super(LogNode, self).__init__(parent, name)
		self.m_package = package

	def fetchContent(self):
		log = self.fetchLog()
		self.setContent(log)

	def fetchLog(self):

		obs = self.getRoot().getObs()

		log = obs.getCommitLog(
			self.getProject().getName(),
			self.getPackage().getName()
		)

		return log

class NumRevisionsNode(oscfs.types.FileNode):
	"""This node type contains the number of commits for the package it
	resides in."""

	def __init__(self, parent, package, name):

		super(NumRevisionsNode, self).__init__(parent, name)
		self.m_package = package
		self.m_revisions = None

	def fetchContent(self):
		self.m_revisions = self.fetchRevisions()
		self.setContent(self.m_revisions)

	def fetchRevisions(self):

		package = self.m_package
		infos = self.m_parent.getCachedCommitInfos()

		return str(len(infos))

	def getNumRevs(self):

		if self.m_revisions is None:
			self.fetchContent()

		return int(self.m_revisions)


class CommitNode(oscfs.types.FileNode):
	"""This node contains the specific commit info for a revision."""

	def __init__(self, parent, info, name):

		super(CommitNode, self).__init__(parent, name)
		self.m_info = info

		commit = self.buildCommit()
		self.setContent(commit, self.m_info.getDate())

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

class RequestNode(oscfs.types.FileNode):
	"""This node contains the specific request info for a request."""

	def __init__(self, parent, req, name):

		super(RequestNode, self).__init__(parent, name)
		self.m_req = req
		try:
			text = unicode(req).encode('utf8')
		except UnicodeEncodeError:
			text = "<unicode-error>"
		self.setContent(text, self.getReqModTime())

	def getReqModTime(self):

		# set the modification time to the time of the last request
		# modification
		last_change = self.m_req.statehistory[-1].when
		import datetime
		dt = datetime.datetime.strptime(
			last_change,
			"%Y-%m-%dT%H:%M:%S"
		)
		return dt

class RequestsDir(oscfs.types.DirNode):
	"""This type provides access to all requests that exist for a
	package. It allows to inspect individual requests directly."""

	def __init__(self, parent, package, name):

		super(RequestsDir, self).__init__(parent, name)
		self.m_package = package

	def update(self):
		obs = self.getRoot().getObs()

		for req in obs.getPackageRequestList(
				project = self.getProject().getName(),
				package = self.getPackage().getName()
		):
			label = "{}:{}".format(req.reqid, req.state.name)
			self.m_entries[label] = RequestNode(self, req, label)

class MetaNode(oscfs.types.FileNode):
	"""This node type contains the raw XML metadata of a package."""

	def __init__(self, parent, package, name):

		super(MetaNode, self).__init__(parent, name)
		self.m_package = package

	def fetchContent(self):
		meta = self.m_parent.getPkgMeta()
		self.setContent(meta)

class DescriptionNode(oscfs.types.FileNode):
	"""This node returns a formatted description of the package."""

	def __init__(self, parent, package, name):

		super(DescriptionNode, self).__init__(parent, name)
		self.m_package = package

	def fetchContent(self):
		pkg_info = self.m_parent.getPkgInfo()

		import textwrap

		# Note: some packages don't have a title/description value
		title = pkg_info.getTitle()
		if not title:
			title = self.m_package.getPackage()
		desc = pkg_info.getDesc()
		if not desc:
			desc = "no description available"

		desc = "# {}\n\n{}".format(
			title,
			'\n'.join(textwrap.wrap(desc))
		)
		self.setContent(desc)

class MaintainersNode(oscfs.types.FileNode):
	"""This node returns a list of maintainers for the package."""

	def __init__(self, parent, package, name):

		super(MaintainersNode, self).__init__(parent, name)
		self.m_package = package

	def fetchContent(self):
		pkg_info = self.m_parent.getPkgInfo()
		maintainers = '\n'.join(pkg_info.getMaintainers())
		self.setContent(maintainers)

class BugownersNode(oscfs.types.FileNode):
	"""This node returns a list of bugownders for the package."""

	def __init__(self, parent, package, name):

		super(BugownersNode, self).__init__(parent, name)
		self.m_package = package

	def fetchContent(self):
		pkg_info = self.m_parent.getPkgInfo()
		bugowners = '\n'.join(pkg_info.getBugowners())
		self.setContent(bugowners)

class BuildresultsNode(oscfs.types.FileNode):
	"""This node returns a the current build results for configured
	repositories."""

	def __init__(self, parent, package, name):

		super(BuildresultsNode, self).__init__(parent, name)
		self.m_package = package
		# always fetch fresh build results without caching
		self.setUseCache(False)

	def fetchContent(self):
		obs = self.getRoot().getObs()
		results = obs.getBuildResults(
			self.getProject().getName(),
			self.getPackage().getName()
		)

		content = results.getTable()
		self.setContent(content)

class BuildlogNode(oscfs.types.FileNode):
	"""This type returns a certain build log for a certain package upon
	read."""

	def __init__(self, parent, project, package, repo, arch):

		super(BuildlogNode, self).__init__(parent, arch)
		self.m_project = project
		self.m_package = package
		self.m_repo = repo
		self.m_arch = arch
		self.m_last_checksum = ""
		self.setUseCache(False)

	def fetchContent(self):
		obs = self.getRoot().getObs()

		args = (self.m_project, self.m_package, self.m_repo,
				self.m_arch)

		results = obs.getBuildResults(*args)
		if results.getNumResults() == 1:
			pkg, code = results.getResults()[0].getPackages()[0]
			if code in ('disabled', 'excluded', 'scheduled'):
				self.setContent("Build is {}, currently no log".format(code))
				return
			if results.getChecksum() == self.m_last_checksum:
				# keep the currently cached content, nothing
				# changed
				return

			self.m_last_checksum = results.getChecksum()
		else:
			# can't determine state, what to do?
			# simply try fetching the log ...
			pass

		log = obs.getBuildlog(*args)
		self.setContent(log)

class BuildlogsDir(oscfs.types.DirNode):
	"""This type provides access to a repository/arch hierarchy that
	allows access to the current build logs of a package."""

	def __init__(self, parent, package, name):

		super(BuildlogsDir, self).__init__(parent, name)
		self.m_package = package

	def update(self):
		pkg_info = self.getPackage().getApiDir().getPkgInfo()
		prj_info = self.getProject().getApiDir().getPrjInfo()

		active = pkg_info.getAllActiveRepos(prj_info)

		for repo, arch in active:
			repodir = self.m_entries.setdefault(
				repo,
				oscfs.types.PlainDirNode(self, repo)
			)

			repodir.m_entries[arch] = BuildlogNode(
				repodir,
				prj_info.getName(),
				pkg_info.getName(),
				repo,
				arch
			)

class BinaryFileNode(oscfs.types.FileNode):
	"""This type returns a certain binary artifact's data upon read."""

	def __init__(self, parent, project, package, repo, arch, binary):

		super(BinaryFileNode, self).__init__(parent, binary[0])
		self.m_project = project
		self.m_package = package
		self.m_repo = repo
		self.m_arch = arch
		self.m_binary = binary
		self._setMeta()

	def _setMeta(self):

		stat = self.getStat()
		stat.setModTime(self.m_binary[1])
		stat.setSize(self.m_binary[2])

	def fetchContent(self):
		obs = self.getRoot().getObs()

		args = (self.m_project, self.m_package, self.m_repo,
				self.m_arch, self.getName())

		# NOTE: this could become difficult to cache big binary files
		# this way, need to handle it in chunks probably without
		# caching.
		content = obs.getBinaryFileContent(*args)
		self.setContent(content)

class BinariesDir(oscfs.types.DirNode):
	"""This type provides access to a repository/arch hierarchy that
	allows access to the current build artifacts of a package."""

	def __init__(self, parent, package, name):

		super(BinariesDir, self).__init__(parent, name)
		self.m_package = package

	def update(self):
		obs = self.getRoot().getObs()
		pkg_info = self.getPackage().getApiDir().getPkgInfo()
		prj_info = self.getProject().getApiDir().getPrjInfo()

		active = pkg_info.getAllActiveRepos(prj_info)

		for repo, arch in active:
			binaries = obs.getBinaryList(
				prj_info.getName(),
				self.m_package.getName(),
				repo,
				arch
			)

			if not binaries:
				continue

			repodir = self.m_entries.setdefault(
				repo,
				oscfs.types.PlainDirNode(self, repo)
			)

			archdir = repodir.m_entries.setdefault(
				arch,
				oscfs.types.PlainDirNode(self, arch)
			)

			for binary in binaries:

				name = binary[0]
				archdir.m_entries[name] = BinaryFileNode(
					repodir,
					prj_info.getName(),
					pkg_info.getName(),
					repo,
					arch,
					binary
				)

