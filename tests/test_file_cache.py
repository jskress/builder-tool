"""
This file contains all the unit tests for our framework's file cache.
"""
from pathlib import Path
from typing import Optional
from unittest.mock import patch, MagicMock, call

# noinspection PyPackageRequirements
import pytest
from requests import HTTPError
from requests.status_codes import codes
from requests.structures import CaseInsensitiveDict

from builder.file_cache import file_cache, FileCache


class FakeResponse(object):
    def __init__(self, status_code: int, msg: Optional[str] = None, content_length: Optional[int] = None,
                 content: Optional[str] = None):
        self.status_code = status_code
        self.reason = codes[status_code]
        self.message = msg
        self.headers = {}
        self.headers = CaseInsensitiveDict()
        self._content = content

        if content_length is not None:
            self.headers['Content-Length'] = content_length

    def iter_content(self, *, chunk_size: int):
        assert chunk_size == 1024

        def generator():
            yield bytes(self._content, encoding='utf-8')
            return

        return generator()

    def raise_for_status(self):
        if self.message:
            raise HTTPError(self.message, response=self)


class TestGlobalCache(object):
    def test_global_cache(self):
        # noinspection PyProtectedMember
        assert file_cache._base_file_cache_path == Path.home() / '.builder'


# noinspection DuplicatedCode
class TestFileCache(object):
    def test_file_cache_construction(self, tmpdir):
        base_path = Path(str(tmpdir))
        builder_path = base_path / '.builder'

        assert not builder_path.exists()

        # Make sure the directory is properly created.
        cache = FileCache(base_path)

        # noinspection PyProtectedMember
        assert cache._base_file_cache_path == builder_path
        assert builder_path.exists()

        # Make sure no errors occur if the directory already exists.
        cache = FileCache(base_path)

        # noinspection PyProtectedMember
        assert cache._base_file_cache_path == builder_path
        assert builder_path.exists()

    def test_resolve_file_existing_file_no_force(self, tmpdir):
        base_path = Path(str(tmpdir))
        the_file = Path('the.file')
        path = base_path / '.builder' / the_file

        # Make sure the path already exists.
        path.parent.mkdir()
        path.touch()

        cache = FileCache(base_path)

        with patch('builder.file_cache.global_options.force_remote_fetch') as mock_frf:
            mock_frf.return_value = False

            assert cache.resolve_file('the-url', the_file) == path

    def test_resolve_file_existing_file_with_force_works(self, tmpdir):
        base_path = Path(str(tmpdir))
        the_file = Path('the.file')
        path = base_path / '.builder' / the_file
        mock_download = MagicMock()

        # Make sure the path already exists.
        path.parent.mkdir()
        path.touch()

        cache = FileCache(base_path)

        cache._download_file = mock_download
        mock_download.return_value = True

        with patch('builder.file_cache.global_options.force_remote_fetch') as mock_frf:
            mock_frf.return_value = True

            assert cache.resolve_file('the-url', the_file) == path
            assert mock_download.mock_calls == [
                call('the-url', path, False)
            ]

    def test_resolve_file_existing_file_with_force_fails(self, tmpdir):
        base_path = Path(str(tmpdir))
        the_file = Path('the.file')
        path = base_path / '.builder' / the_file
        mock_download = MagicMock()

        # Make sure the path already exists.
        path.parent.mkdir()
        path.touch()

        cache = FileCache(base_path)

        cache._download_file = mock_download
        mock_download.return_value = False

        with patch('builder.file_cache.global_options.force_remote_fetch') as mock_frf:
            mock_frf.return_value = True

            assert cache.resolve_file('the-url', the_file) is None
            assert mock_download.mock_calls == [
                call('the-url', path, False)
            ]

    def test_resolve_file_missing_file_fails(self, tmpdir):
        base_path = Path(str(tmpdir))
        the_file = Path('the.file')
        path = base_path / '.builder' / the_file
        mock_download = MagicMock()

        cache = FileCache(base_path)

        cache._download_file = mock_download
        mock_download.return_value = False

        with patch('builder.file_cache.global_options.force_remote_fetch') as mock_frf:
            mock_frf.return_value = False

            assert cache.resolve_file('the-url', the_file) is None
            assert mock_download.mock_calls == [
                call('the-url', path, False)
            ]

    def test_resolve_file_missing_file_works(self, tmpdir):
        base_path = Path(str(tmpdir))
        the_file = Path('the.file')
        path = base_path / '.builder' / the_file
        mock_download = MagicMock()

        cache = FileCache(base_path)

        cache._download_file = mock_download
        mock_download.return_value = True

        with patch('builder.file_cache.global_options.force_remote_fetch') as mock_frf:
            mock_frf.return_value = False

            assert cache.resolve_file('the-url', the_file) == path
            assert mock_download.mock_calls == [
                call('the-url', path, False)
            ]

    def test_resolve_file_handles_http_error(self, tmpdir):
        base_path = Path(str(tmpdir))
        the_file = Path('the.file')
        cache = FileCache(base_path)
        mock_download = MagicMock(side_effect=HTTPError('Bad HTTP call!'))

        cache._download_file = mock_download
        mock_download.return_value = True

        with pytest.raises(ValueError) as info:
            _ = cache.resolve_file('the-url', the_file)

        assert info.value.args[0] == 'Could not cache the.file: Bad HTTP call!'

    def test_download_file_non_existent(self):
        with patch('builder.file_cache.FileCache._get_download_file_size') as mock_dl_size:
            mock_dl_size.return_value = (None, False)

            # noinspection PyProtectedMember
            assert FileCache._download_file('the-url', Path('the-path'), False) is False

        assert mock_dl_size.mock_calls == [call('the-url', False)]

    def test_download_file_http_error(self):
        response = FakeResponse(502, msg='Run away!')

        with patch('builder.file_cache.FileCache._get_download_file_size') as mock_dl_size:
            mock_dl_size.return_value = (7, True)

            with patch('builder.file_cache.requests') as mock_requests:
                mock_requests.get.return_value = response

                with pytest.raises(HTTPError) as he:
                    # noinspection PyProtectedMember
                    _ = FileCache._download_file('the-url', Path('the-path'), False)

        assert mock_dl_size.mock_calls == [call('the-url', False)]
        assert mock_requests.get.mock_calls == [
            call('the-url', allow_redirects=True)
        ]
        assert he.value.response == response
        assert he.value.args[0] == 'Run away!'

    def test_download_file(self, tmpdir):
        path = Path(str(tmpdir)) / 'path' / 'to' / 'file.txt'
        expected = 'The quick brown fox, blah, blah'
        response = FakeResponse(200, content=expected)

        with patch('builder.file_cache.FileCache._get_download_file_size') as mock_dl_size:
            mock_dl_size.return_value = (len(expected), True)

            with patch('builder.file_cache.requests') as mock_requests:
                mock_requests.get.return_value = response

                # noinspection PyProtectedMember
                assert FileCache._download_file('the-url', path, False) is True

        assert path.exists()
        assert path.read_text(encoding='utf-8') == expected

    def test_make_label(self):
        # noinspection PyProtectedMember
        function = FileCache._make_label

        assert function('name') == '                     name'
        assert function('this is a 25-char name---') == 'this is a 25-char name---'
        assert function('this is a too-long name---') == 'this is a t...ong name---'
        assert function('this is a name that is longer than 25 characters') == 'this is a n... characters'

    # noinspection PyProtectedMember
    def test_get_download_file_size_good_content_length(self):
        response = FakeResponse(200, content_length=7)

        with patch('builder.file_cache.requests') as mock_requests:
            mock_requests.head.return_value = response

            length, exists = FileCache._get_download_file_size('the-url', optional=False)

        assert mock_requests.head.mock_calls == [
            call('the-url', allow_redirects=True)
        ]
        assert length == 7
        assert exists is True

    # noinspection PyProtectedMember
    def test_get_download_file_size_no_content_length(self):
        response = FakeResponse(200)

        with patch('builder.file_cache.requests') as mock_requests:
            mock_requests.head.return_value = response

            length, exists = FileCache._get_download_file_size('the-url', optional=False)

        assert mock_requests.head.mock_calls == [
            call('the-url', allow_redirects=True)
        ]
        assert length is None
        assert exists is True

    # noinspection PyProtectedMember
    def test_get_download_file_size_no_required_file(self):
        response = FakeResponse(404, msg='Run away!')

        with patch('builder.file_cache.requests') as mock_requests:
            mock_requests.head.return_value = response

            with pytest.raises(HTTPError) as he:
                _, _ = FileCache._get_download_file_size('the-url', optional=False)

        assert mock_requests.head.mock_calls == [
            call('the-url', allow_redirects=True)
        ]
        assert he.value.response == response
        assert he.value.args[0] == 'Run away!'

    # noinspection PyProtectedMember
    def test_get_download_file_size_no_optional_file(self):
        response = FakeResponse(404, msg='Run away!')

        with patch('builder.file_cache.requests') as mock_requests:
            mock_requests.head.return_value = response

            length, exists = FileCache._get_download_file_size('the-url', optional=True)

        assert mock_requests.head.mock_calls == [
            call('the-url', allow_redirects=True)
        ]
        assert length is None
        assert exists is False
