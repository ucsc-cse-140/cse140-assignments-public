import hashlib
import typing

import edq.util.constants

DEFAULT_CLIP_HASH_LENGTH: int = 8

def sha256_hex(payload: typing.Any, encoding: str = edq.util.constants.DEFAULT_ENCODING) -> str:
    """ Compute and return the hex string of the SHA3-256 encoding of the payload. """

    if (isinstance(payload, str)):
        payload = payload.encode(encoding)

    digest = hashlib.new('sha256')
    digest.update(payload)
    return digest.hexdigest()

def clip_text(text: str, max_length: int, hash_length: int = DEFAULT_CLIP_HASH_LENGTH) -> str:
    """
    Return a clipped version of the input text that is no longer than the specified length.
    If the base text is found to be too long,
    then enough if the tail of the text will be removed to insert a note about the clipping
    and the first |hash_length| characters of the hash from sha256_hex().

    Note that the max length is actually a soft cap.
    Longer strings can be generated if the original text is shorter than the notification
    that will be inserted into the clipped text.
    """

    if (len(text) <= max_length):
        return text

    hash_hex = sha256_hex(text)
    notification = f"[text clipped {hash_hex[0:hash_length]}]"

    # Don't clip the text if the final string would be longer.
    if (len(notification) >= len(text)):
        return text

    keep_length = max(0, max_length - len(notification))
    return text[0:keep_length] + notification
