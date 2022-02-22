# std. modules
import urllib.request
import http.client

# This urlopen wrapper makes http connection reuse possible.
#
# The osc module does not support this. The osc.core.http_request is the
# central function for processing osc request. It uses urllib2.urlopen() to
# establish an http(s) connection for each invocation.
#
# For the purposes of our file system this is bad for performance, because
# we'll need to issue a lot of requests to the same server over and over
# again. It adds a lot of overhead.
#
# The urllib2 does not support connection reuse, sadly. httplib supports it,
# however. The purpose of this wrapper is to transparently replace
# urllib2.urlopen() in a way that only osc.* requests are working correctly
# and are using a reused httplib connection instead.
#
# This is quite hacky. osc.core.http_request passes an urllib2.Request object
# containing possible headers and what not to urllib2.urlopen(). This can't be
# passed directly to httplib. Also the http basic authentication done by
# osc.core/osc.conf is tied to the urrlib2 data structures and API.
#
# Therefore the basic authentication is remodelled here. This is a minimal
# approach that may break easily ... all for the sake of performance. The
# right approach would, of course, be to implement connection reuse on the osc
# side instead.


class UrlopenWrapper:

    def __init__(self):

        self.m_connections = {}
        self._setupWrapper()

    def _setupWrapper(self):
        self.m_orig_urlopen = urllib.request.urlopen
        urllib.request.urlopen = self._wrapper

    def _wrapper(self, req, data=None):
        import base64
        import osc.conf

        if hasattr(req, "get_type"):
            # python2 API
            proto, host = req.get_type(), req.get_host()
        else:
            # python3 API
            proto, host = req.type, req.host

        api_key = "{}://{}".format(proto, host)
        api_conf = osc.conf.config["api_host_options"].get(api_key, None)

        # add user/password, but only if it's an encrypted connection
        if proto == 'https' and api_conf:
            userpw = "{}:{}".format(
                api_conf["user"], api_conf["pass"]
            )
            auth = "Basic {}".format(
                base64.b64encode(userpw.encode()).decode()
            )
            req.add_unredirected_header("Authorization", auth)

        connection = self._getConnection(proto, host)
        retries = 0
        while True:
            try:
                connection.request(
                    req.get_method(),
                    req.get_full_url(),
                    # get_data() is the Python2 API
                    req.get_data() if hasattr(req, "get_data") else req.data,
                    dict(req.header_items())
                )

                resp = connection.getresponse()

                if resp.status == 401:
                    # urllib2.urlopen seems to implicitly
                    # handle this case, so let's do this,
                    # too
                    raise urllib.request.HTTPError(
                        req.get_full_url(),
                        resp.status,
                        resp.msg,
                        resp.getheaders(),
                        resp.fp
                    )

                return self._extendedResponse(resp)
            except http.client.BadStatusLine:
                # probably an http keep-alive issue
                #
                # reestablish the connection and retry
                connection = self._getConnection(proto, host, renew=True)
                retries += 1

                if retries > 3:
                    # avoid an infinite loop
                    raise

    def _extendedResponse(self, resp):
        """This function returns a httplib response object that
        matches the expectations of the osc module."""
        import functools

        def responseReadlines(resp):
            return resp.read().splitlines()

        def responseInfo(resp):
            return resp

        def responseGet(header, resp):
            return resp.getheader(header)

        # the urrlib result allows readlines() to be called so we need
        # to cover that, too.
        resp.readlines = functools.partial(responseReadlines, resp=resp)
        # info() on urrlib2 objects returns a HTTPMessage object which
        # we need to emulate
        resp.info = functools.partial(responseInfo, resp=resp)
        # emulate info().get('My-Header') to retrieve headers
        resp.get = functools.partial(responseGet, resp=resp)

        return resp

    def _getConnection(self, proto, host, renew=False):
        key = (proto, host)

        if renew:
            return self._addConnection(key)

        try:
            return self.m_connections[key]
        except KeyError:
            return self._addConnection(key)

    def _addConnection(self, key):
        proto, host = key

        connection = self.setupConnection(proto, host)

        self.m_connections[key] = connection
        return connection

    def setupConnection(self, proto, host):
        if proto == "https":
            Connection = http.client.HTTPSConnection
        elif proto == "http":
            Connection = http.client.HTTPConnection
        else:
            raise Exception("Unsupported urlopen protocol " + str(proto))

        connection = Connection(host)

        return connection


urlopen_wrapper = UrlopenWrapper()
