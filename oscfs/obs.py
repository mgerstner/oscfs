# vim: ts=8 sw=8 sts=8 :

# standard modules
from __future__ import with_statement, print_function
from xml.etree import cElementTree as et

# third party modules
import osc.core

class Obs(object):
	"""Wrapper around the osc python module for the purposes of this file
	system."""

	def __init__(self):
		pass

	def configure(self, apiurl):

		import osc.conf
		self.m_apiurl = apiurl
		osc.conf.get_config()
		osc.conf.config["apiurl"] = apiurl

	def getUser(self):
		return osc.conf.config["user"]

	def getProjectList(self):
		"""Returns a list of the top-level projects of the current OBS
		instance. It's a list of plain strings."""

		ret = osc.core.meta_get_project_list(self.m_apiurl)

		return ret

	def getPackageList(self, project):
		"""Returns a list of all the packages withing a top-level
		project. It's a list of plain strings."""

		ret = osc.core.meta_get_packagelist(self.m_apiurl, project)

		return ret

	def _getPackageFileTree(self, project, package):
		xml = osc.core.show_files_meta(
			self.m_apiurl,
			project,
			package,
			meta = False
		)

		tree = et.fromstring(xml)
		return tree

	def getPackageFileList(self, project, package):
		"""Returns a list of the files belonging to a package. The
		list is comprised of tuples of the form (name, size,
		modtime)."""

		tree = self._getPackageFileTree(project, package)
		ret = []

		# if this is a linked package then we find two nodes
		# "linkinfo" and a "_link" file entry. For getting information
		# about the link we need to query the linkinfo first
		#
		# sadly there seems to be no way to query a package's link
		# property without individually listing it which is a
		# performance issue.
		#
		# therefore we only make the _link a symlink, not the package
		# itself
		li_node = tree.find("linkinfo")
		# xml node seems to have a strange boolean behaviour...
		if li_node is None:
			link_target = None
		else:
			linkinfo = osc.core.Linkinfo()
			linkinfo.read(li_node)
			link_target = "../../{}/{}".format(
				linkinfo.project,
				linkinfo.package
			)

		from oscfs.types import FileType

		for entry in tree:

			if entry.tag != "entry":
				continue

			attrs = entry.attrib
			name = attrs["name"]
			is_link = name == "_link" and link_target
			ft = FileType.symlink if is_link else FileType.regular
			size = int(attrs["size"])
			mtime = int(attrs["mtime"])
			link = link_target if is_link else None
			ret.append( (ft, name, size, mtime, link) )

		return ret

	def getFileContent(self, project, package, _file):

		# 'cat' is surprisingly difficult ... approach taken by the
		# 'osc cat' command line logic.

		query = {
			# don't follow source links
			"expand": 0
		}

		url = osc.core.makeurl(
			self.m_apiurl,
			['source', project, package, _file],
			query = query
		)

		f = osc.core.http_GET(url)

		return f.read()

	def _getPackageRevisions(self, project, package, fmt):
		"""Returns the list of revisions for the given project/package
		path in the given fmt. @fmt can be any of ('text, 'csv',
		'xml'). Each revision will come with date and commit text."""

		return osc.core.get_commitlog(
			self.m_apiurl,
			project,
			package,
			None,
			format = fmt
		)

	def getCommitLog(self, project, package):
		"""Returns a string containing the commit log of the given
		package in human readable form."""
		return '\n'.join(
			self._getPackageRevisions(project, package, "text")
		)


