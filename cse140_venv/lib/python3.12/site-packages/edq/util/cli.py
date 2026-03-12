"""
Show the CLI tools available in this package.

This will look for objects that "look like" CLI tools.
A package looks like a CLI package if it has a __main__.py file.
A module looks like a CLI tool if it has the following functions:
 - `def _get_parser() -> argparse.ArgumentParser:`
 - `def run_cli(args: argparse.Namespace) -> int:`
"""

import argparse
import inspect
import os

import edq.util.dirent
import edq.util.pyimport

def auto_list(
        recursive: bool = False,
        skip_dirs: bool = False,
        ) -> None:
    """
    Print the caller's docstring and call _list_dir() on it,
    but will figure out the package's docstring, base_dir, and command_prefix automatically.
    This will use the inspect library, so only use in places that use code normally.
    The first stack frame not in this file will be used.
    """

    this_path = os.path.realpath(__file__)

    caller_frame_info = None
    for frame_info in inspect.stack():
        if (edq.util.dirent.same(this_path, frame_info.filename)):
            # Ignore this file.
            continue

        caller_frame_info = frame_info
        break

    if (caller_frame_info is None):
        raise ValueError("Unable to determine caller's stack frame.")

    path = caller_frame_info.filename
    base_dir = os.path.dirname(path)

    try:
        module = inspect.getmodule(caller_frame_info.frame)
        if (module is None):
            raise ValueError(f"Unable to get module for '{path}'.")
    except Exception as ex:
        raise ValueError("Unable to get caller information for listing CLI information.") from ex

    if (module.__package__ is None):
        raise ValueError(f"Caller module has no package information: '{path}'.")

    if (module.__doc__ is None):
        raise ValueError(f"Caller module has no docstring: '{path}'.")

    print(module.__doc__.strip())
    _list_dir(base_dir, module.__package__, recursive, skip_dirs)

def _list_dir(base_dir: str, command_prefix: str, recursive: bool, skip_dirs: bool) -> None:
    """ List/descend the given dir. """

    for dirent in sorted(os.listdir(base_dir)):
        path = os.path.join(base_dir, dirent)
        cmd = command_prefix + '.' + os.path.splitext(dirent)[0]

        if (dirent.startswith('__')):
            continue

        if (os.path.isfile(path)):
            _handle_file(path, cmd)
        else:
            if (not skip_dirs):
                _handle_dir(path, cmd)

            if (recursive):
                _list_dir(path, cmd, recursive, skip_dirs)

def _handle_file(path: str, cmd: str) -> None:
    """ Process a file (possible module). """

    if (not path.endswith('.py')):
        return

    try:
        module = edq.util.pyimport.import_path(path)
    except Exception:
        print("ERROR Importing: ", path)
        return

    if ('_get_parser' not in dir(module)):
        return

    parser = module._get_parser()
    parser.prog = 'python3 -m ' + cmd

    print()
    print(cmd)
    print(parser.description)
    parser.print_usage()

def _handle_dir(path: str, cmd: str) -> None:
    """ Process a dir (possible package). """

    try:
        module = edq.util.pyimport.import_path(os.path.join(path, '__main__.py'))
    except Exception:
        return

    description = module.__doc__.strip()

    print()
    print(cmd + '.*')
    print(description)
    print(f"See `python3 -m {cmd}` for more information.")

def _get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description = __doc__.strip(),
        epilog = ("Note that you don't need to provide a package as an argument,"
            + " since you already called this on the target package."))

    parser.add_argument('-r', '--recursive', dest = 'recursive',
        action = 'store_true', default = False,
        help = 'Recur into each package to look for tools and subpackages (default: %(default)s).')

    parser.add_argument('-s', '--skip-dirs', dest = 'skip_dirs',
        action = 'store_true', default = False,
        help = ('Do not output information about directories/packages,'
            + ' only tools/files/modules (default: %(default)s).'))

    return parser

def run_cli(args: argparse.Namespace) -> int:
    """
    List the caller's dir.
    """

    auto_list(recursive = args.recursive, skip_dirs = args.skip_dirs)

    return 0

def main() -> int:
    """
    Run as if this process has been called as a executable.
    This will parse the command line and list the caller's dir.
    """

    return run_cli(_get_parser().parse_args())
