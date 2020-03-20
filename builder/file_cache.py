"""
This file provides all our support for managing a file cache.
"""
from pathlib import Path
from typing import Optional, Tuple

import click
import requests

from builder.utils import global_options, verbose_out


class FileCache(object):
    def __init__(self):
        self._base_file_cache_path = Path.home() / '.builder'
        self._base_file_cache_path.mkdir(exist_ok=True)

    def resolve_file(self, file_url: str, relative_path: Path, optional: bool = False) -> Optional[Path]:
        full_path = self._base_file_cache_path / relative_path
        if global_options.force_remote_fetch() or not full_path.is_file():
            if not self._download_file(file_url, full_path, optional):
                return None
        return full_path

    @staticmethod
    def _download_file(url: str, full_path: Path, optional: bool) -> bool:
        content_length, exists = FileCache._get_download_file_size(url, optional)
        if not exists:
            return False
        response = requests.get(url, allow_redirects=True)
        response.raise_for_status()
        label = full_path.name
        if len(label) > 25:
            label = f'...{label[-22:]}'
        else:
            label = label.rjust(25)

        full_path.parent.mkdir(parents=True, exist_ok=True)

        with click.progressbar(label=click.style(label, fg='white'), length=content_length, info_sep=' ',
                               width=0) as bar:
            with full_path.open('wb') as fd:
                for chunk in response.iter_content(chunk_size=1024):
                    fd.write(chunk)
                    bar.update(len(chunk))

        return True

    @staticmethod
    def _get_download_file_size(url: str, optional: bool) -> Tuple[Optional[int], bool]:
        # We'll do a HEAD first to make sure the
        response = requests.head(url, allow_redirects=True)
        if optional and 400 <= response.status_code < 500:
            verbose_out(f'Could not download {url}: {response.status_code} {response.reason}')
            return None, False
        response.raise_for_status()
        return int(response.headers['Content-Length']) if 'Content-length' in response.headers else None, True


file_cache = FileCache()
