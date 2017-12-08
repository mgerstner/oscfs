# vim: ts=8 sw=8 sts=8 :

# standard modules
from __future__ import with_statement, print_function

# local modules
import oscfs.types
import oscfs.obs
import oscfs.package

class Project(oscfs.types.DirNode):
	"""This type represents a project node of the file system containing
	all individual OBS packages as childs.
	"""

	def __init__(self, parent, name):

		super(Project, self).__init__(name = name)
		self.m_parent = parent

	def getObs(self):

		return self.m_parent.getObs()

	def getProject(self):

		return self.getName()

	def update(self):

		if not self.isCacheStale():
			return

		self.clearEntries()

		obs = self.m_parent.getObs()

		project = self.getName()

		for package in obs.getPackageList(project):

			if package in self.m_entries:
				continue

			self.m_entries[package] = oscfs.package.Package(
				self, package,
				project = self.getProject(),
				package = package
			)

		self.setCacheFresh()

