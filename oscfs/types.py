# vim: ts=8 sw=8 sts=8 :

# std. modules
from __future__ import with_statement, print_function
import datetime
import time

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
		import stat
		super(Stat, self).__init__()
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

class Node(object):
	"""Generic file node type which needs to be specialized for regular
	files, directories et al.

	At this level a concept of caching is introduced to keep track of
	fresh/stale entries etc.

	Also the Stat information is kept in this base class.
	"""

	max_cache_time = datetime.timedelta(minutes = 30)

	def __init__(self, parent, name, _type = FileType.regular):

		self.m_stat = Stat()
		self.m_name = name
		self.m_parent = parent
		self.setType(_type)
		self.m_last_updated = None

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

	def setType(self, _type):
		self.m_type = _type
		self.m_stat.setFileType(_type)

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

class FileNode(Node):

	def __init__(self, parent, name):

		super(FileNode, self).__init__(parent, name)

	def setContent(self, content, date = None):
		self.m_content = content
		stat = self.getStat()
		stat.setSize(len(content))

		if date:
			stat.setModTime(date)

	def setBoolean(self, value):
		self.setContent("1" if value else "0")

	def read(self, length, offset):
		return self.m_content[offset:length]

class DirNode(Node):

	def __init__(self, parent, name):

		super(DirNode, self).__init__(
			parent,
			name,
			_type = FileType.directory
		)
		self.clearEntries()

	def getNames(self):

		self.update()

		dots = [".", ".."]
		entries = self.m_entries.keys()

		return entries + dots

	def clearEntries(self):

		self.m_entries = dict()

	def getEntries(self):

		return self.m_entries

