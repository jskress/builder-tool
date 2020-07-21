"""
This file contains all the unit tests for our framework's signing support.
"""
import hashlib
from pathlib import Path

# noinspection PyPackageRequirements
import pytest

from builder.signing import sign_path


def _sign_data(data: bytes) -> str:
    digest_constructor = getattr(hashlib, 'md5', None)
    digest = digest_constructor()
    digest.update(data)
    return digest.hexdigest()


class TestSigning(object):
    def test_no_such_algorithm(self, tmpdir):
        path = Path(tmpdir)

        with pytest.raises(ValueError) as info:
            sign_path('no_such_signature', path)

        assert info.value.args[0] == 'There is no support for the no_such_signature signature algorithm.'

    def test_signing_with_no_save(self, tmpdir):
        data = 'test\n'.encode()
        file = Path(tmpdir) / 'test.bin'
        sign_file = Path(tmpdir) / 'test.bin.nd5'

        with file.open('wb') as fd:
            fd.write(data)

        assert sign_path('md5', file) == _sign_data(data)
        assert not sign_file.exists()

    def test_signing_with_save(self, tmpdir):
        data = 'test\n'.encode()
        file = Path(tmpdir) / 'test.bin'
        sign_file = file.parent / 'test.bin.md5'
        signature = _sign_data(data)

        with file.open('wb') as fd:
            fd.write(data)

        assert sign_path('md5', file, save_to_file=True) == signature
        assert sign_file.exists()
        assert sign_file.read_text() == signature
