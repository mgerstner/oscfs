import datetime

import fuse

import oscfs.misc

class FileType(object):

	regular = 1
	directory = 2
	symlink = 4

class Stat(fuse.Stat):

	def __init__(self):
		import stat
		super(Stat, self).__init__()
		self.st_mode = 0o400 | stat.S_IFREG
		self.st_uid = oscfs.misc.getUid()
		self.st_gid = oscfs.misc.getGid()
		self.st_nlink = 1

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

	def setModTime(self, time):

		self.st_mtime = "testasdflj"
		self.st_atime = 50000
		self.st_ctime = 50000
		#self.st_mtime = fuse.Timespec()
		#self.st_mtime.tv_sec = 5000
		#self.st_mtime.tv_nsec = 50000

class Node(object):
	"""Generic file node type which needs to be specialized for regular
	files, directories et al.
	
	At this level a concept of caching is introduced to keep track of
	fresh/stale entries etc.

	Also the Stat information is kept in this base class.
	"""

	max_cache_time = datetime.timedelta(minutes = 5)

	def __init__(self, _type = FileType.regular):

		self.m_stat = Stat()
		self.setType(_type)
		self.setCacheFresh()

	@classmethod
	def setMaxCacheTime(cls, minutes):
		cls.max_cache_time = datetime.timedelta(minutes = minutes)

	def getStat(self):
		return self.m_stat

	def isCacheStale(self):
		age = datetime.datetime.now() - self.m_last_updated
		return age > Node.max_cache_time

	def setCacheFresh(self):
		self.m_last_updated = datetime.datetime.now()

	def setType(self, _type):
		self.m_type = _type
		self.m_stat.setFileType(_type)


