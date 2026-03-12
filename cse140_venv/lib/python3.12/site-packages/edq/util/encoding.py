import base64
import typing

import edq.util.dirent

def to_base64(data: typing.Union[bytes, str], encoding: str = edq.util.dirent.DEFAULT_ENCODING) -> str:
    """ Convert a payload to a base64-encoded string. """

    if (isinstance(data, str)):
        data = data.encode(encoding)

    data = base64.standard_b64encode(data)
    return data.decode(encoding)

def from_base64(data: str, encoding: str = edq.util.dirent.DEFAULT_ENCODING) -> bytes:
    """ Convert a base64-encoded string to bytes. """

    return base64.b64decode(data.encode(encoding), validate = True)
