# standard modules
from xml.etree import cElementTree as et
import datetime

# urllib2 replacement, needs to be imported before osc.core
import oscfs.urlopenwrapper

# third party modules
import osc.core


class Obs:
    """Wrapper around the osc python module for the purposes of this file
    system."""

    def __init__(self):
        pass

    def configure(self, apiurl):

        import osc.conf
        self.m_apiurl = apiurl
        try:
            osc.conf.get_config()
        except osc.oscerr.NoConfigfile:
            raise Exception("No .oscrc config file found. Please configure OSC first.")
        except osc.oscerr.ConfigError as e:
            raise Exception(f"No valid configuration found in .oscrc: {e}. Please configure OSC first.")

        osc.conf.config["apiurl"] = apiurl

    def getUser(self):
        return osc.conf.config["user"]

    def getProjectList(self):
        """Returns a list of the top-level projects of the current OBS
        instance. It's a list of plain strings."""

        ret = osc.core.meta_get_project_list(self.m_apiurl)

        return ret

    def getProjectMeta(self, project):
        """Returns a string consisting of the XML that makes up the
        specified project's metadata."""

        xml_lines = osc.core.show_project_meta(self.m_apiurl, project)

        return '\n'.join([line.decode() for line in xml_lines])

    def getProjectInfo(self, project):
        """Returns an object of type ProjectInfo for the given
        project."""
        xml = self.getProjectMeta(project)
        return ProjectInfo(xml)

    def getPackageList(self, project):
        """Returns a list of all the packages within a top-level
        project. It's a list of plain strings."""

        ret = osc.core.meta_get_packagelist(self.m_apiurl, project)

        return ret

    def _getPackageFileTree(self, project, package, revision=None):
        xml = osc.core.show_files_meta(
            self.m_apiurl,
            project,
            package,
            revision=revision,
            meta=False
        )

        tree = et.fromstring(xml)
        return tree

    def getPackageFileList(self, project, package, revision=None):
        """Returns a list of the files belonging to a package. The
        list is comprised of tuples of the form (name, size,
        modtime)."""

        tree = self._getPackageFileTree(
            project,
            package,
            revision=revision
        )
        ret = []

        # if this is a linked package then we find two nodes
        # "linkinfo" and a "_link" file entry. For getting information
        # about the link we need to query the linkinfo first
        #
        # sadly there seems to be no way to query a package's link
        # property without individually listing it which is a
        # performance issue.
        #
        # therefore we only make the _link a symlink, not the package
        # itself
        li_node = tree.find("linkinfo")
        # xml node seems to have a strange boolean behaviour...
        if li_node is None:
            link_target = None
        else:
            linkinfo = osc.core.Linkinfo()
            linkinfo.read(li_node)
            link_target = "{}/{}".format(
                linkinfo.project,
                linkinfo.package
            )

        from oscfs.types import FileType

        for entry in tree:

            if entry.tag != "entry":
                continue

            attrs = entry.attrib
            name = attrs["name"]
            is_link = name == "_link" and link_target
            ft = FileType.symlink if is_link else FileType.regular
            size = int(attrs["size"])
            mtime = int(attrs["mtime"])
            link = link_target if is_link else None
            ret.append((ft, name, size, mtime, link))

        return ret

    def getPackageRequestList(self, project, package, states=None):
        """Returns a list of osc.core.Request instances representing
        the existing requests for the given project/package.

        If @states is specified then it is supposed to be a list of
        state labels the returned requests should be in. Otherwise all
        requests regardless of state will be returned."""

        return osc.core.get_request_list(
            self.m_apiurl,
            project,
            package,
            req_state=states if states else ['all'],
            withfullhistory=True
        )

    def getSourceFileContent(self, project, package, _file, revision=None):

        # 'cat' is surprisingly difficult ... approach taken by the
        # 'osc cat' command line logic.

        query = {
            # don't follow source links
            "expand": 0
        }

        if revision:
            query["rev"] = revision

        return self._download(
            ['source', project, package, _file],
            query
        )

    def getBinaryFileContent(self, project, package, repo, arch, _file):
        comps = ['build', project, repo, arch, package, _file]
        return self._download(comps)

    def _download(self, urlcomps, query=dict()):

        import urllib.parse
        # makeurl below doesn't urlencode the actual url components, only the
        # query parameters. This breaks certain file names that e.g. contain
        # '#'. So let's explicitly urlencode them.
        urlcomps = [urllib.parse.quote_plus(comp) for comp in urlcomps]

        url = osc.core.makeurl(
            self.m_apiurl,
            urlcomps,
            query=query
        )

        f = osc.core.http_GET(url)

        return f.read()

    def _getPackageRevisions(self, project, package, fmt):
        """Returns the list of revisions for the given project/package
        path in the given fmt. @fmt can be any of ('text, 'csv',
        'xml'). Each revision will come with date and commit text."""

        return osc.core.get_commitlog(
            self.m_apiurl,
            project,
            package,
            None,
            format=fmt
        )

    def getCommitLog(self, project, package):
        """Returns a string containing the commit log of the given
        package in human readable form."""
        return '\n'.join(
            self._getPackageRevisions(project, package, "text")
        )

    def getCommitInfos(self, project, package):
        """Returns details about each revision in the commit log as
        a list of instances of CommitInfo objects."""

        xml = self._getPackageRevisions(project, package, "xml")
        xml = '\n'.join(xml)

        tree = et.fromstring(xml)
        ret = []

        for entry in tree.iter("logentry"):
            rev = entry.attrib["revision"]
            ci = CommitInfo(int(rev))

            for child in entry:
                if child.tag == "author":
                    ci.setAuthor(child.text)
                elif child.tag == "date":
                    dt = datetime.datetime.strptime(
                        child.text,
                        "%Y-%m-%d %H:%M:%S"
                    )
                    ci.setDate(dt)
                elif child.tag == "requestid":
                    ci.setReqId(child.text)
                elif child.tag == "msg":
                    ci.setMessage(child.text)

            ret.append(ci)

        return sorted(
            ret,
            key=lambda r: r.getRevision()
        )

    def getPackageMeta(self, project, package):
        """Returns a string consisting of the XML that makes up the
        specified package's metadata."""

        xml_lines = osc.core.show_package_meta(
            self.m_apiurl,
            project,
            package
        )

        return '\n'.join([line.decode() for line in xml_lines])

    def getPackageInfo(self, project, package):
        """Returns an object of type PackageInfo for the given
        package."""
        xml = self.getPackageMeta(project, package)
        return PackageInfo(xml)

    def getBuildlog(self, project, package, repo, arch):
        """Returns the plaintext build log for the given build
        configuration. This can be empty if the build is not
        configured at all or currently in wait state. It can also be
        partial if building is currently in progress."""

        url = '/'.join([
            self.m_apiurl,
            "build",
            project, repo, arch, package,
            "_log?start=0&nostream=1"
        ])

        ret = b""

        # NOTE: streamfile supports bufsize="line" to read line wise
        # and supports yield semantics. This breaks with our
        # urlopenwrapper hack, however so we don't use it.
        for line in osc.core.streamfile(url):
            ret += line

        return ret

    def getBuildResultsMeta(self, project, package, repo=[], arch=[]):
        """Returns XML data describing the build status of the given
        project/package combination. If repo and arch are given then
        only the status of the given build configuration is returned,
        otherwise all available information is collected."""

        if not isinstance(repo, list):
            repo = [repo]
        if not isinstance(arch, list):
            arch = [arch]

        xml_lines = osc.core.show_results_meta(
            self.m_apiurl, project, package,
            repository=repo, arch=arch
        )

        return '\n'.join([line.decode() for line in xml_lines])

    def getBuildResults(self, *args, **kwargs):
        """Like getBuildResultsMeta() but returns a list of
        BuildResult objects."""

        xml = self.getBuildResultsMeta(*args, **kwargs)

        return BuildResultList(xml)

    def getBinaryList(self, project, package, repo, arch):
        """Returns a list of tuples representing the binary
        artifacts of the given build configuration. Each tuple
        consists of (filename, mtime, size)."""

        # when passing Verbose we get File object with metadata back
        ret = osc.core.get_binarylist(
            self.m_apiurl, project, repo, arch, package,
            verbose=True
        )

        return [(f.name, f.mtime, f.size) for f in ret]


class CommitInfo:

    def __init__(self, revision):

        self.m_revision = revision
        self.m_author = None
        self.m_date = None
        self.m_req_id = None
        self.m_message = None

    def getRevision(self):
        return self.m_revision

    def setAuthor(self, author):
        self.m_author = author

    def getAuthor(self):
        return self.m_author if self.m_author else "<none>"

    def setDate(self, date):
        self.m_date = date

    def getDate(self):
        return self.m_date if self.m_date else "<unknown>"

    def setReqId(self, req_id):
        self.m_req_id = req_id

    def getReqId(self):
        return self.m_req_id if self.m_req_id else -1

    def setMessage(self, message):
        self.m_message = message

    def getMessage(self):
        return self.m_message if self.m_message else "<none>"

    def __str__(self):
        return "r{}: {} on {} via request {}".format(
            self.m_revision,
            self.getAuthor(),
            self.getDate().strftime("%x %X"),
            self.getReqId()
        )


class InfoBase:

    def reset(self):
        self.m_title = ""
        self.m_desc = ""
        self.m_maintainers = []
        self.m_bugowners = []
        self.m_readers = []
        self.m_devel_project = ""
        self.m_name = ""

    def setTitle(self, title):
        self.m_title = title if title else ""

    def getTitle(self):
        return self.m_title

    def getName(self):
        return self.m_name

    def setName(self, name):
        self.m_name = name

    def setDesc(self, desc):
        self.m_desc = desc if desc else ""

    def getDesc(self):
        return self.m_desc

    def setMaintainers(self, maintainers):
        self.m_maintainers = maintainers

    def addMaintainer(self, maintainer):
        self.m_maintainers.append(maintainer)

    def getMaintainers(self):
        return self.m_maintainers

    def setBugowners(self, bugowners):
        self.m_bugowners = bugowners

    def addBugowner(self, bugowner):
        self.m_bugowners.append(bugowner)

    def getBugowners(self):
        return self.m_bugowners

    def addReader(self, reader):
        self.m_readers.append(reader)

    def getReaders(self):
        return self.m_readers

    def setDevelProject(self, project):
        self.m_devel_project = project

    def getDevelProject(self):
        return self.m_devel_project

    def _addRole(self, subject, role):
        if role == "bugowner":
            self.addBugowner(subject)
        elif role == "maintainer":
            self.addMaintainer(subject)
        elif role == "reader":
            self.addReader(subject)

    def parseXmlElement(self, el):

        if el.tag == "title":
            self.setTitle(el.text)
        elif el.tag == "description":
            self.setDesc(el.text)
        elif el.tag == "person":
            role = el.attrib["role"]
            user = el.attrib["userid"]
            self._addRole(user, role)
        elif el.tag == "group":
            role = el.attrib["role"]
            group = el.attrib["groupid"]
            group = f"@{group}"
            self._addRole(group, role)
        elif el.tag == "devel":
            project = el.attrib["project"]
            self.setDevelProject(project)
        else:
            return False

        return True


class PackageInfo(InfoBase):
    """Collective meta information about a package."""

    def __init__(self, meta_xml=None):
        if meta_xml:
            self.parse(meta_xml)
        else:
            self.reset()

    def reset(self):

        InfoBase.reset(self)
        # contains tuples of (repo, arch) where arch can also be None
        self.m_disabled_builds = []
        # same here for explicitly enabled builds in case of
        # m_all_disabled == True
        self.m_enabled_builds = []
        self.m_all_disabled = False
        self.m_release_name = ""

    def getDisabledBuilds(self):
        return self.m_disabled_builds

    def setDisabledBuilds(self, db):
        self.m_disabled_builds = db

    def addDisabledBuild(self, repo, arch):
        self.m_disabled_builds.append((repo, arch))

    def setAllDisabled(self, on_off):
        self.m_all_disabled = on_off

    def getAllDisabled(self):
        return self.m_all_disabled

    def getEnabledBuilds(self):
        return self.m_enabled_builds

    def setEnabledBuilds(self, eb):
        self.m_enabled_builds = eb

    def addEnabledBuild(self, repo, arch):
        self.m_enabled_builds.append((repo, arch))

    def setReleaseName(self, rn):
        self.m_release_name = rn

    def getReleaseName(self):
        return self.m_release_name

    def getMaintenanceIncident(self, project_info):
        # I don't whether there's some more programmatic way to
        # determine where the package was built.
        #
        # so the releasename from the package meta is the basename of
        # the package. The package name is <package>.<incident-number>

        if not self.m_release_name:
            return None
        elif len(self.getName()) <= len(self.m_release_name):
            return None

        parts = self.getName().split('.')
        incident = parts[-1]
        base = '.'.join(parts[:-1])

        if base != self.m_release_name:
            return None

        try:
            incident = int(incident)
        except ValueError:
            # not an incident number after all?
            return None

        parts = project_info.getName().split(':')
        if parts[-1] != "Update":
            # we need to be in an update project of some kind
            return None

        prefix = parts[0]

        return f"{prefix}:Maintenance:{incident}"

    def getAllActiveRepos(self, project_info):
        """Returns a list of all (repository, arch) tuples for which
        the current package building is enabled. @project_info is
        required to calculate this."""

        ret = []

        for repo in project_info.getRepos():

            rt = repo.getReleaseTarget()
            if rt and rt[2]:
                # this is a manually triggered repository
                # e.g. "images" in openSUSE:Factory
                continue

            archs = repo.getArchs()

            for arch in archs:
                ret.append((repo.getName(), arch))

        return ret

    def parse(self, meta_xml):
        """Parses a package meta XML string and fills the object's
        values from it."""

        self.reset()
        tree = et.fromstring(meta_xml)

        name = tree.attrib["name"]
        self.setName(name)

        for el in tree:
            if self.parseXmlElement(el):
                continue
            elif el.tag == "build":
                self.parseBuild(el)
            elif el.tag == "releasename":
                self.setReleaseName(el.text)

    def parseBuild(self, el):
        for child in el:
            if child.tag == "disable":
                repo = child.attrib.get("repository", None)
                arch = child.attrib.get("arch", None)
                if repo or arch:
                    self.addDisabledBuild(repo, arch)
                else:
                    # this is "<disable/>"
                    self.setAllDisabled(True)

            elif child.tag == "enable":
                repo = child.attrib.get("repository", None)
                arch = child.attrib.get("arch", None)
                self.addEnabledBuild(repo, arch)


class Repository:
    """Collective meta information about a repository in a
    project/package."""

    def __init__(self, xml_node):
        if xml_node:
            self.parse(xml_node)
        else:
            self.reset()

    def reset(self):
        self.m_name = ""
        self.m_project = ""
        self.m_repo = ""
        self.m_archs = []
        self.m_release_target = None
        self.m_enabled = True

    def parse(self, xml_node):
        self.reset()

        name = xml_node.attrib["name"]
        self.setName(name)

        for child in xml_node:
            if child.tag == "path":
                attrs = child.attrib
                project = attrs["project"]
                repo = attrs["repository"]
                self.setProject(project)
                self.setRepository(repo)
            elif child.tag == "arch":
                arch = child.text
                self.addArch(arch)
            elif child.tag == "releasetarget":
                attrs = child.attrib
                project = attrs["project"]
                repo = attrs["repository"]
                trigger = attrs.get("trigger", "")
                manual = trigger == "manual"
                self.setReleaseTarget(project, repo, manual)

    def getName(self):
        return self.m_name

    def setName(self, name):
        self.m_name = name

    def getProject(self):
        return self.m_project

    def setProject(self, project):
        self.m_project = project

    def getRepository(self):
        return self.m_repo

    def setRepository(self, repo):
        self.m_repo = repo

    def getArchs(self):
        return self.m_archs

    def addArch(self, arch):
        self.m_archs.append(arch)

    def getReleaseTarget(self):
        return self.m_release_target

    def setReleaseTarget(self, project, repo, manual):
        self.m_release_target = (project, repo, manual)

    def getEnabled(self):
        return self.m_enabled

    def setEnabled(self, on_off):
        self.m_enabled = on_off


class ProjectInfo(InfoBase):
    """Collective meta information about a project."""

    def __init__(self, meta_xml=None):
        if meta_xml:
            self.parse(meta_xml)
        else:
            self.reset()

    def __str__(self):

        ret = f"Project Info for {self.getName()}:\n"

        ret += "all disabled = " + self.getAllDisabled() + "\n"

        for repo in self.m_repos:
            ret += "- repository {} with archs {}\n".format(
                repo.getName(),
                ", ".join(repo.getArchs())
            )

        return ret

    def reset(self):
        InfoBase.reset(self)
        self.m_repos = []
        self.m_disabled_repos = []
        self.m_enabled_repos = []
        self.m_debuginfo = None
        self.m_locked = False
        self.m_all_disabled = False

    def parse(self, meta_xml):
        """Parses a project meta XML string and fills the object's
        values from it."""

        self.reset()
        tree = et.fromstring(meta_xml)

        name = tree.attrib["name"]
        self.setName(name)

        for el in tree:
            if self.parseXmlElement(el):
                continue
            elif el.tag == "debuginfo":
                self.setDebuginfoEnabled(False)
                for child in el:
                    if child.tag == "enable":
                        self.setDebuginfoEnabled(True)
            elif el.tag == "repository":
                repo = Repository(el)
                self.addRepo(repo)
            elif el.tag == "build":
                self.parseBuild(el)
            elif el.tag == "lock":
                for child in el:
                    if child.tag == "enable":
                        self.setLocked(True)

        self.postParse()

    def postParse(self):

        for repo in self.m_repos:

            if repo in self.m_enabled_repos:
                repo.setEnabled(True)
            elif repo in self.m_disabled_repos:
                repo.setEnabled(False)
            elif self.getAllDisabled():
                repo.setEnabled(False)

    def parseBuild(self, el):
        for child in el:
            if child.tag in ("disable", "enable"):
                is_enable = child.tag == "enable"
                attrib = child.attrib
                repo = attrib.get("repository", None)
                arch = attrib.get("arch", None)

                repo_list = self.m_enabled_repos if \
                    is_enable else \
                    self.m_disabled_repos

                if repo or arch:
                    repo_list.append(repo)
                else:
                    self.setAllDisabled(not is_enable)

    def getAllDisabled(self):
        return self.m_all_disabled

    def setAllDisabled(self, on_off):
        self.m_all_disabled = on_off

    def getDebuginfoEnabled(self):
        return self.m_debuginfo

    def setDebuginfoEnabled(self, enabled):
        self.m_debuginfo = enabled

    def getRepos(self):
        return self.m_repos

    def addRepo(self, repo):
        self.m_repos.append(repo)

    def getLocked(self):
        return self.m_locked

    def setLocked(self, locked):
        self.m_locked = locked


class BuildResultList:

    def __init__(self, xml=None):

        if xml:
            self.parse(xml)
        else:
            self.reset()

    def reset(self):

        # checksum identifying the status of the package
        self.m_checksum = ""
        self.m_results = []

    def parse(self, xml):

        self.reset()

        # this is a list of
        #    <result project="" ...><status .../></result>
        # elements

        tree = et.fromstring(xml)

        if tree.tag != "resultlist":
            raise Exception(f"Getting build results failed:\n{xml}")

        self.m_checksum = tree.attrib.get("state", "")

        for el in tree:
            self.m_results.append(BuildResult(el))

    def getResults(self):
        return self.m_results

    def getNumResults(self):
        return len(self.m_results)

    def getChecksum(self):
        return self.m_checksum

    def getTable(self):
        """Returns a formatted, aligned ASCII table describing the
        build results."""
        rows = []
        num_cols = 3

        for res in self.m_results:
            pkgs = res.getPackages()
            row = [
                res.getRepository(),
                res.getArch()
            ]
            if len(pkgs) > 1:
                print("Warning: build result for more than one package")
                # use project code
                row.append(res.getCode())
            else:
                row.append(pkgs[0][1])
            rows.append(row)

        max_cols = []

        for i in range(num_cols):
            maxlen = max([len(row[i]) for row in rows])
            max_cols.append(maxlen + 1)

        ret = ""

        for row in rows:
            for i in range(num_cols):
                ret += row[i].ljust(max_cols[i]) + " "
            ret += "\n"

        return ret


class BuildResult:

    def __init__(self, xml_node=None):
        if xml_node:
            self.parse(xml_node)
        else:
            self.reset()

    def reset(self):
        self.m_project = ""
        self.m_repository = ""
        self.m_arch = ""
        # these is the overall project code/state
        self.m_code = ""
        self.m_state = ""
        self.m_packages = []

    def getProject(self):
        return self.m_project

    def getRepository(self):
        return self.m_repository

    def getArch(self):
        return self.m_arch

    def getCode(self):
        return self.m_code

    def getState(self):
        return self.m_state

    def getPackages(self):
        """Returns a list of packages consisting of tuples of
        (package, code) strings."""
        return self.m_packages

    def parse(self, xml_node):
        """Parses a buildresult meta XML string and fills the object's
        values from it."""

        self.reset()

        if xml_node.tag != "result":
            raise Exception("Not a build result node")

        attrs = xml_node.attrib

        self.m_project = attrs.get("project", "")
        self.m_repository = attrs.get("repository", "")
        self.m_arch = attrs.get("arch", "")
        self.m_code = attrs.get("code", "")
        self.m_state = attrs.get("state", "")

        for status in xml_node:
            if status.tag != "status":
                continue

            pkgattrs = status.attrib
            pkg = pkgattrs.get("package", "")
            code = pkgattrs.get("code", "")

            if not pkg or not code:
                continue

            self.m_packages.append((pkg, code))
