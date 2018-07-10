# vim: ts=8 sw=8 sts=8 :

# std. modules
from __future__ import with_statement, print_function
import datetime
import time
import stat
import errno

# third party modules
import fuse

# local modules
import oscfs.misc

class FileType(object):

	regular = 1
	directory = 2
	symlink = 4

class Stat(object):

	start_time = datetime.datetime.now()

	def __init__(self):
		super(Stat, self).__init__()
		# TODO: incorporate umask?
		self.st_mode = 0o400 | stat.S_IFREG
		self.st_uid = oscfs.misc.getUid()
		self.st_gid = oscfs.misc.getGid()
		self.st_nlink = 1
		# at least give each new node some current time
		self.setModTime(self.start_time)

	def updateModTime(self):
		self.setModTime(time.time())

	def setFileType(self, _type):

		import stat

		if _type == FileType.regular:
			new_mode = stat.S_IFREG
			self.st_mode &= ~(stat.S_IXUSR)
		elif _type == FileType.directory:
			new_mode = stat.S_IFDIR
			self.st_mode |= stat.S_IXUSR
		elif _type == FileType.symlink:
			new_mode = stat.S_IFLNK
		else:
			raise Exception("Invalid type specified: " + str(_type))

		self.st_mode &= ~(stat.S_IFMT(self.st_mode))
		self.st_mode |= new_mode

	def setSize(self, size):
		"""Sets the size of the node in bytes."""

		import math
		self.st_size = size
		self.st_blocks = int(math.ceil(size / 512.0))

	def setModTime(self, tm):

		if isinstance(tm, datetime.datetime):
			tm = time.mktime(tm.timetuple())

		self.st_mtime = tm
		self.st_atime = tm
		self.st_ctime = tm

	def toDict(self):

		ret = dict()
		for attr in dir(self):
			if attr.startswith("st_"):
				ret[attr] = getattr(self, attr)

		return ret

	def setLinks(self, links):
		self.st_nlink = links

	def setMode(self, mode):

		if mode > 0o777:
			raise Exception("Invalid mode encountered")

		self.st_mode &= ~0o777
		self.st_mode |= mode

	def isReadable(self):
		return (self.st_mode & stat.S_IRUSR) != 0

	def isWriteable(self):
		return (self.st_mode & stat.S_IWUSR) != 0

class Node(object):
	"""Generic file node type which needs to be specialized for regular
	files, directories et al.

	At this level a concept of caching is introduced to keep track of
	fresh/stale entries etc.

	Also the Stat information is kept in this base class.
	"""

	max_cache_time = datetime.timedelta(minutes = 60)

	def __init__(self, parent, name, _type = FileType.regular):

		self.m_stat = Stat()
		self.m_name = name
		self.m_parent = parent
		self.setType(_type)
		self.m_last_updated = None
		self.m_auto_clear_on_update = True

	@classmethod
	def setMaxCacheTime(cls, seconds):
		cls.max_cache_time = datetime.timedelta(seconds = seconds)

	def getStat(self):
		return self.m_stat

	def getName(self):
		return self.m_name

	def getParent(self):
		return self.m_parent

	def isCacheStale(self):
		if not self.wasEverUpdated():
			return True

		age = datetime.datetime.now() - self.m_last_updated
		return age > Node.max_cache_time

	def wasEverUpdated(self):
		return self.m_last_updated != None

	def setCacheFresh(self):
		self.m_last_updated = datetime.datetime.now()

	def setCacheStale(self):
		self.m_last_updated = None

	def setType(self, _type):
		self.m_type = _type
		self.m_stat.setFileType(_type)

	def _setAutoClearOnUpdate(self, on_off):
		self.m_auto_clear_on_update = on_off

	def doAutoClearOnUpdate(self):
		return self.m_auto_clear_on_update

	def calcDepth(self):
		"""Returns the nesting depth of the Node i.e. the number of
		parent directories it has up to the root node."""

		parent = self.m_parent
		ret = 0

		while not parent.isRoot():
			parent = parent.getParent()
			ret += 1

		return ret

	def isRoot(self):
		"""Returns whether this node is the root node of the file
		system."""
		return self.m_parent == None

	def getRoot(self):
		"""Returns the root node of the file system."""
		ret = self
		while ret.m_parent:
			ret = ret.m_parent
		return ret

	def _findParent(self, _type):
		ret = self.m_parent
		while ret:
			if isinstance(ret, _type):
				return ret
			ret = ret.m_parent

		raise Exception("No parent of type '{}' found".format(str(_type)))

	def getPackage(self):
		"""Returns the package node the current node belongs to."""
		import oscfs.package
		return self._findParent(oscfs.package.Package)

	def getProject(self):
		"""Returns the project node the current node belongs to."""
		import oscfs.project
		return self._findParent(oscfs.project.Project)

	def updateIfNeeded(self):
		"""Calls the update method if it is necessary."""
		if self.isCacheStale():
			if self.doAutoClearOnUpdate():
				self.clearEntries()
			self.update()
			self.setCacheFresh()

class FileNode(Node):
	"""Specialized Node type for read-only regular files. Implementations
	of this type can set the current content of the file via setContent()
	in their constructors and everything else is cared for. For lazy
	evaluation of file content implement fetchContent() which should call
	setContent() in turn."""

	def __init__(self, parent, name):

		super(FileNode, self).__init__(parent, name)
		self.m_content = None
		self.m_use_cache = True

	def setContent(self, content, date = None):
		self.m_content = content
		stat = self.getStat()
		stat.setSize(len(content))

		if date:
			stat.setModTime(date)

	def setUseCache(self, on_off):
		self.m_use_cache = on_off

	def setBoolean(self, value):
		self.setContent("1" if value else "0")

	def read(self, length, offset):
		if self.m_content is None or not self.m_use_cache:
			self.fetchContent()

		return self.m_content[offset:offset+length]

class TriggerNode(Node):
	"""Specialized Node type for writable pseudo files. It expects a
	boolean value of 0 or 1 as write content. If it is encountered then a
	virtual method is called which can be overwritten by derived classes.
	"""

	def __init__(self, parent, name):

		super(TriggerNode, self).__init__(parent, name)
		self.getStat().setMode(0o200)

	def triggered(self, value):
		"""This method needs to be implemented to react on valid
		boolean values written to the file."""
		pass

	def write(self, data, offset):

		def bad():
			raise fuse.FuseOSError(errno.EINVAL)

		if offset != 0:
			bad()
		elif data.strip() == "0":
			self.triggered(False)
		elif data.strip() == "1":
			self.triggered(True)
		else:
			bad()

		return len(data)

class DirNode(Node):
	"""Specialized Node type for directories. This type introduces a
	dictionary of name -> Node mappings."""

	def __init__(self, parent, name):

		super(DirNode, self).__init__(
			parent,
			name,
			_type = FileType.directory
		)
		# correct link count for directories
		self.getStat().setLinks(2)
		self.clearEntries()

	def getNames(self):

		self.updateIfNeeded()

		dots = [".", ".."]
		entries = self.m_entries.keys()

		return entries + dots

	def clearEntries(self):

		self.m_entries = dict()

	def getEntries(self):

		return self.m_entries

	def setCacheStale(self):

		Node.setCacheStale(self)

		for entry in self.m_entries.values():
			entry.setCacheStale()

class PlainDirNode(DirNode):
	"""Specialized DirNode that doesn't implement its own update logic.
	This type of dir can be used to implement subdirs that shouldn't act
	on their own."""

	def __init__(self, *args, **kwargs):

		super(PlainDirNode, self).__init__(*args, **kwargs)
		self._setAutoClearOnUpdate(False)

	def update(self):
		pass

