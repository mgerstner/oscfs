import oscfs.types
import oscfs.obs
import oscfs.package
import oscfs.refreshtrigger


class Project(oscfs.types.DirNode):
    """This type represents a project node of the file system containing
    all individual OBS packages as childs.
    """

    def __init__(self, parent, name):

        self.m_api_name = ".oscfs"
        super(Project, self).__init__(parent, name)

    def _addApiDir(self):

        api_name = self.m_api_name
        self.m_entries[api_name] = PrjApiDir(self, api_name)

    def getApiDir(self):
        return self.m_entries[self.m_api_name]

    def update(self):
        obs = self.getRoot().getObs()

        project = self.getName()

        for package in obs.getPackageList(project):

            if package in self.m_entries:
                continue

            self.m_entries[package] = oscfs.package.Package(
                self, package,
                project=self.getName(),
                package=package
            )

        self._addApiDir()


class PrjApiDir(oscfs.types.DirNode):
    """This type provides access to additional meta data for a project.
    This is just the root directory for this which adds individual file
    and directory nodes tha represent actual API features."""

    def __init__(self, parent, name):

        super(PrjApiDir, self).__init__(parent, name)
        self.m_meta_name = "meta"
        self.m_bugowners_name = "bugowners"
        self.m_maintainers_name = "maintainers"
        self.m_debuginfo_name = "debuginfo"
        self.m_repositories_name = "repositories"
        self.m_locked_name = "locked"
        self.m_readers_name = "readers"
        self.m_refresh_trigger = "refresh"
        self.m_prj_meta = None

    def update(self):
        for name, _type in (
            (self.m_meta_name, MetaNode),
            (self.m_maintainers_name, MaintainersNode),
            (self.m_bugowners_name, BugownersNode),
            (self.m_debuginfo_name, DebuginfoNode),
            (self.m_repositories_name, RepositoriesNode),
            (self.m_locked_name, LockedNode),
            (self.m_readers_name, ReadersNode),
            (self.m_refresh_trigger,
                oscfs.refreshtrigger.RefreshTrigger)
        ):
            try:
                node = _type(self, self.m_parent, name)
                self.m_entries[name] = node
            except Exception as e:
                print("Failed to add", name, "entry:", e)

    def getPrjMeta(self):

        if not self.m_prj_meta:
            obs = self.getRoot().getObs()
            self.m_prj_meta = obs.getProjectMeta(
                self.getProject().getName()
            )

        return self.m_prj_meta

    def getPrjInfo(self):

        return oscfs.obs.ProjectInfo(self.getPrjMeta())


class MetaNode(oscfs.types.FileNode):
    """This node type contains the raw XML metadata of a project."""

    def __init__(self, parent, project, name):

        super(MetaNode, self).__init__(parent, name)
        self.m_project = project

        meta = self.m_parent.getPrjMeta()
        self.setContent(meta)


class ReadersNode(oscfs.types.FileNode):
    """This node returns a list of reader accounts for the project."""

    def __init__(self, parent, project, name):

        super(ReadersNode, self).__init__(parent, name)
        self.m_project = project

        prj_info = self.m_parent.getPrjInfo()
        readers = '\n'.join(prj_info.getReaders())
        self.setContent(readers)


class MaintainersNode(oscfs.types.FileNode):
    """This node returns a list of maintainers for the project."""

    def __init__(self, parent, project, name):

        super(MaintainersNode, self).__init__(parent, name)
        self.m_project = project

        prj_info = self.m_parent.getPrjInfo()
        maintainers = '\n'.join(prj_info.getMaintainers())
        self.setContent(maintainers)


class BugownersNode(oscfs.types.FileNode):
    """This node returns a list of bugowners for the project."""

    def __init__(self, parent, project, name):

        super(BugownersNode, self).__init__(parent, name)
        self.m_project = project

        prj_info = self.m_parent.getPrjInfo()
        bugowners = '\n'.join(prj_info.getBugowners())
        self.setContent(bugowners)


class DebuginfoNode(oscfs.types.FileNode):
    """This node contains a boolean 0/1 value for representing the
    debuginfo setting of the project."""

    def __init__(self, parent, project, name):

        super(DebuginfoNode, self).__init__(parent, name)

        prj_info = self.m_parent.getPrjInfo()
        self.setBoolean(prj_info.getDebuginfoEnabled())


class LockedNode(oscfs.types.FileNode):
    """This node contains a boolean 0/1 value for representing the
    locked status of the project."""

    def __init__(self, parent, project, name):

        super(LockedNode, self).__init__(parent, name)

        prj_info = self.m_parent.getPrjInfo()
        self.setBoolean(prj_info.getLocked())


class RepositoriesNode(oscfs.types.FileNode):
    """This node contains a list of the available repositories for the
    project."""

    def __init__(self, parent, project, name):

        super(RepositoriesNode, self).__init__(parent, name)

        prj_info = self.m_parent.getPrjInfo()

        content = ""
        first = True

        for repo in prj_info.getRepos():
            if first:
                first = False
            else:
                content += "\n"

            content += "# {}\n".format(repo.getName())
            if repo.getProject():
                content += "path: {}/{}\n".format(
                    repo.getProject(),
                    repo.getRepository()
                )
            content += "archs: {}\n".format(
                ", ".join(repo.getArchs())
            )

            if not repo.getEnabled():
                content += "disabled\n"

            rt = repo.getReleaseTarget()

            if rt:
                content += "release target: {}/{}".format(
                    rt[0], rt[1]
                )

                if rt[2]:
                    content += " [manual]"

                content += "\n"

        self.setContent(content)
