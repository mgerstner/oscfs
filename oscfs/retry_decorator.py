import urllib


def _logRetry(ex):
    from oscfs.misc import getExceptionTrace
    from sys import stderr
    trace = getExceptionTrace(ex)
    print(f"HTTP status 503 service unavailable transparent retry occured:\n{trace}\n", file=stderr)


# OBS randomly fails with HTTP 503 "service unavailable".
#
# This can happen both via HTTPError exceptions or via a document of
# this form returned instead of XML:
#
# <!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">\n<html><head>\n<title>503 Service Unavailable</title>\n</head><body>\n<h1>Service Unavailable</h1>\n<p>The server is temporarily unable to service your\nrequest due to maintenance downtime or capacity\nproblems. Please try again later.</p>\n<p>Additionally, a 503 Service Unavailable\nerror was encountered while trying to use an ErrorDocument to handle the request.</p>\n</body></html>
#
# There currently seems no easy way to solve this on the server end, so
# we are required to transparently retry in this case. Ugly.
#
# This is a function decorator that easily allows to add transparent retry
# behaviour to affected OBS API calls.
def transparent_retry(expect_xml=False):

    def inner_decorator(func):

        def retry_loop(*args, **kwargs):
            while True:
                try:
                    ret = func(*args, **kwargs)
                except urllib.error.HTTPError as e:
                    if e.code == 503:
                        _logRetry(e)
                        continue
                    # on any other error simply re-raise the exception to the
                    # original caller
                    raise

                if expect_xml:
                    try:
                        text = ret.decode()
                    except Exception:
                        text = ret

                    # heuristic to detect this, the osc module seems to fail to
                    # detect the error status, or there is none sent by the server.
                    if text.lower().find("503 service unavailable") != -1:
                        try:
                            raise Exception("503 transparent retry (xml)")
                        except Exception as e:
                            _logRetry(e)
                        continue

                return ret

        return retry_loop

    return inner_decorator
