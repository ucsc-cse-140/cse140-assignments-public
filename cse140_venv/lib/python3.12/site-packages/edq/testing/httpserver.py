import glob
import http.server
import logging
import os
import threading
import time
import typing

import requests

import edq.testing.unittest
import edq.util.dirent
import edq.util.json
import edq.util.net

_logger = logging.getLogger(__name__)

SERVER_THREAD_START_WAIT_SEC: float = 0.02
SERVER_THREAD_REAP_WAIT_SEC: float = 0.15

class HTTPTestServer():
    """
    An HTTP server meant for testing.
    This server is generally meant to already know about all the requests that will be made to it,
    and all the responses it should make in reaction to those respective requests.
    This allows the server to respond very quickly, and makes it ideal for testing.
    This makes it easy to mock external services for testing.

    If a request is not found in the predefined requests,
    then missing_request() will be called.
    If a response is still not available (indicated by a None return from missing_request()),
    then an error will be raised.
    """

    def __init__(self,
            port: typing.Union[int, None] = None,
            match_options: typing.Union[typing.Dict[str, typing.Any], None] = None,
            default_match_options: bool = True,
            verbose: bool = False,
            raise_on_404: bool = False,
            **kwargs: typing.Any) -> None:
        self.port: typing.Union[int, None] = port
        """
        The active port this server is using.
        If None, then a random port will be chosen when the server is started and this field will be populated.
        """

        self._http_server: typing.Union[http.server.HTTPServer, None] = None
        """ The HTTP server listening for connections. """

        self._thread: typing.Union[threading.Thread, None] = None
        """ The thread running the HTTP server. """

        self._run_lock: threading.Lock = threading.Lock()
        """ A lock that the server holds while running. """

        self.verbose: bool = verbose
        """ Log more information. """

        self.raise_on_404: bool = raise_on_404
        """ Raise an exception when no exchange is matched (instead of a 404 error). """

        self._exchanges: typing.Dict[str, typing.Dict[typing.Union[str, None], typing.Dict[str, typing.List[edq.util.net.HTTPExchange]]]] = {}
        """
        The HTTP exchanges (requests+responses) that this server knows about.
        Exchanges are stored in layers to help make errors for missing requests easier.
        Exchanges are stored as: {url_path: {anchor: {method: [exchange, ...]}, ...}, ...}.
        """

        if (match_options is None):
            match_options = {}

        if (default_match_options):
            if ('headers_to_skip' not in match_options):
                match_options['headers_to_skip'] = []

            match_options['headers_to_skip'] += edq.util.net.DEFAULT_EXCHANGE_IGNORE_HEADERS

        self.match_options: typing.Dict[str, typing.Any] = match_options.copy()
        """ Options to use when matching HTTP exchanges. """

    def get_exchanges(self) -> typing.List[edq.util.net.HTTPExchange]:
        """
        Get a shallow list of all the exchanges in this server.
        Ordering is not guaranteed.
        """

        exchanges = []

        for url_exchanges in self._exchanges.values():
            for anchor_exchanges in url_exchanges.values():
                for method_exchanges in anchor_exchanges.values():
                    exchanges += method_exchanges

        return exchanges

    def start(self) -> None:
        """ Start this server in a thread and return the port. """

        class NestedHTTPHandler(_TestHTTPHandler):
            """ An HTTP handler as a nested class to bind this server object to the handler. """

            _server = self
            _verbose = self.verbose
            _raise_on_404 = self.raise_on_404
            _missing_request_func = self.missing_request

        if (self.port is None):
            self.port = edq.util.net.find_open_port()

        self._http_server = http.server.HTTPServer(('', self.port), NestedHTTPHandler)

        if (self.verbose):
            _logger.info("Starting test server on port %d.", self.port)

        # Use a barrier to ensure that the server thread has started.
        server_startup_barrier = threading.Barrier(2)

        def _run_server(server: 'HTTPTestServer', server_startup_barrier: threading.Barrier) -> None:
            server_startup_barrier.wait()

            if (server._http_server is None):
                raise ValueError('Server was not initialized.')

            # Run the server within the run lock context.
            with server._run_lock:
                server._http_server.serve_forever(poll_interval = 0.01)
                server._http_server.server_close()

            if (self.verbose):
                _logger.info("Stopping test server.")

        self._thread = threading.Thread(target = _run_server, args = (self, server_startup_barrier))
        self._thread.start()

        # Wait for the server to startup.
        server_startup_barrier.wait()
        time.sleep(SERVER_THREAD_START_WAIT_SEC)

    def wait_for_completion(self) -> None:
        """
        Block until the server is not running.
        If called while the server is not running, this will return immediately.
        This function will handle keyboard interrupts (Ctrl-C).
        """

        try:
            with self._run_lock:
                pass
        except KeyboardInterrupt:
            self.stop()
            self.wait_for_completion()

    def start_and_wait(self) -> None:
        """ Start the server and block until it is done. """

        self.start()
        self.wait_for_completion()

    def stop(self) -> None:
        """ Stop this server. """

        self.port = None

        if (self._http_server is not None):
            self._http_server.shutdown()
            self._http_server = None

        if (self._thread is not None):
            if (self._thread.is_alive()):
                self._thread.join(SERVER_THREAD_REAP_WAIT_SEC)

            self._thread = None

    def missing_request(self, query: edq.util.net.HTTPExchange) -> typing.Union[edq.util.net.HTTPExchange, None]:
        """
        Provide the server (specifically, child classes) one last chance to resolve an incoming HTTP request
        before the server raises an exception.
        Usually exchanges are loaded from disk, but technically a server can resolve all requests with this method.

        Exchanges returned from this method are not cached/saved.
        """

        return None

    def modify_exchanges(self, exchanges: typing.List[edq.util.net.HTTPExchange]) -> typing.List[edq.util.net.HTTPExchange]:
        """
        Modify any exchanges before they are saved into this server's cache.
        The returned exchanges will be saved in this server's cache.

        This method may be called multiple times with different collections of exchanges.
        """

        return exchanges

    def lookup_exchange(self,
            query: edq.util.net.HTTPExchange,
            match_options: typing.Union[typing.Dict[str, typing.Any], None] = None,
            ) -> typing.Tuple[typing.Union[edq.util.net.HTTPExchange, None], typing.Union[str, None]]:
        """
        Lookup the query exchange to see if it exists in this server.
        If a match exists, the matching exchange (likely a full version of the query) will be returned along with None.
        If a match does not exist, a None will be returned along with a message indicating how the query missed
        (e.g., the URL was matched, but the method was not).
        """

        if (match_options is None):
            match_options = {}

        hint_display = query.url_path
        target: typing.Any = self._exchanges

        if (query.url_path not in target):
            return None, f"Could not find matching URL path for '{hint_display}'."

        hint_display = query.url_path
        if (query.url_anchor is not None):
            hint_display = f"{query.url_path}#{query.url_anchor}"

        target = target[query.url_path]

        if (query.url_anchor not in target):
            return None, f"Found URL path, but could not find matching anchor for '{hint_display}'."

        hint_display = f"{hint_display} ({query.method})"
        target = target[query.url_anchor]

        if (query.method not in target):
            return None, f"Found URL, but could not find matching method for '{hint_display}'."

        params = list(sorted(query.parameters.keys()))
        hint_display = f"{hint_display}, (param keys = {params})"
        target = target[query.method]

        full_match_options = self.match_options.copy()
        full_match_options.update(match_options)

        hints = []
        matches = []

        for (i, exchange) in enumerate(target):
            match, hint = exchange.match(query, **full_match_options)
            if (match):
                matches.append(exchange)
                continue

            # Collect hints for non-matches.
            label = exchange.source_path
            if (label is None):
                label = str(i)

            hints.append(f"{label}: {hint}")

        if (len(matches) == 1):
            # Found exactly one match.
            return matches[0], None

        if (len(matches) > 1):
            # Found multiple matches.
            match_paths = list(sorted([match.source_path for match in matches]))
            return None, f"Found multiple matching exchanges for '{hint_display}': {match_paths}."

        # Found no matches.
        return None, f"Found matching URL and method, but could not find matching headers/params for '{hint_display}' (non-matching hints: {hints})."

    def load_exchange(self, exchange: edq.util.net.HTTPExchange) -> None:
        """ Load an exchange into this server. """

        if (exchange is None):
            raise ValueError("Cannot load a None exchange.")

        target: typing.Any = self._exchanges
        if (exchange.url_path not in target):
            target[exchange.url_path] = {}

        target = target[exchange.url_path]
        if (exchange.url_anchor not in target):
            target[exchange.url_anchor] = {}

        target = target[exchange.url_anchor]
        if (exchange.method not in target):
            target[exchange.method] = []

        target = target[exchange.method]
        target.append(exchange)

    def load_exchange_file(self, path: str) -> None:
        """
        Load an exchange from a file.
        This will also handle setting the exchanges source path and resolving the exchange's paths.
        """

        self.load_exchange(edq.util.net.HTTPExchange.from_path(path))

    def load_exchanges_dir(self, base_dir: str, extension: str = edq.util.net.DEFAULT_HTTP_EXCHANGE_EXTENSION) -> None:
        """ Load all exchanges found (recursively) within a directory. """

        paths = list(sorted(glob.glob(os.path.join(base_dir, "**", f"*{extension}"), recursive = True)))
        for path in paths:
            self.load_exchange_file(path)

@typing.runtime_checkable
class MissingRequestFunction(typing.Protocol):
    """
    A function that can be used to create an exchange when none was found.
    This is often the last resort when a test server cannot find an exchange matching a request.
    """

    def __call__(self,
            query: edq.util.net.HTTPExchange,
            ) -> typing.Union[edq.util.net.HTTPExchange, None]:
        """
        Create an exchange for the given query or return None.
        """

class _TestHTTPHandler(http.server.BaseHTTPRequestHandler):
    _server: typing.Union[HTTPTestServer, None] = None
    """ The test server this handler is being used for. """

    _verbose: bool = False
    """ Log more interactions. """

    _raise_on_404: bool = True
    """ Raise an exception when no exchange is matched (instead of a 404 error). """

    _missing_request_func: typing.Union[MissingRequestFunction, None] = None
    """ A fallback to get an exchange before resulting in a 404. """

    # Quiet logs.
    def log_message(self, format: str, *args: typing.Any) -> None:  # pylint: disable=redefined-builtin
        pass

    def do_DELETE(self) -> None:  # pylint: disable=invalid-name
        """ A handler for DELETE requests. """

        self._do_request('DELETE')

    def do_GET(self) -> None:  # pylint: disable=invalid-name
        """ A handler for GET requests. """

        self._do_request('GET')

    def do_HEAD(self) -> None:  # pylint: disable=invalid-name
        """ A handler for HEAD requests. """

        self._do_request('HEAD')

    def do_OPTIONS(self) -> None:  # pylint: disable=invalid-name
        """ A handler for OPTIONS requests. """

        self._do_request('OPTIONS')

    def do_PATCH(self) -> None:  # pylint: disable=invalid-name
        """ A handler for PATCH requests. """

        self._do_request('PATCH')

    def do_POST(self) -> None:  # pylint: disable=invalid-name
        """ A handler for POST requests. """

        self._do_request('POST')

    def do_PUT(self) -> None:  # pylint: disable=invalid-name
        """ A handler for PUT requests. """

        self._do_request('PUT')

    def _do_request(self, method: str) -> None:
        """ A common handler for multiple types of requests. """

        if (self._server is None):
            raise ValueError("Server has not been initialized.")

        if (self._verbose):
            _logger.debug("Incoming %s request: '%s'.", method, self.path)

        # Parse data from the request url and body.
        request_data, request_files = edq.util.net.parse_request_data(self.path, self.headers, self.rfile)

        # Construct file info objects from the raw files.
        files = [edq.util.net.FileInfo(name = name, content = content) for (name, content) in request_files.items()]

        exchange, hint = self._get_exchange(method, parameters = request_data, files = files)  # type: ignore[arg-type]

        if (exchange is None):
            code = http.HTTPStatus.NOT_FOUND.value
            headers = {}
            payload = hint
        else:
            code = exchange.response_code
            headers = exchange.response_headers
            payload = exchange.response_body

        if (payload is None):
            payload = ''

        self.send_response(code)
        for (key, value) in headers.items():
            self.send_header(key, value)
        self.end_headers()

        self.wfile.write(payload.encode(edq.util.dirent.DEFAULT_ENCODING))

    def _get_exchange(self, method: str,
            parameters: typing.Union[typing.Dict[str, typing.Any], None] = None,
            files: typing.Union[typing.List[typing.Union[edq.util.net.FileInfo, typing.Dict[str, str]]], None] = None,
            ) -> typing.Tuple[typing.Union[edq.util.net.HTTPExchange, None], typing.Union[str, None]]:
        """ Get the matching exchange or raise an error. """

        if (self._server is None):
            raise ValueError("Server has not been initialized.")

        query = edq.util.net.HTTPExchange(method = method,
                url = self.path,
                url_anchor = self.headers.get(edq.util.net.ANCHOR_HEADER_KEY, None),
                headers = self.headers,  # type: ignore[arg-type]
                parameters = parameters, files = files)

        exchange, hint = self._server.lookup_exchange(query)

        if ((exchange is None) and (self._missing_request_func is not None)):
            exchange = self._missing_request_func(query)  # pylint: disable=not-callable

        if ((exchange is None) and self._raise_on_404):
            raise ValueError(f"Failed to lookup exchange: '{hint}'.")

        return exchange, hint

class HTTPServerTest(edq.testing.unittest.BaseTest):
    """
    A unit test class that requires a testing HTTP server to be running.
    """

    server_key: str = ''
    """
    A key to indicate which test server this test class is using.
    By default all test classes share the same server,
    but child classes can set this if they want to control who is using the same server.
    If `tear_down_server` is true, then the relevant server will be stopped (and removed) on a call to tearDownClass(),
    which happens after a test class is complete.
    """

    tear_down_server: bool = True
    """
    Tear down the relevant test server in tearDownClass().
    If set to false then the server will never get torn down,
    but can be shared between child test classes.
    """

    skip_test_exchanges_base: bool = False
    """ Skip test_exchanges_base. """

    override_server_url: typing.Union[str, None] = None
    """ If set, return this URL from get_server_url(). """

    _servers: typing.Dict[str, HTTPTestServer] = {}
    """ The active test servers. """

    _complete_exchange_tests: typing.Set[str] = set()
    """
    Keep track of the servers (by key) that have run their test_exchanges_base.
    This test should only be run once per server.
    """

    _child_class_setup_called: bool = False
    """ Keep track if the child class setup was called. """

    @classmethod
    def setUpClass(cls) -> None:
        if (not cls._child_class_setup_called):
            cls.child_class_setup()
            cls._child_class_setup_called = True

        if (cls.server_key in cls._servers):
            return

        server = HTTPTestServer()
        cls._servers[cls.server_key] = server

        cls.setup_server(server)
        server.start()
        cls.post_start_server(server)

    @classmethod
    def tearDownClass(cls) -> None:
        if (cls.server_key not in cls._servers):
            return

        server = cls.get_server()

        if (cls.tear_down_server):
            server.stop()
            del cls._servers[cls.server_key]
            cls._complete_exchange_tests.discard(cls.server_key)

    @classmethod
    def suite_cleanup(cls) -> None:
        """ Cleanup all test servers. """

        for server in cls._servers.values():
            server.stop()

        cls._servers.clear()

    @classmethod
    def get_server(cls) -> HTTPTestServer:
        """ Get the current HTTP server or raise if there is no server. """

        server = cls._servers.get(cls.server_key, None)
        if (server is None):
            raise ValueError("Server has not been initialized.")

        return server

    @classmethod
    def child_class_setup(cls) -> None:
        """ This function is the recommended time for child classes to set any configuration. """

    @classmethod
    def setup_server(cls, server: HTTPTestServer) -> None:
        """ An opportunity for child classes to configure the test server before starting it. """

    @classmethod
    def post_start_server(cls, server: HTTPTestServer) -> None:
        """ An opportunity for child classes to work with the server after it has been started, but before any tests. """

    @classmethod
    def get_server_url(cls) -> str:
        """ Get the URL for this test's test server. """

        if (cls.override_server_url is not None):
            return cls.override_server_url

        server = cls.get_server()

        if (server.port is None):
            raise ValueError("Test server port has not been set.")

        return f"http://127.0.0.1:{server.port}"

    def assert_exchange(self, request: edq.util.net.HTTPExchange, response: edq.util.net.HTTPExchange,
            base_url: typing.Union[str, None] = None,
            ) -> requests.Response:
        """
        Assert that the result of making the provided request matches the provided response.
        The same HTTPExchange may be supplied for both the request and response.
        By default, the server's URL will be used as the base URL.
        The full response will be returned (if no assertion is raised).
        """

        server = self.get_server()

        if (base_url is None):
            base_url = self.get_server_url()

        full_response, body = request.make_request(base_url, raise_for_status = True, **server.match_options)

        match, hint = response.match_response(full_response, override_body = body, **server.match_options)
        if (not match):
            raise AssertionError(f"Exchange does not match: '{hint}'.")

        return full_response

    def test_exchanges_base(self) -> None:
        """ Test making a request with each of the loaded exchanges. """

        # Check if this test has already been run for this server.
        if (self.server_key in self._complete_exchange_tests):
            # Don't skip the test (which will show up in the test output).
            # Instead, just return.
            return

        if (self.skip_test_exchanges_base):
            self.skipTest('test_exchanges_base has been manually skipped.')

        self._complete_exchange_tests.add(self.server_key)

        server = self.get_server()

        for (i, exchange) in enumerate(server.get_exchanges()):
            base_name = exchange.get_url()
            if (exchange.source_path is not None):
                base_name = os.path.splitext(os.path.basename(exchange.source_path))[0]

            with self.subTest(msg = f"Case {i} ({base_name}):"):
                self.assert_exchange(exchange, exchange)
