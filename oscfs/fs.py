import argparse
import errno
import os
import sys

# third party modules
import fuse

# local modules
import oscfs.obs
import oscfs.root


class OscFs(fuse.LoggingMixIn, fuse.Operations):
    """The main class implementing the fuse operations and python-fuse
    setup."""

    def __init__(self):

        self.m_default_url = "https://api.opensuse.org"
        self.m_obs = oscfs.obs.Obs()
        # stores file handle -> node mappings
        # (file handles need to be integers)
        self.m_handles = [None] * 1024
        # unallocated file handles
        self.m_free_handles = list(range(1024))
        self._setupParser()

    def _setupParser(self):

        self.m_parser = argparse.ArgumentParser(
            description="SUSE open build service file system"
        )

        self.m_parser.add_argument(
            "-f", action='store_true',
            help="Run the file system in the foreground"
        )
        self.m_parser.add_argument(
            "--apiurl", type=str, default=self.m_default_url,
            help="The API URL of the OBS instance. openSUSE build service is used by default"
        )
        self.m_parser.add_argument(
            "--homes", action='store_true',
            help="If set then home projects will be included which is not the default"
        )
        self.m_parser.add_argument(
            "--maintenance", action='store_true',
            help="If set then maintenance projects will be included which is not the default"
        )
        self.m_parser.add_argument(
            "--ptf", action='store_true',
            help="If set then PTF projects will be included which is not the default"
        )
        self.m_parser.add_argument(
            "mountpoint", type=str,
            help="Path where to mount the file system"
        )

        CACHE_SECS = oscfs.types.Node.max_cache_time.seconds

        self.m_parser.add_argument(
            "--cache-time", type=int,
            default=None,
            help=f"""Specifies the time in seconds the contents
                of the file system will be cached. Default: {CACHE_SECS}
                seconds. Set to zero to disable caching."""
        )

    def _checkAuth(self):
        """Check for correct authentication at the remote server."""
        # simply fetch the root entries, this will also benefit the
        # initial access at least. On HTTP 401 this will throw an
        # exception.
        import urllib.request
        try:
            _ = self.m_obs.getProjectInfo("openSUSE:Factory")
            return
        except urllib.request.HTTPError as e:
            if e.code == 401:
                print(
                    "Authorization at the remote server failed. Please check your ~/.oscrc user/pass settings for API url {}.".format(
                        self.m_args.apiurl
                    ),
                    file=sys.stderr
                )
            elif e.code == 404:
                # authorization worked but the project is not there, also fine
                return
            else:
                print("HTTP error occured trying to access the remote server:")
                print(e)
        except Exception as e:
            print(
                "Accessing the remote server failed:",
                e, file=sys.stderr
            )
            raise

        sys.exit(1)

    def _getNode(self, path, fh=None):

        if fh is not None:
            return self._getFileHandle(fh)
        else:
            try:
                return self.m_root.getNode(path)
            except KeyError:
                raise fuse.FuseOSError(errno.ENOENT)

    def run(self):

        self.m_args = self.m_parser.parse_args()
        self.m_obs.configure(self.m_args.apiurl)
        self.m_root = oscfs.root.Root(self.m_obs, self.m_args)
        if self.m_args.cache_time is not None:
            oscfs.types.Node.setMaxCacheTime(self.m_args.cache_time)

        self._checkAuth()

        fuse.FUSE(
            self,
            self.m_args.mountpoint,
            foreground=self.m_args.f,
            nothreads=True,
            # direct_io is necessary in our use case to avoid
            # caching in the kernel and support dynamically
            # determined file contents
            direct_io=True,
            nonempty=True
        )

    def init(self, path):
        """This is called upon file system initialization."""
        if self.m_args.f:
            # print a status message that allows e.g. the regtest
            # program to determine when the file system is
            # actually mounted
            print("file system initialized")
            sys.stdout.flush()

    # global file system methods

    def getattr(self, path, fh=None):

        node = self._getNode(path, fh)

        ret = node.getStat()

        return ret.toDict()

    def readdir(self, path, fh=None):

        node = self._getNode(path, fh)

        ret = node.getNames()

        return ret

    def readlink(self, path):
        node = self._getNode(path)
        return node.readlink()

    # per file handle methods

    def _allocFileHandle(self, node):

        if not self.m_free_handles:
            raise fuse.FuseOSError(errno.EMFILE)

        fd = self.m_free_handles.pop(0)

        if self.m_handles[fd] is not None:
            raise Exception("Handle allocation inconsistency")

        self.m_handles[fd] = node

        return fd

    def _freeFileHandle(self, fh):

        self.m_handles[fh] = None
        self.m_free_handles.append(fh)

    def _getFileHandle(self, fh):

        return self.m_handles[fh]

    def opendir(self, path):

        node = self._getNode(path)
        return self._allocFileHandle(node)

    def release(self, path, fh):

        if fh is not None:
            self._freeFileHandle(fh)

    def releasedir(self, path, fh):

        if fh is not None:
            self._freeFileHandle(fh)

    def truncate(self, path, length, fh=None):

        node = self._getNode(path, fh)
        if node.getStat().isWriteable():
            # be tolerant for pseudo files such that "echo '1'
            # >file" works.
            return

        # otherwise report an error
        raise fuse.FuseOSError(errno.EPERM)

    def open(self, path, flags):

        node = self._getNode(path)

        if not node.getStat().isWriteable():
            # deny writing
            for badflag in (os.O_RDWR, os.O_WRONLY, os.O_CREAT):
                if (flags & badflag) != 0:
                    raise fuse.FuseOSError(errno.EPERM)

        return self._allocFileHandle(node)

    def read(self, path, length, offset, fh):

        node = self._getNode(path, fh)

        if not node.getStat().isReadable():
            raise fuse.FuseOSError(errno.EBADF)

        return node.read(length, offset)

    def write(self, path, data, offset, fh):

        node = self._getNode(path, fh)

        return node.write(data, offset)
