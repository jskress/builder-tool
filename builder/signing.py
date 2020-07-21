"""
This file provides our support around digital signature handling.
"""
import hashlib
from pathlib import Path


def sign_path(signature_name: str, path: Path, save_to_file: bool = False) -> str:
    """
    A function for signing a file using a named signing algorithm such as ``sha256``.
    If ``save_to_file`` is ``True``, the derived signature is written to its own file.
    The name of the file will be the name of the file that was signed, with the signature
    algorithm name added as an extension.

    :param signature_name: the name of the algorithm to use in signing the file.
    :param path: the path to the file to sign.
    :param save_to_file: if ``True``, writes the signature to its own file.
    :return: the signature, in hex form.
    """
    digest_constructor = getattr(hashlib, signature_name, None)

    if not digest_constructor:
        raise ValueError(f'There is no support for the {signature_name} signature algorithm.')

    with path.open('rb') as fd:
        digest = digest_constructor()
        chunk = fd.read(4096)
        while chunk:
            digest.update(chunk)
            chunk = fd.read(4096)
    signature = digest.hexdigest()

    if save_to_file:
        signature_file = path.parent / f'{path.name}.{signature_name}'

        with signature_file.open('w') as fd:
            fd.write(signature)

    return signature
