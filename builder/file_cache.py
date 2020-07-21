"""
This file provides all our support for managing a file cache.
"""
from pathlib import Path
from typing import Optional, Tuple

import click
import requests

from builder.utils import global_options, verbose_out


class FileCache(object):
    """
    Instances of this class represent a cache of files.  It is intended to be used as a singleton.
    Do not instantiate this class directly; instead use the ``file_cache`` module attribute.
    """
    def __init__(self, root: Path):
        """
        A function to create an instance of the ``FileCache`` class.  This class is designed to
        be created once during module load and used via the ``file_cache`` module attribute.

        The root of the file cache will be located in the ``.builder`` directory underneath
        the provided root path.

        :param root: the path to the root of the file cache.
        """
        self._base_file_cache_path = root / '.builder'
        self._base_file_cache_path.mkdir(exist_ok=True)

    def resolve_file(self, file_url: str, relative_path: Path, optional: bool = False) -> Optional[Path]:
        """
        A function that guarantees the given remote file exists in the cache.  If the file
        could not be downloaded, then ``None`` is returned.  Otherwise, the full path to the
        file is returned.

        The file is only downloaded if it does not exist locally or if the global ``--force-fetch``
        option is in play.  If a required file cannot be cached, an exception is raised.

        :param file_url: the URL of the remote file.
        :param relative_path: the relative path where the file should be stored locally.  This
        will be relative to the file cache's root.
        :param optional: a flag noting whether the file is optional or required.
        :return: the full local path to the file or ``None``.
        :raises ValueError: if we had a problem downloading the requested file.
        """
        try:
            full_path = self._base_file_cache_path / relative_path
            if global_options.force_remote_fetch() or not full_path.is_file():
                if not self._download_file(file_url, full_path, optional):
                    return None
        except requests.HTTPError as httpError:
            raise ValueError(f'Could not cache {relative_path}: {str(httpError)}')
        return full_path

    @staticmethod
    def _download_file(url: str, full_path: Path, optional: bool) -> bool:
        """
        A function for downloading a remote file to a local one.  If the remote file
        is not found and is optional, then ``False`` is returned.  If a problem occurs
        downloading the file, an exception is raised.  Otherwise, the file is downloaded
        and ``True`` is returned.

        :param url: the URL from which the remote file is to be downloaded.
        :param full_path: the full path to which the file will be downloaded.
        :param optional: a flag noting whether the file is optional or required.
        :return: a flag noting whether or not the file was successfully downloaded.
        """
        content_length, exists = FileCache._get_download_file_size(url, optional)
        if not exists:
            return False
        response = requests.get(url, allow_redirects=True)
        response.raise_for_status()
        label = FileCache._make_label(full_path.name)

        full_path.parent.mkdir(parents=True, exist_ok=True)

        with click.progressbar(label=click.style(label, fg='white'), length=content_length, info_sep=' ',
                               width=0) as bar:
            with full_path.open('wb') as fd:
                for chunk in response.iter_content(chunk_size=1024):
                    fd.write(chunk)
                    bar.update(len(chunk))

        return True

    @staticmethod
    def _make_label(name: str, limit: int = 25) -> str:
        """
        A function that makes sure the given name is exactly a set number of characters long.
        Currently, this is set to 25.  This is used to make sure that the name of the file
        being downloaded fit on the screen.  If the name is shorter than the limit, it is
        right-justified within that limit.  If it is too long, the excess, plus 3 characters,
        is removed from the middle of the string and replaced with an ellipsis.

        :param name: the name to guarantee is the set limit characters long.
        :param limit: the limit within which the name should be formatted.  This must always
        be an odd number
        :return: the name, possibly modified to be exactly 25 characters long.
        """
        if len(name) > limit:
            size = (limit - 3) // 2
            label = f'{name[:size]}...{name[-size:]}'
        else:
            label = name.rjust(limit)
        return label

    @staticmethod
    def _get_download_file_size(url: str, optional: bool) -> Tuple[Optional[int], bool]:
        """
        A function to determine the file size, if possible, of a remote file.  We do this by
        issuing an HTTP ``HEAD`` request on the URL so we only get the headers back.  If the
        file is not optional and cannot be found, an exception is raised.

        :param url: the URL to download a file from.
        :param optional: a flag noting whether the file is optional or required.
        :return: a tuple where the first entry notes the length of the remote file.  If the
        remote file exists but its length cannot be determined, then this will be ``None``.
        The second entry in the tuple will be a boolean noting whether the file exists or not.
        :raises HTTPError: if an HTTP problem occurred getting the file's content length.
        """
        # We'll do a HEAD first to make sure the remote file is there and find out how big
        # it is.
        response = requests.head(url, allow_redirects=True)
        if optional and 400 <= response.status_code < 500:
            verbose_out(f'Could not download {url}: {response.status_code} {response.reason}')
            return None, False
        response.raise_for_status()
        return int(response.headers['Content-Length']) if 'Content-Length' in response.headers else None, True


file_cache = FileCache(Path.home())
