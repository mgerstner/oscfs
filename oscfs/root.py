# vim: ts=8 sw=8 sts=8 :

# standard modules
from __future__ import with_statement, print_function
import os

# local modules
import oscfs.types
import oscfs.obs
import oscfs.project

class Root(oscfs.types.DirNode):
	"""This type represents the root node of the file system containing
	all the OBS projects as childs.

	The root node can be used to iterate the complete file system.
	"""

	def __init__(self, obs, args):

		super(Root, self).__init__(None, name = "/")

		self.m_obs = obs
		self.m_args = args

	def getObs(self):

		return self.m_obs

	def getNode(self, path):
		"""Traverses child nodes until the given path is found.
		Returns the corresponding Node object."""

		if path == self.getName():
			return self

		parts = path.split(os.path.sep)[1:]

		node = self

		for part in parts:

			node.updateIfNeeded()
			entries = node.getEntries()

			node = entries[part]

		return node

	def update(self):
		for project in self.m_obs.getProjectList():

			if project in self.m_entries:
				continue

			parts = project.split(':')

			is_home = "home" in parts
			is_maintenance = "Maintenance" in parts
			is_ptf = "PTF" in parts

			if is_home:
				# if it's our own home then still keep it
				is_our_home = self.m_obs.getUser() in parts
				if not is_our_home and not self.m_args.homes:
					continue
			elif is_maintenance and not self.m_args.maintenance:
				continue
			elif is_ptf and not self.m_args.ptf:
				continue

			self.m_entries[project] = oscfs.project.Project(
				self, project
			)

		self.setCacheFresh()

