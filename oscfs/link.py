# vim: ts=8 sw=8 sts=8 :

# standard modules
from __future__ import with_statement, print_function
import os

# local modules
import oscfs.types

class Link(oscfs.types.Node):
	"""This type represents a symlink in an OBS package which can
	return its target via readlink()."""

	def __init__(self, parent, name, target):

		super(Link, self).__init__(parent, name, oscfs.types.FileType.symlink)
		depth = self.calcDepth()
		up = "{}/".format(os.path.pardir) * depth
		self.m_target = up + target

		stat = self.getStat()
		stat.setSize(len(self.m_target))
		stat.setMode(0o777)

	def readlink(self):

		return self.m_target


