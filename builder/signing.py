"""
This file provides our support around digital signature handling.
"""
import hashlib
from pathlib import Path
from typing import Dict, Callable, Optional

supported_signatures = ['sha512', 'sha256', 'sha1', 'md5']
FetchFileFunction = Callable[[str], Optional[Path]]


def sign_path(path: Path) -> Dict[str, str]:
    """
    A function for signing a file with each of our known signature algorithms.  The
    dictionary returned will be keyed by the signature name mapped to the digital
    signature resulting from signing the file.

    :param path: the path to the file to sign.
    :return: a dictionary of signature name to signature.
    """
    with path.open('rb') as fd:
        digests = {signature_name: getattr(hashlib, signature_name, None)() for signature_name in supported_signatures}
        chunk = fd.read(4096)

        while chunk:
            for digest in digests.values():
                digest.update(chunk)
            chunk = fd.read(4096)

    return {signature_name: digest.hexdigest() for signature_name, digest in digests.items()}


def sign_path_to_files(path: Path):
    """
    A function for signing a file with each of our known signature algorithms and then
    writing each to a parallel file.

    :param path: the path to the file to sign.
    """
    signatures = sign_path(path)
    path = path.parent / f'{path.name}.tmp'

    for signature_name in supported_signatures:
        signature_path = path.with_suffix(f'.{signature_name}')

        signature_path.write_text(signatures[signature_name], encoding='utf-8')


def _get_reference_signature(signature_name: str, signatures: Optional[Dict[str, str]], base_name: str,
                             function: FetchFileFunction) -> Optional[str]:
    """
    A function that will acquire the reference signature for a path.  If the ``signatures``
    dictionary is ``None``, the given function will be used to gain access to a file that
    will be read for the signature.  Otherwise, the reference signature will be pulled
    from the ``signatures`` dictionary.

    :param signature_name: the name of the signature algorithm.
    :param signatures: the optional dictionary of reference signatures.
    :param base_name: the base name of the reference signature file.
    :param function: the function to use to resolve a signature file when necessary.
    :return: the reference signature or ``None``.
    """
    if signatures is None:
        signature_path = function(f'{base_name}.{signature_name}')

        if signature_path:
            return signature_path.read_text('utf-8').strip()
    elif signature_name in signatures:
        return signatures[signature_name]

    return None


def verify_signature(path: Path, signatures: Optional[Dict[str, str]], function: FetchFileFunction) -> bool:
    """
    A function that will verify the digital signature of the given path.  If the
    ``signatures`` dictionary is ``None``, it is assumed that reference signatures
    will be found in files that are parallel to the given path.  If fetching is needed
    the given function will be used to resolve access to each reference signature
    file.  If the ``signatures`` dictionary is not ``None`` then it will be treated
    as the source for reference signatures.

    :param path: the path to verify the signature for.
    :param signatures: the optional dictionary of reference signatures.
    :param function: the function to use to resolve a signature file when necessary.
    :return: ``True`` if a matching signature is found or ``False`` if not.
    """
    path_signatures = sign_path(path)

    for signature_name in supported_signatures:
        path_signature = path_signatures[signature_name]
        reference_signature = _get_reference_signature(signature_name, signatures, path.name, function)

        if path_signature == reference_signature:
            return True

    return False
