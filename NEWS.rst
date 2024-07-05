0.9.1
=====

- minor fix for compatibility with OSC version >= 1.6.1, to avoid HTTP bad
  request errors when opening files.

0.9.0
=====

- use Python3 by default now.
- various small bugfixes:
  - fix error if a binary build artifact has zero file size
  - fix symlink target in package update links (symlink to maintenance
    incidents).
- new --no-urlopen-wrapper command line option to disable the HTTP connection
  reuse hack. This is helpful when working against build.suse.de, where
  two-factor-authentication is now required and the hack doesn't work with
  that anymore.
- new --no-bin-cache command line option to disable caching of large binary files.
- new --use-logfile command line option to write errors and debugging
  information to file. This is helpful when oscfs is running as a daemon and
  stdout/stderr are discarded.
- implements transparent retry if the OBS server responds with HTTP status 503
  (service unavailable).

0.8.1
=====

- fix minor error in urlopen wrapper occuring in  some Python versions,
  causing an exception upon start.

0.8.0
=====

- fix error if a package filename contained the '#' character.
- fix authentication error detection during startup.
- enable urlopenwrapper hack again which speeds up consecutive requests
  drastically.
- source code ported to Python3 only, removed all Python2 compatibility.
  Source code is now conforming largely to PIP and flake8 standards.

0.7.2
=====

- fix error when reading from some "buildlog" nodes that contained non-utf8
  encoding data.
- fix problem with grep on larger files, because more data was returned by
  read() than actually requested when unicode data was involved.

0.7.1
=====

- fix read() with offset especially with large files. This fixes use of
  various tools when applied on oscfs files e.g. `rpm2cpio` or
  `tail *.spec` previously failed or behaved strangely.
- be robust against non-ASCII characters in OBS buildlogs.
- apply caching also to actual file content to be more efficient when e.g.
  operating on larger files.

0.7.0
=====

- Added support for running in Python3 with the Python3 osc module installed.
- support mounting of oscfs in non-empty directories.
- minor bugfixes with accessing package and project meta data via `.oscfs`.

0.6.1
=====

- Fixed a bug with accessing the artifacts in the ``.oscfs/binaries/``
  per-package sub-directory. The data was very inefficiently retrieved
  from the OBS server resulting in extremely low read performance.

0.6.0
=====

- Initial release
