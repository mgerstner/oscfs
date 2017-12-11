# vim: ts=8 sw=8 sts=8 :

# standard modules
from __future__ import with_statement, print_function

# local modules
import oscfs.types

class Link(oscfs.types.Node):
	"""This type represents a symlink in an OBS package which can
	return its target via readlink()."""

	def __init__(self, parent, name, target):

		super(Link, self).__init__(parent, name, oscfs.types.FileType.symlink)
		self.m_target = target

		stat = self.getStat()
		stat.setSize(len(self.m_target))

	def readlink(self):

		return self.m_target


