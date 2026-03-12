import gzip

import edq.util.dirent
import edq.util.encoding

def uncompress_base64(b64_contents: str, encoding: str = edq.util.dirent.DEFAULT_ENCODING) -> bytes:
    """ Uncompress base64 encoded gzipped bytes into bytes. """

    contents = edq.util.encoding.from_base64(b64_contents, encoding = encoding)
    return uncompress(contents)

def uncompress_base64_to_path(b64_contents: str, path: str, encoding: str = edq.util.dirent.DEFAULT_ENCODING) -> None:
    """ Uncompress base64 encoded gzipped bytes into a file. """

    contents = uncompress_base64(b64_contents, encoding)
    edq.util.dirent.write_file_bytes(path, contents)

def uncompress_base64_to_string(b64_contents: str, encoding: str = edq.util.dirent.DEFAULT_ENCODING) -> str:
    """ Uncompress base64 encoded gzipped bytes into a string. """

    return uncompress_base64(b64_contents, encoding).decode(encoding)

def uncompress(data: bytes) -> bytes:
    """ Uncompress gzipped bytes into bytes. """

    return gzip.decompress(data)

def uncompress_to_path(data: bytes, path: str) -> None:
    """ Uncompress gzipped bytes into a file. """

    contents = uncompress(data)
    edq.util.dirent.write_file_bytes(path, contents)

def uncompress_to_string(data: bytes, encoding: str = edq.util.dirent.DEFAULT_ENCODING) -> str:
    """ Uncompress gzipped bytes into a string. """

    return uncompress(data).decode(encoding)

def compress_as_base64(raw_data: bytes, encoding: str = edq.util.dirent.DEFAULT_ENCODING) -> str:
    """ Get the compressed representation of some bytes as a base64 encoded string. """

    data = compress(raw_data)
    return edq.util.encoding.to_base64(data, encoding = encoding)

def compress(raw_data: bytes) -> bytes:
    """ Get the compressed representation of some bytes as bytes. """

    return gzip.compress(raw_data)

def compress_path_as_base64(path: str, encoding: str = edq.util.dirent.DEFAULT_ENCODING) -> str:
    """ Get the compressed contents of a file as a base64 encoded string. """

    data = compress_path(path)
    return edq.util.encoding.to_base64(data, encoding = encoding)

def compress_path(path: str) -> bytes:
    """ Get the compressed contents of a file as bytes. """

    data = edq.util.dirent.read_file_bytes(path)
    return gzip.compress(data)
