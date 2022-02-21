import oscfs.types


class ObsFile(oscfs.types.Node):
    """This type represents a regular file in an OBS package which can
    return actual file content via read()."""

    def __init__(self, parent, name, size, mtime, revision=None):

        super(ObsFile, self).__init__(parent, name)
        self.m_revision = revision

        stat = self.getStat()
        stat.setModTime(mtime)
        stat.setSize(size)

    def update(self):

        obs = self.getRoot().getObs()

        self.m_data = obs.getSourceFileContent(
            self.getProject().getName(),
            self.getPackage().getName(),
            self.getName(),
            revision=self.m_revision
        )

    def read(self, length, offset):

        self.updateIfNeeded()

        return self.m_data[offset:offset + length]
