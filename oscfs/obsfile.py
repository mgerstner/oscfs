# vim: ts=8 sw=8 sts=8 :

# standard modules
from __future__ import with_statement, print_function

# local modules
import oscfs.types

class ObsFile(oscfs.types.Node):
	"""This type represents a regular file in an OBS package which can
	return actual file content via read()."""

	def __init__(self, parent, name, size, mtime, revision = None):

		super(ObsFile, self).__init__(parent, name)
		self.m_revision = revision

		stat = self.getStat()
		stat.setModTime(mtime)
		stat.setSize(size)

	def read(self, length, offset):

		obs = self.getRoot().getObs()

		data = obs.getSourceFileContent(
			self.getProject().getName(),
			self.getPackage().getName(),
			self.getName(),
			revision = self.m_revision
		)

		return data[offset:length]

