from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Generator
from urllib.parse import urlparse, urlunparse
from urllib.request import Request

import requests
from locust import User
from locust.clients import LocustHttpAdapter, absolute_http_url_regexp, ResponseContextManager, LocustResponse
from requests.auth import HTTPBasicAuth
from requests.exceptions import MissingSchema, InvalidSchema, InvalidURL, RequestException
from urllib3 import PoolManager

logger = logging.getLogger(__name__)

from locust.exception import LocustError

logger = logging.getLogger(__name__)


class SingletonRequestsClient(requests.Session):
    globalClient = None
    initialized = False

    def __new__(cls, *args, **k):
        if cls.globalClient is None:
            cls.globalClient = super().__new__(cls)
        return cls.globalClient

    def __init__(self, *args, **k):
        if not self.__class__.initialized:
            super().__init__(*args, **k)
            self.__class__.initialized = True


class HttpSession(SingletonRequestsClient):
    pool_connections = 10
    pool_maxsize = 10

    """
    Class for performing web requests and holding (session-) cookies between requests (in order
    to be able to log in and out of websites). Each request is logged so that locust can display
    statistics.

    This is a slightly extended version of `python-request <http://python-requests.org>`_'s
    :py:class:`requests.Session` class and mostly this class works exactly the same. However
    the methods for making requests (get, post, delete, put, head, options, patch, request)
    can now take a *url* argument that's only the path part of the URL, in which case the host
    part of the URL will be prepended with the HttpSession.base_url which is normally inherited
    from a User class' host attribute.

    Each of the methods for making requests also takes two additional optional arguments which
    are Locust specific and doesn't exist in python-requests. These are:

    :param name: (optional) An argument that can be specified to use as label in Locust's statistics instead of the URL path.
                 This can be used to group different URL's that are requested into a single entry in Locust's statistics.
    :param catch_response: (optional) Boolean argument that, if set, can be used to make a request return a context manager
                           to work as argument to a with statement. This will allow the request to be marked as a fail based on the content of the
                           response, even if the response code is ok (2xx). The opposite also works, one can use catch_response to catch a request
                           and then mark it as successful even if the response code was not (i.e 500 or 404).
    """

    def __init__(self, base_url, request_event, user, *args, pool_manager: PoolManager | None = None, **kwargs):
        super().__init__(*args, **kwargs)

        self.base_url = base_url
        self.request_event = request_event
        self.user = user

        # User can group name, or use the group context manager to gather performance statistics under a specific name
        # This is an alternative to passing in the "name" parameter to the requests function
        self.request_name: str | None = None

        # Check for basic authentication
        parsed_url = urlparse(self.base_url)
        if parsed_url.username and parsed_url.password:
            netloc = parsed_url.hostname
            if parsed_url.port:
                netloc += ":%d" % parsed_url.port

            # remove username and password from the base_url
            self.base_url = urlunparse(
                (parsed_url.scheme, netloc, parsed_url.path, parsed_url.params, parsed_url.query, parsed_url.fragment)
            )
            # configure requests to use basic auth
            self.auth = HTTPBasicAuth(parsed_url.username, parsed_url.password)

        locustHttpAdapter = LocustHttpAdapter(
            pool_manager=pool_manager,
            pool_connections=self.pool_connections,
            pool_maxsize=self.pool_maxsize,
        )
        self.mount("https://", locustHttpAdapter)
        self.mount("http://", locustHttpAdapter)

    def _build_url(self, path):
        """prepend url with hostname unless it's already an absolute URL"""
        if absolute_http_url_regexp.match(path):
            return path
        else:
            return f"{self.base_url}{path}"

    @contextmanager
    def rename_request(self, name: str) -> Generator[None, None, None]:
        """Group requests using the "with" keyword"""

        self.request_name = name
        try:
            yield
        finally:
            self.request_name = None

    def request(self, method, url, name=None, catch_response=False, context={}, **kwargs):
        """
        Constructs and sends a :py:class:`requests.Request`.
        Returns :py:class:`requests.Response` object.

        :param method: method for the new :class:`Request` object.
        :param url: URL for the new :class:`Request` object.
        :param name: (optional) An argument that can be specified to use as label in Locust's statistics instead of the URL path.
          This can be used to group different URL's that are requested into a single entry in Locust's statistics.
        :param catch_response: (optional) Boolean argument that, if set, can be used to make a request return a context manager
          to work as argument to a with statement. This will allow the request to be marked as a fail based on the content of the
          response, even if the response code is ok (2xx). The opposite also works, one can use catch_response to catch a request
          and then mark it as successful even if the response code was not (i.e 500 or 404).
        :param params: (optional) Dictionary or bytes to be sent in the query string for the :class:`Request`.
        :param data: (optional) Dictionary or bytes to send in the body of the :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the :class:`Request`.
        :param files: (optional) Dictionary of ``'filename': file-like-objects`` for multipart encoding upload.
        :param auth: (optional) Auth tuple or callable to enable Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How long in seconds to wait for the server to send data before giving up, as a float,
            or a (`connect timeout, read timeout <user/advanced.html#timeouts>`_) tuple.
        :type timeout: float or tuple
        :param allow_redirects: (optional) Set to True by default.
        :type allow_redirects: bool
        :param proxies: (optional) Dictionary mapping protocol to the URL of the proxy.
        :param stream: (optional) whether to immediately download the response content. Defaults to ``False``.
        :param verify: (optional) if ``True``, the SSL cert will be verified. A CA_BUNDLE path can also be provided.
        :param cert: (optional) if String, path to ssl client cert file (.pem). If Tuple, ('cert', 'key') pair.
        """

        # if group name has been set and no name parameter has been passed in; set the name parameter to group_name
        if self.request_name and not name:
            name = self.request_name

        # prepend url with hostname unless it's already an absolute URL
        url = self._build_url(url)

        start_time = time.time()
        start_perf_counter = time.perf_counter()
        response = self._send_request_safe_mode(method, url, **kwargs)
        response_time = (time.perf_counter() - start_perf_counter) * 1000

        request_before_redirect = (response.history and response.history[0] or response).request
        url = request_before_redirect.url

        if not name:
            name = request_before_redirect.path_url

        if self.user:
            context = {**self.user.context(), **context}

        # store meta data that is used when reporting the request to locust's statistics
        request_meta = {
            "request_type": method,
            "response_time": response_time,
            "name": name,
            "context": context,
            "response": response,
            "exception": None,
            "start_time": start_time,
            "url": url,
        }

        # get the length of the content, but if the argument stream is set to True, we take
        # the size from the content-length header, in order to not trigger fetching of the body
        if kwargs.get("stream", False):
            request_meta["response_length"] = int(response.headers.get("content-length") or 0)
        else:
            request_meta["response_length"] = len(response.content or b"")

        if catch_response:
            return ResponseContextManager(response, request_event=self.request_event, request_meta=request_meta)
        else:
            with ResponseContextManager(response, request_event=self.request_event, request_meta=request_meta):
                pass
            return response

    def _send_request_safe_mode(self, method, url, **kwargs):
        """
        Send an HTTP request, and catch any exception that might occur due to connection problems.

        Safe mode has been removed from requests 1.x.
        """
        try:
            return super().request(method, url, **kwargs)
        except (MissingSchema, InvalidSchema, InvalidURL):
            raise
        except RequestException as e:
            r = LocustResponse()
            r.error = e
            r.status_code = 0  # with this status_code, content returns None
            r.request = Request(method, url).prepare()
            return r


class RequestsUser(User):
    """
    Represents an HTTP "user" which is to be spawned and attack the system that is to be load tested.

    The behaviour of this user is defined by its tasks. Tasks can be declared either directly on the
    class by using the :py:func:`@task decorator <locust.task>` on methods, or by setting
    the :py:attr:`tasks attribute <locust.User.tasks>`.

    This class creates a *client* attribute on instantiation which is an HTTP client with support
    for keeping a user session between requests.
    """

    abstract = True
    """If abstract is True, the class is meant to be subclassed, and users will not choose this locust during a test"""

    pool_manager: PoolManager | None = None
    """Connection pool manager to use. If not given, a new manager is created per single user."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.host is None:
            raise LocustError(
                "You must specify the base host. Either in the host attribute in the User class, or on the command line using the --host option."
            )

        self.client = HttpSession(
            base_url=self.host,
            request_event=self.environment.events.request,
            user=self,
            pool_manager=self.pool_manager,
        )

        # self.client.pool_connections = 100
        # self.client.pool_maxsize = 100
        """
        Instance of HttpSession that is created upon instantiation of Locust.
        The client supports cookies, and therefore keeps the session between HTTP requests.
        """
        self.client.trust_env = False
