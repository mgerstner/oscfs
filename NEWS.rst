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
