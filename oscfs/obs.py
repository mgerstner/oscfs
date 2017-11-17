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

	def getPackageFileList(self, project, package):
		"""Returns a list of the files belonging to a package. The
		list is comprised of tuples of the form (name, size,
		modtime)."""

		xml = osc.core.show_files_meta(
			self.m_apiurl,
			project,
			package,
			meta = False
		)

		ret = []

		tree = et.fromstring(xml)
		node = tree.find("directory")

		for entry in tree:

			if entry.tag != "entry":
				continue

			attrs = entry.attrib
			name = attrs["name"]
			size = int(attrs["size"])
			mtime = int(attrs["mtime"])
			ret.append( (name, size, mtime) )

		return ret

	def getFileContent(self, project, package, _file):

		# 'cat' is surprisingly difficult ... approach taken by the
		# 'osc cat' command line logic.

		query = {
			# follow source links
			"expand": 1
		}

		url = osc.core.makeurl(
			self.m_apiurl,
			['source', project, package, _file],
			query = query
		)

		f = osc.core.http_GET(url)

		return f.read()

