# vim: ts=8 sw=8 sts=8 :

# standard modules
from __future__ import with_statement, print_function

# local modules
import oscfs.types

class File(oscfs.types.Node):
	"""This type represents a regular file in an OBS package which can
	return actual file content via read()."""

	def __init__(self, parent, name, size, mtime):

		super(File, self).__init__(name = name)
		self.m_parent = parent

		stat = self.getStat()
		stat.setModTime(mtime)
		stat.setSize(size)

	def getProject(self):

		return self.m_parent.getProject()

	def getPackage(self):

		return self.m_parent.getName()

	def read(self, length, offset):

		obs = self.m_parent.getObs()

		data = obs.getFileContent(
			self.getProject(),
			self.getPackage(),
			self.getName()
		)

		return data[offset:length]

