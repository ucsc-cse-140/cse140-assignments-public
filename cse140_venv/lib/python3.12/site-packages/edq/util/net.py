"""
Utilities for network and HTTP.
"""

import argparse
import copy
import email.message
import errno
import http.server
import io
import logging
import os
import pathlib
import socket
import time
import typing
import urllib.parse
import urllib3

import requests
import requests_toolbelt.multipart.decoder

import edq.util.dirent
import edq.util.encoding
import edq.util.hash
import edq.util.json
import edq.util.pyimport

_logger = logging.getLogger(__name__)

DEFAULT_START_PORT: int = 30000
DEFAULT_END_PORT: int = 40000
DEFAULT_PORT_SEARCH_WAIT_SEC: float = 0.01

DEFAULT_REQUEST_TIMEOUT_SECS: float = 10.0

DEFAULT_HTTP_EXCHANGE_EXTENSION: str= '.httpex.json'

QUERY_CLIP_LENGTH: int = 100
""" If the filename of an HTTPExhange being saved is longer than this, then clip it. """

ANCHOR_HEADER_KEY: str = 'edq-anchor'
"""
By default, requests made via make_request() will send a header with this key that includes the anchor component of the URL.
Anchors are not traditionally sent in requests, but this will allow exchanges to capture this extra piece of information.
"""

ALLOWED_METHODS: typing.List[str] = [
    'DELETE',
    'GET',
    'HEAD',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
""" Allowed HTTP methods for an HTTPExchange. """

DEFAULT_EXCHANGE_IGNORE_HEADERS: typing.List[str] = [
    'accept',
    'accept-encoding',
    'accept-language',
    'cache-control',
    'connection',
    'content-length',
    'content-security-policy',
    'content-type',
    'cookie',
    'date',
    'dnt',
    'etag',
    'host',
    'link',
    'location',
    'priority',
    'referrer-policy',
    'sec-fetch-dest',
    'sec-fetch-mode',
    'sec-fetch-site',
    'sec-fetch-user',
    'sec-gpc',
    'server',
    'server-timing',
    'set-cookie',
    'upgrade-insecure-requests',
    'user-agent',
    'x-content-type-options',
    'x-download-options',
    'x-permitted-cross-domain-policies',
    'x-rate-limit-remaining',
    'x-request-context-id',
    'x-request-cost',
    'x-runtime',
    'x-session-id',
    'x-xss-protection',
    ANCHOR_HEADER_KEY,
]
"""
By default, ignore these headers during exchange matching.
Some are sent automatically and we don't need to record (like content-length),
and some are additional information we don't need.
"""

_exchanges_out_dir: typing.Union[str, None] = None  # pylint: disable=invalid-name
""" If not None, all requests made via make_request() will be saved as an HTTPExchange in this directory. """

_exchanges_clean_func: typing.Union[str, None] = None  # pylint: disable=invalid-name
"""
If not None, all created exchanges (in HTTPExchange.make_request() and HTTPExchange.from_response()) will use this response modifier.
This function will be called with the response and response body before parsing the rest of the data to build the exchange.
"""

_exchanges_finalize_func: typing.Union[str, None] = None  # pylint: disable=invalid-name
"""
If not None, all created exchanges (in HTTPExchange.make_request()) will use this finalize function.
This function will be called with the created exchange right after construction and before passing back to the caller
(or writing).
"""

_module_makerequest_options: typing.Union[typing.Dict[str, typing.Any], None] = None  # pylint: disable=invalid-name
"""
Module-wide options for requests.request().
These should generally only be used in testing.
"""

@typing.runtime_checkable
class ResponseModifierFunction(typing.Protocol):
    """
    A function that can be used to modify an exchange's response.
    Exchanges can use these functions to normalize their responses before saving.
    """

    def __call__(self,
            response: requests.Response,
            body: str,
            ) -> str:
        """
        Modify the http response.
        Headers may be modified in the response directly,
        while the modified (or same) body must be returned.
        """

class FileInfo(edq.util.json.DictConverter):
    """ Store info about files used in HTTP exchanges. """

    def __init__(self,
            path: typing.Union[str, None] = None,
            name: typing.Union[str, None] = None,
            content: typing.Union[str, bytes, None] = None,
            b64_encoded: bool = False,
            **kwargs: typing.Any) -> None:
        # Normalize the path from POSIX-style to the system's style.
        if (path is not None):
            path = str(pathlib.PurePath(pathlib.PurePosixPath(path)))

        self.path: typing.Union[str, None] = path
        """ The on-disk path to a file. """

        if ((name is None) and (self.path is not None)):
            name = os.path.basename(self.path)

        if (name is None):
            raise ValueError("No name was provided for file.")

        self.name: str = name
        """ The name for this file used in an HTTP request. """

        self.content: typing.Union[str, bytes, None] = content
        """ The contents of this file. """

        self.b64_encoded: bool = b64_encoded
        """ Whether the content is a string encoded in Base64. """

        if ((self.path is None) and (self.content is None)):
            raise ValueError("File must have either path or content specified.")

    def resolve_path(self, base_dir: str, load_file: bool = True) -> None:
        """ Resolve this path relative to the given base dir. """

        if ((self.path is not None) and (not os.path.isabs(self.path))):
            self.path = os.path.abspath(os.path.join(base_dir, self.path))

        if ((self.path is not None) and (self.content is None) and load_file):
            self.content = edq.util.dirent.read_file_bytes(self.path)

    def hash_content(self) -> str:
        """
        Compute a hash for the content present.
        If no content is provided, use the path.
        """

        hash_content = self.content

        if (self.b64_encoded and isinstance(hash_content, str)):
            hash_content = edq.util.encoding.from_base64(hash_content)

        if (hash_content is None):
            hash_content = self.path

        return edq.util.hash.sha256_hex(hash_content)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        data = vars(self).copy()

        # JSON does not support raw bytes, so we will need to base64 encode any binary content.
        if (isinstance(self.content, bytes)):
            data['content'] = edq.util.encoding.to_base64(self.content)
            data['b64_encoded'] = True

        return data

    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> typing.Any:
        return FileInfo(**data)

class HTTPExchange(edq.util.json.DictConverter):
    """
    The request and response making up a full HTTP exchange.
    """

    def __init__(self,
            method: str = 'GET',
            url: typing.Union[str, None] = None,
            url_path: typing.Union[str, None] = None,
            url_anchor: typing.Union[str, None] = None,
            parameters: typing.Union[typing.Dict[str, typing.Any], None] = None,
            files: typing.Union[typing.List[typing.Union[FileInfo, typing.Dict[str, typing.Any]]], None] = None,
            headers: typing.Union[typing.Dict[str, typing.Any], None] = None,
            allow_redirects: typing.Union[bool, None] = None,
            response_code: int = http.HTTPStatus.OK,
            response_headers: typing.Union[typing.Dict[str, typing.Any], None] = None,
            json_body: typing.Union[bool, None] = None,
            response_body: typing.Union[str, dict, list, None] = None,
            source_path: typing.Union[str, None] = None,
            response_modifier: typing.Union[str, None] = None,
            finalize: typing.Union[str, None] = None,
            extra_options: typing.Union[typing.Dict[str, typing.Any], None] = None,
            **kwargs: typing.Any) -> None:
        method = str(method).upper()
        if (method not in ALLOWED_METHODS):
            raise ValueError(f"Got unknown/disallowed method: '{method}'.")

        self.method: str = method
        """ The HTTP method for this exchange. """

        url_path, url_anchor, parameters = self._parse_url_components(url, url_path, url_anchor, parameters)

        self.url_path: str = url_path
        """
        The path portion of the request URL.
        Only the path (not domain, port, params, anchor, etc) should be included.
        """

        self.url_anchor: typing.Union[str, None] = url_anchor
        """
        The anchor portion of the request URL (if it exists).
        """

        self.parameters: typing.Dict[str, typing.Any] = parameters
        """
        The parameters/arguments for this request.
        Parameters should be provided here and not encoded into URLs,
        regardless of the request method.
        With the exception of files, all parameters should be placed here.
        """

        if (files is None):
            files = []

        parsed_files = []
        for file in files:
            if (isinstance(file, FileInfo)):
                parsed_files.append(file)
            else:
                parsed_files.append(FileInfo(**file))

        self.files: typing.List[FileInfo] = parsed_files
        """
        A list of files to include in the request.
        The files are represented as dicts with a
        "path" (path to the file on disk) and "name" (the filename to send in the request) field.
        These paths must be POSIX-style paths,
        they will be converted to system-specific paths.
        Once this exchange is ready for use, these paths should be resolved (and probably absolute).
        However, when serialized these paths should probably be relative.
        To reconcile this, resolve_paths() should be called before using this exchange.
        """

        if (headers is None):
            headers = {}

        self.headers: typing.Dict[str, typing.Any] = headers
        """ Headers in the request. """

        if (allow_redirects is None):
            allow_redirects = True

        self.allow_redirects: bool = allow_redirects
        """ Follow redirects. """

        self.response_code: int = response_code
        """ The HTTP status code of the response. """

        if (response_headers is None):
            response_headers = {}

        self.response_headers: typing.Dict[str, typing.Any] = response_headers
        """ Headers in the response. """

        if (json_body is None):
            json_body = isinstance(response_body, (dict, list))

        self.json_body: bool = json_body
        """
        Indicates that the response is JSON and should be converted to/from a string.
        If the response body is passed in a dict/list and this is passed as None,
        then this will be set as true.
        """

        if (self.json_body and isinstance(response_body, (dict, list))):
            response_body = edq.util.json.dumps(response_body)

        self.response_body: typing.Union[str, None] = response_body  # type: ignore[assignment]
        """
        The response that should be sent in this exchange.
        """

        self.response_modifier: typing.Union[str, None] = response_modifier
        """
        This function reference will be used to modify responses (in HTTPExchange.make_request() and HTTPExchange.from_response())
        before sent back to the caller.
        This reference must be importable via edq.util.pyimport.fetch().
        """

        self.finalize: typing.Union[str, None] = finalize
        """
        This function reference will be used to finalize echanges before sent back to the caller.
        This reference must be importable via edq.util.pyimport.fetch().
        """

        self.source_path: typing.Union[str, None] = source_path
        """
        The path that this exchange was loaded from (if it was loaded from a file).
        This value should never be serialized, but can be useful for testing.
        """

        if (extra_options is None):
            extra_options = {}

        self.extra_options: typing.Dict[str, typing.Any] = extra_options.copy()
        """
        Additional options for this exchange.
        This library will not use these options, but other's may.
        kwargs will also be added to this.
        """

        self.extra_options.update(kwargs)

    def _parse_url_components(self,
            url: typing.Union[str, None] = None,
            url_path: typing.Union[str, None] = None,
            url_anchor: typing.Union[str, None] = None,
            parameters: typing.Union[typing.Dict[str, typing.Any], None] = None,
            ) -> typing.Tuple[str, typing.Union[str, None], typing.Dict[str, typing.Any]]:
        """
        Parse out all URL-based components from raw inputs.
        The URL's path and anchor can either be supplied separately, or as part of the full given URL.
        If content is present in both places, they much match (or an error will be raised).
        Query parameters may be provided in the full URL,
        but will be overwritten by any that are provided separately.
        Any information from the URL aside from the path, anchor/fragment, and query will be ignored.
        Note that path parameters (not query parameters) will be ignored.
        The final url path, url anchor, and parameters will be returned.
        """

        # Do base initialization and cleanup.

        if (url_path is not None):
            url_path = url_path.strip()
            if (url_path == ''):
                url_path = ''
            else:
                url_path = url_path.lstrip('/')

        if (url_anchor is not None):
            url_anchor = url_anchor.strip()
            if (url_anchor == ''):
                url_anchor = None
            else:
                url_anchor = url_anchor.lstrip('#')

        if (parameters is None):
            parameters = {}

        # Parse the URL (if present).

        if ((url is not None) and (url.strip() != '')):
            parts = urllib.parse.urlparse(url)

            # Handle the path.

            path = parts.path.lstrip('/')

            if ((url_path is not None) and (url_path != path)):
                raise ValueError(f"Mismatched URL paths where supplied implicitly ('{path}') and explicitly ('{url_path}').")

            url_path = path

            # Check the optional anchor/fragment.

            if (parts.fragment != ''):
                fragment = parts.fragment.lstrip('#')

                if ((url_anchor is not None) and (url_anchor != fragment)):
                    raise ValueError(f"Mismatched URL anchors where supplied implicitly ('{fragment}') and explicitly ('{url_anchor}').")

                url_anchor = fragment

            # Check for any parameters.

            url_params = parse_query_string(parts.query)
            for (key, value) in url_params.items():
                if (key not in parameters):
                    parameters[key] = value

        if (url_path is None):
            raise ValueError('URL path cannot be empty, it must be explicitly set via `url_path`, or indirectly via `url`.')

        # Sort parameter keys for consistency.
        parameters = {key: parameters[key] for key in sorted(parameters.keys())}

        return url_path, url_anchor, parameters

    def resolve_paths(self, base_dir: str) -> None:
        """ Resolve any paths relative to the given base dir. """

        for file_info in self.files:
            file_info.resolve_path(base_dir)

    def match(self, query: 'HTTPExchange',
            match_headers: bool = True,
            headers_to_skip: typing.Union[typing.List[str], None] = None,
            params_to_skip: typing.Union[typing.List[str], None] = None,
            **kwargs: typing.Any) -> typing.Tuple[bool, typing.Union[str, None]]:
        """
        Check if this exchange matches the query exchange.
        If they match, `(True, None)` will be returned.
        If they do not match, `(False, <hint>)` will be returned, where `<hint>` points to where the mismatch is.

        Note that this is not an equality check,
        as a query exchange is often missing the response components.
        This method is often invoked the see if an incoming HTTP request (the query) matches an existing exchange.
        """

        if (query.method != self.method):
            return False, f"HTTP method does not match (query = {query.method}, target = {self.method})."

        if (query.url_path != self.url_path):
            return False, f"URL path does not match (query = {query.url_path}, target = {self.url_path})."

        if (query.url_anchor != self.url_anchor):
            return False, f"URL anchor does not match (query = {query.url_anchor}, target = {self.url_anchor})."

        if (headers_to_skip is None):
            headers_to_skip = DEFAULT_EXCHANGE_IGNORE_HEADERS

        if (params_to_skip is None):
            params_to_skip = []

        if (match_headers):
            match, hint = self._match_dict('header', query.headers, self.headers, headers_to_skip)
            if (not match):
                return False, hint

        match, hint = self._match_dict('parameter', query.parameters, self.parameters, params_to_skip)
        if (not match):
            return False, hint

        # Check file names and hash contents.
        query_filenames = {(file.name, file.hash_content()) for file in query.files}
        target_filenames = {(file.name, file.hash_content()) for file in self.files}
        if (query_filenames != target_filenames):
            return False, f"File names do not match (query = {query_filenames}, target = {target_filenames})."

        return True, None

    def _match_dict(self, label: str,
            query_dict: typing.Dict[str, typing.Any],
            target_dict: typing.Dict[str, typing.Any],
            keys_to_skip: typing.Union[typing.List[str], None] = None,
            query_label: str = 'query',
            target_label: str = 'target',
            normalize_key_case: bool = True,
            ) -> typing.Tuple[bool, typing.Union[str, None]]:
        """ A subcheck in match(), specifically for a dictionary. """

        if (keys_to_skip is None):
            keys_to_skip = []

        if (normalize_key_case):
            keys_to_skip = [key.lower() for key in keys_to_skip]
            query_dict = {key.lower(): value for (key, value) in query_dict.items()}
            target_dict = {key.lower(): value for (key, value) in target_dict.items()}

        query_keys = set(query_dict.keys()) - set(keys_to_skip)
        target_keys = set(target_dict.keys()) - set(keys_to_skip)

        if (query_keys != target_keys):
            return False, f"{label.title()} keys do not match ({query_label} = {query_keys}, {target_label} = {target_keys})."

        for key in sorted(query_keys):
            query_value = query_dict[key]
            target_value = target_dict[key]

            if (query_value != target_value):
                comparison = f"{query_label} = '{query_value}', {target_label} = '{target_value}'"
                return False, f"{label.title()} '{key}' has a non-matching value ({comparison})."

        return True, None

    def get_url(self) -> str:
        """ Get the URL path and anchor combined. """

        url = self.url_path

        if (self.url_anchor is not None):
            url += ('#' + self.url_anchor)

        return url

    def make_request(self, base_url: str, raise_for_status: bool = True, **kwargs: typing.Any) -> typing.Tuple[requests.Response, str]:
        """ Perform the HTTP request described by this exchange. """

        files = []
        for file_info in self.files:
            content = file_info.content

            # Content is base64 encoded.
            if (file_info.b64_encoded and isinstance(content, str)):
                content = edq.util.encoding.from_base64(content)

            # Content is missing and must be in a file.
            if (content is None):
                content = open(file_info.path, 'rb')  # type: ignore[assignment,arg-type]  # pylint: disable=consider-using-with

            files.append((file_info.name, content))

        url = f"{base_url}/{self.get_url()}"

        response, body = make_request(self.method, url,
                headers = self.headers,
                data = self.parameters,
                files = files,
                raise_for_status = raise_for_status,
                allow_redirects = self.allow_redirects,
                **kwargs,
        )

        if (self.response_modifier is not None):
            modify_func = edq.util.pyimport.fetch(self.response_modifier)
            body = modify_func(response, body)

        return response, body

    def match_response(self, response: requests.Response,
            override_body: typing.Union[str, None] = None,
            headers_to_skip: typing.Union[typing.List[str], None] = None,
            **kwargs: typing.Any) -> typing.Tuple[bool, typing.Union[str, None]]:
        """
        Check if this exchange matches the given response.
        If they match, `(True, None)` will be returned.
        If they do not match, `(False, <hint>)` will be returned, where `<hint>` points to where the mismatch is.
        """

        if (headers_to_skip is None):
            headers_to_skip = DEFAULT_EXCHANGE_IGNORE_HEADERS

        response_body = override_body
        if (response_body is None):
            response_body = response.text

        if (self.response_code != response.status_code):
            return False, f"http status code does match (expected: {self.response_code}, actual: {response.status_code})"

        expected_body = self.response_body
        actual_body = None

        if (self.json_body):
            actual_body = response.json()

            # Normalize the actual and expected bodies.

            actual_body = edq.util.json.dumps(actual_body)

            if (isinstance(expected_body, str)):
                expected_body = edq.util.json.loads(expected_body)

            expected_body = edq.util.json.dumps(expected_body)
        else:
            actual_body = response_body

        if (self.response_body != actual_body):
            body_hint = f"expected: '{self.response_body}', actual: '{actual_body}'"
            return False, f"body does not match ({body_hint})"

        match, hint = self._match_dict('header', response.headers, self.response_headers,
                keys_to_skip = headers_to_skip,
                query_label = 'response', target_label = 'exchange')

        if (not match):
            return False, hint

        return True, None

    def compute_relpath(self, http_exchange_extension: str = DEFAULT_HTTP_EXCHANGE_EXTENSION) -> str:
        """ Create a consistent, semi-unique, and relative path for this exchange. """

        url = self.get_url().strip()
        parts = url.split('/')


        if (url in ['', '/']):
            filename = '_index_'
            dirname = ''
        else:
            filename = parts[-1]

            if (len(parts) > 1):
                dirname = os.path.join(*parts[0:-1])
            else:
                dirname = ''

        parameters = {}
        for key in sorted(self.parameters.keys()):
            parameters[key] = self.parameters[key]

        # Treat files as params as well.
        for file_info in self.files:
            parameters[f"file-{file_info.name}"] = file_info.hash_content()

        query = urllib.parse.urlencode(parameters)
        if (query != ''):
            # The query can get very long, so we may have to clip it.
            query_text = edq.util.hash.clip_text(query, QUERY_CLIP_LENGTH)

            # Note that the '?' is URL encoded.
            filename += f"%3F{query_text}"

        filename += f"_{self.method}{http_exchange_extension}"

        return os.path.join(dirname, filename)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return vars(self)

    @classmethod
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> typing.Any:
        return HTTPExchange(**data)

    @classmethod
    def from_path(cls, path: str,
            set_source_path: bool = True,
            ) -> 'HTTPExchange':
        """
        Load an exchange from a file.
        This will also handle setting the exchanges source path (if specified) and resolving the exchange's paths.
        """

        exchange = typing.cast(HTTPExchange, edq.util.json.load_object_path(path, HTTPExchange))

        if (set_source_path):
            exchange.source_path = os.path.abspath(path)

        exchange.resolve_paths(os.path.abspath(os.path.dirname(path)))

        return exchange

    @classmethod
    def from_response(cls,
            response: requests.Response,
            headers_to_skip: typing.Union[typing.List[str], None] = None,
            params_to_skip: typing.Union[typing.List[str], None] = None,
            allow_redirects: typing.Union[bool, None] = None,
            ) -> 'HTTPExchange':
        """ Create a full excahnge from a response. """

        if (headers_to_skip is None):
            headers_to_skip = DEFAULT_EXCHANGE_IGNORE_HEADERS

        if (params_to_skip is None):
            params_to_skip = []

        body = response.text

        # Use a clean function (if one exists).
        if (_exchanges_clean_func is not None):
            # Make a copy of the response to avoid cleaning functions modifying it.
            # Note that this is not a very complete solution, since we can't rely on the deep copy getting everything right.
            response = copy.deepcopy(response)

            modify_func = edq.util.pyimport.fetch(_exchanges_clean_func)
            body = modify_func(response, body)

        request_headers = {key.lower().strip(): value for (key, value) in response.request.headers.items()}
        response_headers = {key.lower().strip(): value for (key, value) in response.headers.items()}

        # Clean headers.
        for key in headers_to_skip:
            key = key.lower()

            request_headers.pop(key, None)
            response_headers.pop(key, None)

        request_data, request_files = parse_request_data(response.request.url, response.request.headers, response.request.body)

        # Clean parameters.
        for key in params_to_skip:
            request_data.pop(key, None)

        files = [FileInfo(name = name, content = content) for (name, content) in request_files.items()]

        data = {
            'method': response.request.method,
            'url': response.request.url,
            'url_anchor': response.request.headers.get(ANCHOR_HEADER_KEY, None),
            'parameters': request_data,
            'files': files,
            'headers': request_headers,
            'response_code': response.status_code,
            'response_headers': response_headers,
            'response_body': body,
            'response_modifier': _exchanges_clean_func,
            'allow_redirects': allow_redirects,
        }

        exchange = HTTPExchange(**data)

        # Use a finalize function (if one exists).
        if (_exchanges_finalize_func is not None):
            finalize_func = edq.util.pyimport.fetch(_exchanges_finalize_func)

            exchange = finalize_func(exchange)
            exchange.finalize = _exchanges_finalize_func

        return exchange

@typing.runtime_checkable
class HTTPExchangeComplete(typing.Protocol):
    """
    A function that can be called after a request has been made (and exchange constructed).
    """

    def __call__(self,
            exchange: HTTPExchange
            ) -> str:
        """
        Called after an HTTP exchange has been completed.
        """

_make_request_exchange_complete_func: typing.Union[HTTPExchangeComplete, None] = None  # pylint: disable=invalid-name
""" If not None, call this func after make_request() has created its HTTPExchange. """

def find_open_port(
        start_port: int = DEFAULT_START_PORT, end_port: int = DEFAULT_END_PORT,
        wait_time: float = DEFAULT_PORT_SEARCH_WAIT_SEC) -> int:
    """
    Find an open port on this machine within the given range (inclusive).
    If no open port is found, an error is raised.
    """

    for port in range(start_port, end_port + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('127.0.0.1', port))

            # Explicitly close the port and wait a short amount of time for the port to clear.
            # This should not be required because of the socket option above,
            # but the cost is small.
            sock.close()
            time.sleep(DEFAULT_PORT_SEARCH_WAIT_SEC)

            return port
        except socket.error as ex:
            sock.close()

            if (ex.errno == errno.EADDRINUSE):
                continue

            # Unknown error.
            raise ex

    raise ValueError(f"Could not find open port in [{start_port}, {end_port}].")

def make_request(method: str, url: str,
        headers: typing.Union[typing.Dict[str, typing.Any], None] = None,
        data: typing.Union[typing.Dict[str, typing.Any], None] = None,
        files: typing.Union[typing.List[typing.Any], None] = None,
        raise_for_status: bool = True,
        timeout_secs: float = DEFAULT_REQUEST_TIMEOUT_SECS,
        output_dir: typing.Union[str, None] = None,
        send_anchor_header: bool = True,
        headers_to_skip: typing.Union[typing.List[str], None] = None,
        params_to_skip: typing.Union[typing.List[str], None] = None,
        http_exchange_extension: str = DEFAULT_HTTP_EXCHANGE_EXTENSION,
        add_http_prefix: bool = True,
        additional_requests_options: typing.Union[typing.Dict[str, typing.Any], None] = None,
        exchange_complete_func: typing.Union[HTTPExchangeComplete, None] = None,
        allow_redirects: typing.Union[bool, None] = None,
        use_module_options: bool = True,
        **kwargs: typing.Any) -> typing.Tuple[requests.Response, str]:
    """
    Make an HTTP request and return the response object and text body.
    """

    if (add_http_prefix and (not url.lower().startswith('http'))):
        url = 'http://' + url

    if (output_dir is None):
        output_dir = _exchanges_out_dir

    if (headers is None):
        headers = {}

    if (data is None):
        data = {}

    if (files is None):
        files = []

    if (additional_requests_options is None):
        additional_requests_options = {}

    # Add in the anchor as a header (since it is not traditionally sent in an HTTP request).
    if (send_anchor_header):
        headers = headers.copy()

        parts = urllib.parse.urlparse(url)
        headers[ANCHOR_HEADER_KEY] = parts.fragment.lstrip('#')

    options = {}

    if (use_module_options and (_module_makerequest_options is not None)):
        options.update(_module_makerequest_options)

    options.update(additional_requests_options)

    options.update({
        'headers': headers,
        'files': files,
        'timeout': timeout_secs,
    })

    if (allow_redirects is not None):
        options['allow_redirects'] = allow_redirects

    if (method == 'GET'):
        options['params'] = data
    else:
        options['data'] = data

    _logger.debug("Making %s request: '%s' (options = %s).", method, url, options)
    response = requests.request(method, url, **options)  # pylint: disable=missing-timeout

    body = response.text
    _logger.debug("Response:\n%s", body)

    if (raise_for_status):
        # Handle 404s a little special, as their body may contain useful information.
        if ((response.status_code == http.HTTPStatus.NOT_FOUND) and (body is not None) and (body.strip() != '')):
            response.reason += f" (Body: '{body.strip()}')"

        response.raise_for_status()

    exchange = None
    if ((output_dir is not None) or (exchange_complete_func is not None) or (_make_request_exchange_complete_func is not None)):
        exchange = HTTPExchange.from_response(response,
                headers_to_skip = headers_to_skip, params_to_skip = params_to_skip,
                allow_redirects = options.get('allow_redirects', None))

    if ((output_dir is not None) and (exchange is not None)):
        relpath = exchange.compute_relpath(http_exchange_extension = http_exchange_extension)
        path = os.path.abspath(os.path.join(output_dir, relpath))

        edq.util.dirent.mkdir(os.path.dirname(path))
        edq.util.json.dump_path(exchange, path, indent = 4, sort_keys = False)

    if ((exchange_complete_func is not None) and (exchange is not None)):
        exchange_complete_func(exchange)

    if ((_make_request_exchange_complete_func is not None) and (exchange is not None)):
        _make_request_exchange_complete_func(exchange)  # pylint: disable=not-callable

    return response, body

def make_get(url: str, **kwargs: typing.Any) -> typing.Tuple[requests.Response, str]:
    """
    Make a GET request and return the response object and text body.
    """

    return make_request('GET', url, **kwargs)

def make_post(url: str, **kwargs: typing.Any) -> typing.Tuple[requests.Response, str]:
    """
    Make a POST request and return the response object and text body.
    """

    return make_request('POST', url, **kwargs)

def parse_request_data(
        url: str,
        headers: typing.Union[email.message.Message, typing.Dict[str, typing.Any]],
        body: typing.Union[bytes, str, io.BufferedIOBase],
        ) -> typing.Tuple[typing.Dict[str, typing.Any], typing.Dict[str, bytes]]:
    """ Parse data and files from an HTTP request URL and body. """

    # Parse data from the request body.
    request_data, request_files = parse_request_body_data(headers, body)

    # Parse parameters from the URL.
    url_parts = urllib.parse.urlparse(url)
    request_data.update(parse_query_string(url_parts.query))

    return request_data, request_files

def parse_request_body_data(
        headers: typing.Union[email.message.Message, typing.Dict[str, typing.Any]],
        body: typing.Union[bytes, str, io.BufferedIOBase],
        ) -> typing.Tuple[typing.Dict[str, typing.Any], typing.Dict[str, bytes]]:
    """ Parse data and files from an HTTP request body. """

    data: typing.Dict[str, typing.Any] = {}
    files: typing.Dict[str, bytes] = {}

    length = int(headers.get('Content-Length', 0))
    if (length == 0):
        return data, files

    if (isinstance(body, io.BufferedIOBase)):
        raw_content = body.read(length)
    elif (isinstance(body, str)):
        raw_content = body.encode(edq.util.dirent.DEFAULT_ENCODING)
    else:
        raw_content = body

    content_type = headers.get('Content-Type', '')

    if (content_type in ['', 'application/x-www-form-urlencoded']):
        data = parse_query_string(raw_content.decode(edq.util.dirent.DEFAULT_ENCODING).strip())
        return data, files

    if (content_type.startswith('multipart/form-data')):
        decoder = requests_toolbelt.multipart.decoder.MultipartDecoder(
            raw_content, content_type, encoding = edq.util.dirent.DEFAULT_ENCODING)

        for multipart_section in decoder.parts:
            values = parse_content_dispositions(multipart_section.headers)

            name = values.get('name', None)
            if (name is None):
                raise ValueError("Could not find name for multipart section.")

            # Look for a "filename" field to indicate a multipart section is a file.
            # The file's desired name is still in "name", but an alternate name is in "filename".
            if ('filename' in values):
                filename = values.get('name', '')
                if (filename == ''):
                    raise ValueError("Unable to find filename for multipart section.")

                files[filename] = multipart_section.content
            else:
                # Normal Parameter
                data[name] = multipart_section.text

        return data, files

    raise ValueError(f"Unknown content type: '{content_type}'.")

def parse_content_dispositions(headers: typing.Union[email.message.Message, typing.Dict[str, typing.Any]]) -> typing.Dict[str, typing.Any]:
    """ Parse a request's content dispositions from headers. """

    values = {}
    for (key, value) in headers.items():
        if (isinstance(key, bytes)):
            key = key.decode(edq.util.dirent.DEFAULT_ENCODING)

        if (isinstance(value, bytes)):
            value = value.decode(edq.util.dirent.DEFAULT_ENCODING)

        key = key.strip().lower()
        if (key != 'content-disposition'):
            continue

        # The Python stdlib recommends using the email library for this parsing,
        # but I have not had a good experience with it.
        for part in value.strip().split(';'):
            part = part.strip()

            parts = part.split('=')
            if (len(parts) != 2):
                continue

            cd_key = parts[0].strip()
            cd_value = parts[1].strip().strip('"')

            values[cd_key] = cd_value

    return values

def parse_query_string(text: str,
        replace_single_lists: bool = True,
        keep_blank_values: bool = True,
        **kwargs: typing.Any) -> typing.Dict[str, typing.Any]:
    """
    Parse a query string (like urllib.parse.parse_qs()), and normalize the result.
    If specified, lists with single values (as returned from urllib.parse.parse_qs()) will be replaced with the single value.
    """

    results = urllib.parse.parse_qs(text, keep_blank_values = True)
    for (key, value) in results.items():
        if (replace_single_lists and (len(value) == 1)):
            results[key] = value[0]  # type: ignore[assignment]

    return results

def _disable_https_verification() -> None:
    """ Disable checking the SSL certificate for HTTPS requests. """

    global _module_makerequest_options  # pylint: disable=global-statement

    if (_module_makerequest_options is None):
        _module_makerequest_options = {}

    _module_makerequest_options['verify'] = False

    # Ignore insecure warnings.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def set_cli_args(parser: argparse.ArgumentParser, extra_state: typing.Dict[str, typing.Any]) -> None:
    """
    Set common CLI arguments.
    This is a sibling to init_from_args(), as the arguments set here can be interpreted there.
    """

    parser.add_argument('--http-exchanges-out-dir', dest = 'http_exchanges_out_dir',
        action = 'store', type = str, default = None,
        help = 'If set, write all outgoing HTTP requests as exchanges to this directory.')

    parser.add_argument('--http-exchanges-clean-func', dest = 'http_exchanges_clean_func',
        action = 'store', type = str, default = None,
        help = 'If set, default all created exchanges to this modifier function.')

    parser.add_argument('--http-exchanges-finalize-func', dest = 'http_exchanges_finalize_func',
        action = 'store', type = str, default = None,
        help = 'If set, default all created exchanges to this finalize.')

    parser.add_argument('--https-no-verify', dest = 'https_no_verify',
        action = 'store_true', default = False,
        help = 'If set, skip HTTPS/SSL verification.')

def init_from_args(
        parser: argparse.ArgumentParser,
        args: argparse.Namespace,
        extra_state: typing.Dict[str, typing.Any]) -> None:
    """
    Take in args from a parser that was passed to set_cli_args(),
    and call init() with the appropriate arguments.
    """

    global _exchanges_out_dir  # pylint: disable=global-statement
    if (args.http_exchanges_out_dir is not None):
        _exchanges_out_dir = args.http_exchanges_out_dir

    global _exchanges_clean_func  # pylint: disable=global-statement
    if (args.http_exchanges_clean_func is not None):
        _exchanges_clean_func = args.http_exchanges_clean_func

    global _exchanges_finalize_func  # pylint: disable=global-statement
    if (args.http_exchanges_finalize_func is not None):
        _exchanges_finalize_func = args.http_exchanges_finalize_func

    if (args.https_no_verify):
        _disable_https_verification()
