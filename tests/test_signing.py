"""
This file contains all the unit tests for our framework's signing support.
"""
import hashlib
from pathlib import Path

# noinspection PyPackageRequirements
from unittest.mock import MagicMock

# noinspection PyProtectedMember
from builder.signing import sign_path, supported_signatures, sign_path_to_files, _get_reference_signature, \
    verify_signature


class TestSigning(object):
    def test_supported_signatures(self):
        for name in supported_signatures:
            digest_constructor = getattr(hashlib, name, None)

            assert digest_constructor is not None

    def test_sign_path(self, tmpdir):
        path = Path(str(tmpdir)) / 'test.txt'

        path.write_text("Testing.\n", encoding='utf-8')

        data = path.read_bytes()
        expected_signatures = {}

        for name in supported_signatures:
            digest = getattr(hashlib, name, None)()
            digest.update(data)
            expected_signatures[name] = digest.hexdigest()

        assert sign_path(path) == expected_signatures

    def test_sign_path_to_files(self, tmpdir):
        path = Path(str(tmpdir)) / 'test.txt'

        path.write_text("Testing.\n", encoding='utf-8')

        signatures = sign_path(path)

        sign_path_to_files(path)

        for name in supported_signatures:
            signature_file = path.parent / f'{path.name}.{name}'

            assert signature_file.is_file() is True
            assert signature_file.read_text(encoding='utf-8') == signatures[name]

    # noinspection PyTypeChecker
    def test_get_reference_signature_no_file(self):
        function = MagicMock(return_value=None)

        assert _get_reference_signature('sig', None, 'base-name', function) is None

        function.assert_called_once_with('base-name.sig')

    # noinspection PyTypeChecker
    def test_get_reference_signature_with_file(self, tmpdir):
        directory = Path(str(tmpdir))
        path = directory / 'base-name.sig'
        function = MagicMock(return_value=path)

        path.write_text("Testing...\n", encoding='utf-8')

        assert _get_reference_signature('sig', None, 'base-name', function) == "Testing..."

        function.assert_called_once_with('base-name.sig')

    # noinspection PyTypeChecker
    def test_get_reference_signature_no_signature(self):
        function = MagicMock(return_value=None)

        assert _get_reference_signature('sig', {}, 'base-name', function) is None

        function.assert_not_called()

    # noinspection PyTypeChecker
    def test_get_reference_signature_with_signature(self):
        function = MagicMock(return_value=None)

        assert _get_reference_signature('sig', {
            'sig': 'digital-signature'
        }, 'base-name', function) == 'digital-signature'

        function.assert_not_called()

    # noinspection PyTypeChecker
    def test_verify_signature(self, tmpdir):
        directory = Path(str(tmpdir))
        path = directory / 'file.sig'
        function = MagicMock(return_value=None)

        path.write_text("Testing...\n", encoding='utf-8')

        signatures = sign_path(path)

        # No matching signatures.
        assert verify_signature(path, {}, function) is False

        # With matching signature.
        assert verify_signature(path, signatures, function) is True
