import oscfs.types


class RefreshTrigger(oscfs.types.TriggerNode):
    """This type represents a refresh trigger file that can be used to
    mark the cache of a package of complete project as stale."""

    def __init__(self, parent, name, target):
        super(RefreshTrigger, self).__init__(parent, name)

    def triggered(self, value):
        if not value:
            return

        # this invalidates the cache of the package or project in a
        # recursive fashion
        self.m_parent.m_parent.setCacheStale()
