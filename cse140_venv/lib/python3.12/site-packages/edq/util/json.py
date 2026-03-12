"""
This file standardizes how we write and read JSON.
Specifically, we try to be flexible when reading (using JSON5),
and strict when writing (using vanilla JSON).
"""

import enum
import json
import os
import typing

import json5

import edq.util.dirent

class DictConverter():
    """
    A base class for class that can represent (serialize) and reconstruct (deserialize) themselves as/from a dict.
    The intention is that the dict can then be cleanly converted to/from JSON.

    General (but inefficient) implementations of several core Python equality, comparison, and representation methods are provided.
    """

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        """
        Return a dict that can be used to represent this object.
        If the dict is passed to from_dict(), an identical object should be reconstructed.

        A general (but inefficient) implementation is provided by default.
        """

        return vars(self).copy()

    @classmethod
    # Note that `typing.Self` is returned, but that is introduced in Python 3.12.
    def from_dict(cls, data: typing.Dict[str, typing.Any]) -> typing.Any:
        """
        Return an instance of this subclass created using the given dict.
        If the dict came from to_dict(), the returned object should be identical to the original.

        A general (but inefficient) implementation is provided by default.
        """

        return cls(**data)

    def __eq__(self, other: object) -> bool:
        """
        Check for equality.

        This check uses to_dict() and compares the results.
        This may not be complete or efficient depending on the child class.
        """

        # Note the hard type check (done so we can keep this method general).
        if (type(self) != type(other)):  # pylint: disable=unidiomatic-typecheck
            return False

        return bool(self.to_dict() == other.to_dict())  # type: ignore[attr-defined]

    def __lt__(self, other: 'DictConverter') -> bool:
        return dumps(self) < dumps(other)

    def __hash__(self) -> int:
        return hash(dumps(self))

    def __str__(self) -> str:
        return dumps(self)

    def __repr__(self) -> str:
        return dumps(self)

def _custom_handle(value: typing.Any) -> typing.Union[typing.Dict[str, typing.Any], str]:
    """
    Handle objects that are not JSON serializable by default,
    e.g., calling vars() on an object.
    """

    if (isinstance(value, DictConverter)):
        return value.to_dict()

    if (isinstance(value, enum.Enum)):
        return str(value)

    if (hasattr(value, '__dict__')):
        return dict(vars(value))

    raise ValueError(f"Could not JSON serialize object: '{value}'.")

def load(file_obj: typing.TextIO, strict: bool = False, **kwargs: typing.Any) -> typing.Any:
    """
    Load a file object/handler as JSON.
    If strict is set, then use standard Python JSON,
    otherwise use JSON5.
    """

    if (strict):
        return json.load(file_obj, **kwargs)

    return json5.load(file_obj, **kwargs)

def loads(text: str, strict: bool = False, **kwargs: typing.Any) -> typing.Any:
    """
    Load a string as JSON.
    If strict is set, then use standard Python JSON,
    otherwise use JSON5.
    """

    if (strict):
        return json.loads(text, **kwargs)

    return json5.loads(text, **kwargs)

def load_path(
        path: str,
        strict: bool = False,
        encoding: str = edq.util.dirent.DEFAULT_ENCODING,
        **kwargs: typing.Any) -> typing.Any:
    """
    Load a file path as JSON.
    If strict is set, then use standard Python JSON,
    otherwise use JSON5.
    """

    if (os.path.isdir(path)):
        raise IsADirectoryError(f"Cannot open JSON file, expected a file but got a directory at '{path}'.")

    try:
        with open(path, 'r', encoding = encoding) as file:
            return load(file, strict = strict, **kwargs)
    except Exception as ex:
        raise ValueError(f"Failed to read JSON file '{path}'.") from ex

def loads_object(text: str, cls: typing.Type[DictConverter], **kwargs: typing.Any) -> DictConverter:
    """ Load a JSON string into an object (which is a subclass of DictConverter). """

    data = loads(text, **kwargs)
    if (not isinstance(data, dict)):
        raise ValueError(f"JSON to load into an object is not a dict, found '{type(data)}'.")

    return cls.from_dict(data)  # type: ignore[no-any-return]

def load_object_path(path: str, cls: typing.Type[DictConverter], **kwargs: typing.Any) -> DictConverter:
    """ Load a JSON file into an object (which is a subclass of DictConverter). """

    data = load_path(path, **kwargs)
    if (not isinstance(data, dict)):
        raise ValueError(f"JSON to load into an object is not a dict, found '{type(data)}'.")

    return cls.from_dict(data)  # type: ignore[no-any-return]

def dump(
        data: typing.Any,
        file_obj: typing.TextIO,
        default: typing.Union[typing.Callable, None] = _custom_handle,
        sort_keys: bool = True,
        **kwargs: typing.Any) -> None:
    """ Dump an object as a JSON file object. """

    json.dump(data, file_obj, default = default, sort_keys = sort_keys, **kwargs)

def dumps(
        data: typing.Any,
        default: typing.Union[typing.Callable, None] = _custom_handle,
        sort_keys: bool = True,
        **kwargs: typing.Any) -> str:
    """ Dump an object as a JSON string. """

    return json.dumps(data, default = default, sort_keys = sort_keys, **kwargs)

def dump_path(
        data: typing.Any,
        path: str,
        default: typing.Union[typing.Callable, None] = _custom_handle,
        sort_keys: bool = True,
        encoding: str = edq.util.dirent.DEFAULT_ENCODING,
        **kwargs: typing.Any) -> None:
    """ Dump an object as a JSON file. """

    with open(path, 'w', encoding = encoding) as file:
        dump(data, file, default = default, sort_keys = sort_keys, **kwargs)
