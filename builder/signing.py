"""
This file provides our support around digital signature handling.
"""
import hashlib
from pathlib import Path


def sign_path(signature_name: str, path: Path, save_to_file: bool = False) -> str:
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
