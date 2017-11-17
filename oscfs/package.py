# vim: ts=8 sw=8 sts=8 :

# standard modules
from __future__ import with_statement, print_function

# local modules
import oscfs.types
import oscfs.obs
import oscfs.file

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
	
	def update(self):

		if not self.isCacheStale():
			return

		obs = self.m_parent.getObs()

		for name, size, mtime in obs.getPackageFileList(
			self.getProject(), self.getName()
		):
			node = oscfs.file.File(self, name, size, mtime)
			self.m_entries[name] = node
		
		self.setCacheFresh()
		

