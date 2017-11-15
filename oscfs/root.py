# vim: ts=8 sw=8 sts=8 :

# standard modules
from __future__ import with_statement, print_function

# third party modules
import osc.core

# local modules
import oscfs.types

class Root(oscfs.types.Node):
	"""This type represents the root node of the file system containing
	all the OBS projects as childs.

	The root node can be used to iterate the complete file system.
	"""

	def __init__(self):

		super(Root, self).__init__(
			_type = oscfs.types.FileType.directory
		)

		self.getStat().setModTime(self.m_last_updated)

	def update(self):

		pass


