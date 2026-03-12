import typing

def get_qualified_name(target: typing.Union[type, object, str]) -> str:
    """
    Try to get a qualified name for a type (or for the type of an object).
    Names will not always come out clean.
    """

    # Get the type for this target.
    if (isinstance(target, type)):
        target_class = target
    elif (callable(target)):
        target_class = typing.cast(type, target)
    else:
        target_class = type(target)

    # Check for various name components.
    parts = []

    if (hasattr(target_class, '__module__')):
        parts.append(str(getattr(target_class, '__module__')))

    if (hasattr(target_class, '__qualname__')):
        parts.append(str(getattr(target_class, '__qualname__')))
    elif (hasattr(target_class, '__name__')):
        parts.append(str(getattr(target_class, '__name__')))

    # Fall back to just the string reprsentation.
    if (len(parts) == 0):
        return str(target_class)

    return '.'.join(parts)
