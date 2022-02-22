# OSC File System

## Introduction

*oscfs* is a FUSE based user space file system that allows to access open
build service (OBS) instances. It is based on the *osc* (openSUSE Commander)
Python package for interfacing with OBS. At the moment it provides read-only
access for inspecting packages and their metadata.

# Dependencies

*oscfs* itself is implemented in Python and uses the *fusepy* module to
implement the file system portion. There is another Python Fuse package called
*python-fuse* which **is not compatible** with *oscfs*.

For accessing OBS instances the Python *osc* module is required. The *osc*
module by now is working with Python3, therefore *oscfs* is no longer
supporting Python2 since version 0.8.0.

## Features

- Representation of all OBS projects and packages in a hierarchical file
  system.
- Access to individual package files including old revisions.
- Access to project and package metadata via pseudo files.
- Access to package buildlogs and artifacts.
- Configurable runtime caching of cached data.

## Usage

*oscfs* ships a main script called `oscfs`. It supports a couple of command
line parameters to influence its behaviour. It should only be called by a
regular user and never by the `root` user.

For mounting the file system simply provide the *mountpoint* argument to the
`oscfs` main script. By default the openSUSE build service is accessed. For
authentication at the OBS instance, the configuration file in the home
directory in `~/.config/osc/oscrc` (or `~/.oscrc` on older installations)
needs to be setup. This file is part of the *osc* Python module for which you
can find more documentation in the [openSUSE
wiki](https://en.opensuse.org/openSUSE:OSC).

To access a different OBS instance, provide the URL via the `--apiurl`
parameter. For example to mount the SUSE internal build service (IBS) under
use a command line like this:

```sh
$ oscfs --apiurl https://api.suse.de ~/ibs
```

By default `oscfs` detaches and runs in the background as a daemon. For
testing purposes it can be run in the foreground by passing the `-f`
parameter.

Certain special OBS projects are excluded by default like the users' *home:*
projects, maintenance incident projects or PTF (Program Temporary Fix)
projects. This is the case, because a lot of these projects can exist in an
OBS instance which would clutter the file system contents.

If you want to include these types of projects you can pass the according
command line parameter like `--homes`, `--maintenance` or `--ptf`
respectively. Your user account's own home projects will always be included in
the file system independently of the `--homes` switch.

Content that has been fetched from the OBS instance will be cached locally for
a certain time to improve response times. The time before content will be
refreshed can be tuned via the `--cache-time` parameter.

## File System Structure

On the first level of the file system, a directory for each OBS project is
found. When accessing the openSUSE OBS instance you can find the
`openSUSE:Factory` directory, for example. On the second level the packages
within a project are found. Within `openSUSE:Factory` all packages that make
up the openSUSE Tumbleweed rolling release codebase are found. For example you
can find the package bash within `openSUSE:Factory/bash`.

Within each package directory you can find a list of flat files that make up
the package's data like RPM spec file, patches, source tarballs and so on.
You can read the file contents like every other file with your editor or tools
like `cat` and `less`. There are no regular subdirectories found in a package.

Each project and package directory contains a hidden `.oscfs` directory which
contains metadata and pseudo files provided by `oscfs`. These files are not
actually existing in OBS.

The following is a list of pseudo files provided in each project's `.oscfs`
directory:

- `bugowners`: contains a list of the usernames of the bugowners of the
  project, one per line. If the name starts with an '@' then the name refers
  to a group of users.
- `maintainers`: just like `bugowners` but contains a list of the project's
  maintainers.
- `debuginfo`: returns a boolean "0" or "1", indicating whether debuginfo
  generation is enabled.
- `locked`: returns a boolean "0" or "1", indicating whether the project is in
  the locked state.
- `meta`: returns the complete XML metadata for the project as provided by the
  OBS instance.
- `refresh`: this is a control file. When you write the value of "1" into the
  file then the cache for the project will be flushed. This can be used to
  force regeneration of cached content.
- `repositories`: this file returns a list of all the repositories defined for
  the project. Each new repository starts with a line `# <name>`. Following
  are a number of lines providing additional information about the repository
  like `archs: <...>`, defining the architectures used in the repository.

The following is a list of pseudo files provided in each package's `.oscfs`
directory:

- `bugowners`: the same as for projects above.
- `maintainers`: the same as for projects above.
- `description`: contains the human readable description of the package.
- `log`: contains the commit changelog of the package.
- `meta`: returns the complete XML metadata for the package as provided by the
  OBS instance.
- `num_revisions`: returns an integer denoting the number of commit revisions
  that are available for the package.
- `commits`: a directory that contains one file for each commit available for
  the package. Each file is named after the commit revision number. Each file
  returns a description of the commit user, date and description.
- `requests`: a directory that contains one file for each OBS request that
  exists for the package. Each file is named in the format `<num>:<state>`,
  where `<num>` is the submit request ID and `<state>` is the current state of
  the request. Upon reading each file returns the description and history of
  the submit request it represents.
- `revisions`: a directory that contains a subdirectory for each commit
  available for the package. Each directory is named after the commit revision
  number. Each directory contains the state of the package's files as of that
  revision.
- `buildresults`: A file that contains the current package build results for
  each repository/architecture combination.
- `buildlogs`: a directory below which a hierarchy of repository/architecture
  files can be found. The architecture files are regular files that return the
  build log of the package for the repository/architecture combination it
  represents.
- `binaries`: a directory below which a hierarchy of repository/architecture
  directories can be found. Within the architecture directory the binary
  artifacts can be found that have been produced in the package for the
  repository/architecture combination it represents.
- `incident`: a symlink only present in package updates that originate from a
  maintenance incident. In this case this symlink points to the maintenance
  project where the package was built. For this to work the file system needs
  to be mounted with the `--maintenance` parameter.

## Usage Hints

### How the Runtime Caching Works

Each operation performed on the file system in some way needs to talk to the
remote OBS instance. This is a slow process and needs to be minimized. The
`oscfs` performs lazy evaluation of directory contents. This means that only
when you access a certain path for the first time will the actual contents be
determined by communicating with the OBS instance. This will take a noticeable
amount of time. The second time you will access the same path a locally cached
version of the file or directory will be served. This will take considerably
less time.

Caching also means that the state of files shown in the file system may not
correspond to the state on the remote server any more. Therefore `oscfs`
refetches the contents of files and directories after the cache has reached a
certain age as is determined by the `--cache-time` parameter. This only
happens when a cached path is accessed after the configured cache time has
passed since the last retrieval of data from the remote server. You can also
explicitly invalidate the caching for a complete package by writing to the
`refresh` control file documented above.

When `oscfs` is restarted then any previously cached contents are lost. This
means that the cache is not written to the local disk in any form. Fetching a
lot amount of data from the remote server should be avoided (e.g. don't call
`find` for the complete file system). This would be a kind of denial of
service attack on the remote server.

In a future version of `oscfs` evaluation of remote server modification times
could be used to transparently update cached data when necessary.

### Sorting of Directory Contents

Listing directories with `ls` can feel a bit on the slow side, even if data is
cached by `oscfs`. This results from `ls` sorting the directory contents by
name. Since e.g. `openSUSE:Factory` contains more than 10.000 entries this can
take about a second to complete. When listing without sorting i.e. by running
`ls -f` then the time required is considerably lower. Similar considerations
need to be made when accessing the file system by other means like from
programming languages that could sort directory contents by default.

### Metadata of Pseudo Files

The pseudo files contained in the `.oscfs` directory of a package start out
with a size of zero bytes, although they may actually contain data. The reason
for this is that for determining the size of the content, the content would
need to be accessed right away. This would slow down e.g. recursive searching
for file names considerably. Therefore some metadata like the size of pseudo
files is only calculated after it is accessed the first time. Since some of
the pseudo files may return dynamic data the displayed file size is also
subject to change at any time i.e. it only reflects a snapshot of the data as
it was last seen by `oscfs`.

## Usage Examples

### Finding Packages

You can find packages by using tools like `find` or shell wildcards expansion.
To find all Fuse related packages you do this for example:

```sh
$ cd openSUSE:Factory
$ ls -d *fuse*
enblend-enfuse  fuse  fuse-exfat  fuseiso  fusepod  fusesmb  ifuse  ldapfuse  libconfuse0  python-defusedxml  python-fuse  python-fusepy  unionfs-fuse
```

### Matching Lines from RPM Specs

You can query for packages containing certain RPM spec statements. For example
to find packages that require some Perl package by using grep like this:

```sh
$ cd openSUSE:Factory
$ grep -H "^Requires:.*perl" */*.spec
```

Note that this is going to take a long time, because each package needs to be
queried on OBS.

### Comparing Two Package Revisions

You can check two package revisions for differences by taking this approach:

```sh
$ cd openSUSE:Factory/bash/.oscfs/revisions
$ diff -r 1 2
<diff output...>
```
