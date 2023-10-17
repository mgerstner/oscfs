import os
import sys

our_uid = None
our_gid = None


def getUid():
    global our_uid

    if our_uid is None:
        our_uid = os.getuid()

    return our_uid


def getGid():
    global our_gid

    if our_gid is None:
        our_gid = os.getgid()

    return our_gid


def getFriendlyException(ex):
    """Returns a friendly description of the currently active exception
    as a one-line string. This only works when called from an except:
    block."""
    import traceback

    _, _, tb = sys.exc_info()
    fn, ln, _, _ = traceback.extract_tb(tb)[-1]
    return "Exception in {}:{}: {}".format(fn, ln, str(ex))


def getExceptionTrace(ex):
    import sys
    import traceback
    _, _, tb = sys.exc_info()
    first = True
    ret = []
    for frame in traceback.extract_tb(tb):
        fn, ln, func, ln_text = frame

        ln = str(ln).rjust(4)

        if first:
            line = f"{fn}:{ln} {func}(): {str(ex)}"
            ret.append(line)
            first = False
        else:
            ret.append(f"{fn}:{ln} {func}()")

    return '\n'.join(ret)


def printException(ex):
    """Prints the currently active exception in a friendly, compact
    way to stderr."""
    print(getFriendlyException(ex), file=sys.stderr)
