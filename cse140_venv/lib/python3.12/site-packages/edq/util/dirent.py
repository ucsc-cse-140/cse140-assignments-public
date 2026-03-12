"""
Operations relating to directory entries (dirents).

These operations are designed for clarity and compatibility, not performance.

Only directories, files, and links will be handled.
Other types of dirents may result in an error being raised.

In general, all recursive operations do not follow symlinks by default and instead treat the link as a file.
"""

import atexit
import os
import shutil
import tempfile
import typing
import uuid

import edq.util.constants
import edq.util.hash

DEFAULT_ENCODING: str = edq.util.constants.DEFAULT_ENCODING
""" The default encoding that will be used when reading and writing. """

DEPTH_LIMIT: int = 10000

def exists(path: str) -> bool:
    """
    Check if a path exists.
    This will transparently call os.path.lexists(),
    which will include broken links.
    """

    return os.path.lexists(path)

def get_temp_path(prefix: str = '', suffix: str = '', rm: bool = True) -> str:
    """
    Get a path to a valid (but not currently existing) temp dirent.
    If rm is True, then the dirent will be attempted to be deleted on exit
    (no error will occur if the path is not there).
    """

    path = None
    while ((path is None) or exists(path)):
        path = os.path.join(tempfile.gettempdir(), prefix + str(uuid.uuid4()) + suffix)

    path = os.path.realpath(path)

    if (rm):
        atexit.register(remove, path)

    return path

def get_temp_dir(prefix: str = '', suffix: str = '', rm: bool = True) -> str:
    """
    Get a temp directory.
    The directory will exist when returned.
    """

    path = get_temp_path(prefix = prefix, suffix = suffix, rm = rm)
    mkdir(path)
    return path

def mkdir(raw_path: str) -> None:
    """
    Make a directory (including any required parent directories).
    Does not complain if the directory (or parents) already exist
    (this includes if the directory or parents are links to directories).
    """

    path = os.path.abspath(raw_path)

    if (exists(path)):
        if (os.path.isdir(path)):
            return

        raise ValueError(f"Target of mkdir already exists, and is not a dir: '{raw_path}'.")

    _check_parent_dirs(raw_path)

    os.makedirs(path, exist_ok = True)

def _check_parent_dirs(raw_path: str) -> None:
    """
    Check all parents to ensure that they are all dirs (or don't exist).
    This is naturally handled by os.makedirs(),
    but the error messages are not consistent between POSIX and Windows.
    """

    path = os.path.abspath(raw_path)

    parent_path = path
    for _ in range(DEPTH_LIMIT):
        new_parent_path = os.path.dirname(parent_path)
        if (parent_path == new_parent_path):
            # We have reached root (are our own parent).
            return

        parent_path = new_parent_path

        if (os.path.exists(parent_path) and (not os.path.isdir(parent_path))):
            raise ValueError(f"Target of mkdir contains parent ('{os.path.basename(parent_path)}') that exists and is not a dir: '{raw_path}'.")

    raise ValueError("Depth limit reached.")

def remove(path: str) -> None:
    """
    Remove the given path.
    The path can be of any type (dir, file, link),
    and does not need to exist.
    """

    if (not exists(path)):
        return

    if (os.path.isfile(path) or os.path.islink(path)):
        os.remove(path)
    elif (os.path.isdir(path)):
        shutil.rmtree(path)
    else:
        raise ValueError(f"Unknown type of dirent: '{path}'.")

def same(a: str, b: str) -> bool:
    """
    Check if two paths represent the same dirent.
    If either (or both) paths do not exist, false will be returned.
    If either paths are links, they are resolved before checking
    (so a link and the target file are considered the "same").
    """

    return (exists(a) and exists(b) and os.path.samefile(a, b))

def move(raw_source: str, raw_dest: str, no_clobber: bool = False) -> None:
    """
    Move the source dirent to the given destination.
    Any existing destination will be removed before moving.
    """

    source = os.path.abspath(raw_source)
    dest = os.path.abspath(raw_dest)

    if (not exists(source)):
        raise ValueError(f"Source of move does not exist: '{raw_source}'.")

    # If dest is a dir, then resolve the path.
    if (os.path.isdir(dest)):
        dest = os.path.abspath(os.path.join(dest, os.path.basename(source)))

    # Skip if this is self.
    if (same(source, dest)):
        return

    # Check for clobber.
    if (exists(dest)):
        if (no_clobber):
            raise ValueError(f"Destination of move already exists: '{raw_dest}'.")

        remove(dest)

    # Create any required parents.
    os.makedirs(os.path.dirname(dest), exist_ok = True)

    shutil.move(source, dest)

def copy(raw_source: str, raw_dest: str, no_clobber: bool = False) -> None:
    """
    Copy a dirent or directory to a destination.

    The destination will be overwritten if it exists (and no_clobber is false).
    For copying the contents of a directory INTO another directory, use copy_contents().

    No copy is made if the source and dest refer to the same dirent.
    """

    source = os.path.abspath(raw_source)
    dest = os.path.abspath(raw_dest)

    if (same(source, dest)):
        return

    if (not exists(source)):
        raise ValueError(f"Source of copy does not exist: '{raw_source}'.")

    if (contains_path(source, dest)):
        raise ValueError(f"Source of copy cannot contain the destination. Source: '{raw_source}', Destination: '{raw_dest}'.")

    if (contains_path(dest, source)):
        raise ValueError(f"Destination of copy cannot contain the source. Destination: '{raw_dest}', Source: '{raw_source}'.")

    if (exists(dest)):
        if (no_clobber):
            raise ValueError(f"Destination of copy already exists: '{raw_dest}'.")

        remove(dest)

    mkdir(os.path.dirname(dest))

    if (os.path.islink(source)):
        # shutil.copy2() can generally handle (broken) links, but Windows is inconsistent (between 3.11 and 3.12) on link handling.
        link_target = os.readlink(source)
        os.symlink(link_target, dest)
    elif (os.path.isfile(source)):
        shutil.copy2(source, dest, follow_symlinks = False)
    elif (os.path.isdir(source)):
        mkdir(dest)

        for child in sorted(os.listdir(source)):
            copy(os.path.join(raw_source, child), os.path.join(raw_dest, child))
    else:
        raise ValueError(f"Source of copy is not a dir, fie, or link: '{raw_source}'.")

def copy_contents(raw_source: str, raw_dest: str, no_clobber: bool = False) -> None:
    """
    Copy a file or the contents of a directory (excluding the top-level directory itself) into a destination.
    If the destination exists, it must be a directory.

    The source and destination should not be the same file.

    For a file, this is equivalent to `mkdir -p dest && cp source dest`
    For a dir, this is equivalent to `mkdir -p dest && cp -r source/* dest`
    """

    source = os.path.abspath(raw_source)
    dest = os.path.abspath(raw_dest)

    if (same(source, dest)):
        raise ValueError(f"Source and destination of contents copy cannot be the same: '{raw_source}'.")

    if (exists(dest) and (not os.path.isdir(dest))):
        raise ValueError(f"Destination of contents copy exists and is not a dir: '{raw_dest}'.")

    mkdir(dest)

    if (os.path.isfile(source) or os.path.islink(source)):
        copy(source, os.path.join(dest, os.path.basename(source)), no_clobber = no_clobber)
    elif (os.path.isdir(source)):
        for child in sorted(os.listdir(source)):
            copy(os.path.join(raw_source, child), os.path.join(raw_dest, child), no_clobber = no_clobber)
    else:
        raise ValueError(f"Source of contents copy is not a dir, fie, or link: '{raw_source}'.")

def read_file(raw_path: str, strip: bool = True, encoding: str = DEFAULT_ENCODING) -> str:
    """ Read the contents of a file. """

    path = os.path.abspath(raw_path)

    if (not exists(path)):
        raise ValueError(f"Source of read does not exist: '{raw_path}'.")

    with open(path, 'r', encoding = encoding) as file:
        contents = file.read()

    if (strip):
        contents = contents.strip()

    return contents

def write_file(
        raw_path: str, contents: typing.Union[str, None],
        strip: bool = True, newline: bool = True,
        encoding: str = DEFAULT_ENCODING,
        no_clobber: bool = False) -> None:
    """
    Write the contents of a file.
    If clobbering, any existing dirent will be removed before write.
    """

    path = os.path.abspath(raw_path)

    if (exists(path)):
        if (no_clobber):
            raise ValueError(f"Destination of write already exists: '{raw_path}'.")

        remove(path)

    if (contents is None):
        contents = ''

    if (strip):
        contents = contents.strip()

    if (newline):
        contents += "\n"

    with open(path, 'w', encoding = encoding) as file:
        file.write(contents)

def read_file_bytes(raw_path: str) -> bytes:
    """ Read the contents of a file as bytes. """

    path = os.path.abspath(raw_path)

    if (not exists(path)):
        raise ValueError(f"Source of read bytes does not exist: '{raw_path}'.")

    with open(path, 'rb') as file:
        return file.read()

def write_file_bytes(
        raw_path: str, contents: typing.Union[bytes, str, None],
        no_clobber: bool = False) -> None:
    """
    Write the contents of a file as bytes.
    If clobbering, any existing dirent will be removed before write.
    """

    if (contents is None):
        contents = b''

    if (isinstance(contents, str)):
        contents = contents.encode(DEFAULT_ENCODING)

    path = os.path.abspath(raw_path)

    if (exists(path)):
        if (no_clobber):
            raise ValueError(f"Destination of write bytes already exists: '{raw_path}'.")

        remove(path)

    with open(path, 'wb') as file:
        file.write(contents)

def contains_path(parent: str, child: str) -> bool:
    """
    Check if the parent path contains the child path.
    This is pure lexical analysis, no dirent stats are checked.
    Will return false if the (absolute) paths are the same
    (this function does not allow a path to contain itself).
    """

    if ((parent == '') or (child == '')):
        return False

    parent = os.path.abspath(parent)
    child = os.path.abspath(child)

    child = os.path.dirname(child)
    for _ in range(DEPTH_LIMIT):
        if (parent == child):
            return True

        new_child = os.path.dirname(child)
        if (child == new_child):
            return False

        child = new_child

    raise ValueError("Depth limit reached.")

def hash_file(raw_path: str) -> str:
    """
    Compute the SHA256 hash of the file (see edq.util.hash.sha256_hex()).
    Links will has their path (according to os.readlink()).
    Directories will raise an exception.
    """

    path = os.path.abspath(raw_path)

    contents: typing.Any = None

    if (not exists(path)):
        raise ValueError(f"Target of hash file does not exist: '{raw_path}'.")

    if (os.path.islink(path)):
        contents = os.readlink(path)
    elif (os.path.isfile(path)):
        contents = read_file_bytes(raw_path)
    else:
        raise ValueError(f"Target of hash file is not a file: '{raw_path}'.")

    return edq.util.hash.sha256_hex(contents)

def tree(raw_path: str, hash_files: bool = False) -> typing.Dict[str, typing.Union[None, str, typing.Dict[str, typing.Any]]]:
    """
    Return a tree structure that includes all descendants of the given dirent (including the dirent itself).
    If `hash_files` is true, then the value of non-dir keys will be the SHA256 hash of the file (see hash_file()),
    otherwise the value will be None.
    """

    path = os.path.abspath(raw_path)

    if (not exists(path)):
        raise ValueError(f"Target of tree does not exist: '{raw_path}'.")

    return {
        os.path.basename(path): _tree(path, hash_files, 0),
    }

def _tree(path: str, hash_files: bool, level: int) -> typing.Union[str, None, typing.Dict[str, typing.Any]]:
    """ Recursive helper for tree(). """

    if (level > DEPTH_LIMIT):
        raise ValueError("Depth limit reached.")

    if (not os.path.isdir(path)):
        if (hash_files):
            return hash_file(path)

        return None

    result = {}
    for child in sorted(os.listdir(path)):
        result[child] = _tree(os.path.join(path, child), hash_files, level + 1)

    return result
