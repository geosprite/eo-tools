# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

import os
from pathlib import Path
from urllib.parse import urljoin
from functools import wraps
from typing import Callable

from geosprite.eo.tools.snap.core.ingest import Aria2Manager


def config_parser(conf_file: str):
    import warnings

    from configparser import ConfigParser

    parser = ConfigParser()

    if not os.path.isfile(conf_file):
        conf_file = os.path.join(os.path.dirname(__file__), conf_file)

        if not os.path.isfile(conf_file):
            warnings.warn(f"Config file '{conf_file}' not found")
            return None

    parser.read(conf_file)

    return parser


class StoreSettings:
    storage_dir: str
    base_path: str | None
    download_path: str | None
    path_filters: list[str]
    domain: str
    source_dirs: list[str] | None

    def __init__(self, conf_file: str = "store.ini"):
        import os
        import warnings
        from configparser import ConfigParser

        self.storage_dir = ""
        self.base_path = ""
        self.download_path = ""
        self.path_filters = []
        self.domain = ""
        self.source_dirs = None

        conf_file = os.environ.get("STORE_CONFIG", conf_file)

        parser = ConfigParser()

        if not os.path.isfile(conf_file):
            conf_file = os.path.join(os.path.dirname(__file__), conf_file)

            if not os.path.isfile(conf_file):
                warnings.warn(f"Config file '{conf_file}' not found")
                return

        parser.read(conf_file)

        section = "Storage"

        if parser.has_section(section):
            import re

            storage_dir = parser[section].get("storage_dir")
            base_path = parser[section].get("base_path")
            download_path = parser[section].get("download_path")
            path_filters = parser[section].get("path_filters")
            domain = parser[section].get("domain")

            if isinstance(storage_dir, str) and (storage_dir.endswith("/") or storage_dir.endswith("\\")):
                storage_dir = storage_dir[:len(storage_dir) - 1]

            self.storage_dir = os.path.normpath(storage_dir) if isinstance(storage_dir, str) and storage_dir.strip() != "" else ""
            self.base_path = os.path.normpath(base_path.strip('/')) if isinstance(base_path, str) and base_path.strip() != "" else ""
            self.download_path = os.path.normpath(download_path.strip('/')) if isinstance(download_path, str) and download_path.strip() != "" else ""
            self.path_filters = re.split('[, ]+', path_filters) if isinstance(path_filters, str) and path_filters.strip() != "" else ""
            self.domain = domain.strip('/') if isinstance(domain, str) and domain.strip() != "" else ""

        if parser.has_section("Sources"):
            self.source_dirs = [value for key, value in parser.items("Sources")]
        else:
            self.source_dirs = None

    def path(self, *paths):
        parts = [self.storage_dir, self.base_path]

        for i, p in enumerate(paths):
            if p.startswith("/"):
                parts.append(p.lstrip("/"))
            else:
                parts.append(p)

        return os.path.normpath(os.path.join(*parts))

    def url(self, path: str):
        path = path.removeprefix(os.path.normpath(os.path.join(self.storage_dir, self.base_path))).strip("/").strip("\\")

        return urljoin(self.domain, f"{self.base_path}/{os.path.normpath(path)}".replace('\\', '/'))

    def filter_path(self, path):
        import fnmatch
        from urllib.parse import urlparse

        url_path = urlparse(path).path

        if not url_path.startswith("/"):
            url_path = "/" + url_path

        for path_filter in self.path_filters:
            pattern = path_filter.rstrip('/')

            if pattern == '':
                continue

            # 情况1: 过滤器包含通配符（如/downloads/*/）
            if '*' in path_filter:
                # 使用fnmatch进行模式匹配
                if fnmatch.fnmatch(url_path, pattern) or fnmatch.fnmatch(url_path, pattern + '/*'):
                    pattern_parts = pattern.split('/')
                    url_parts = url_path.split('/')

                    match_length = 0
                    for i, (p_part, u_part) in enumerate(zip(pattern_parts, url_parts)):
                        if fnmatch.fnmatch(u_part, p_part):
                            match_length = i + 1
                        else:
                            break

                    result = '/'.join(url_parts[match_length:])
                    if result:
                        return result

            # 情况2: 过滤器以/结尾（如/downloads/）
            elif path_filter.endswith('/'):
                # 匹配并移除整个目录
                if url_path.startswith(pattern + '/'):
                    result = url_path[len(pattern) + 1:]
                    if result:  # 确保结果不为空
                        return result.lstrip('/')

            # 情况3: 简单匹配（如/downloads）
            else:
                if url_path.startswith(pattern):
                    result = url_path[len(pattern):]
                    if result or result == '':
                        return result if result != '' else '/'

        # 如果没有匹配的过滤器，返回原始路径
        return url_path


store_settings = StoreSettings()


def auto_download(urls_param: str, downloads_dir: str | None = store_settings.download_path or "", async_call: bool = False):

    def decorator(func: Callable):
        manager = Aria2Manager(store_settings.path(downloads_dir))

        from urllib.parse import urlparse
        import re

        def is_lan_url(url: str) -> bool:
            """
            快速判断URL是否为局域网地址（不进行DNS解析）
            """
            parsed = urlparse(url)
            hostname = parsed.hostname

            if not hostname:
                return False

            # 检查常见的内网地址模式
            lan_patterns = [
                # IPv4私有地址
                r'^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$',
                r'^172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3}$',
                r'^192\.168\.\d{1,3}\.\d{1,3}$',
                # 环回地址
                r'^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$',
                # 链路本地
                r'^169\.254\.\d{1,3}\.\d{1,3}$',
                # 本地主机名
                r'^localhost$',
                # 内网域名
                r'\.local$',
                r'\.localdomain$',
                r'\.internal$',
            ]

            for pattern in lan_patterns:
                if re.match(pattern, hostname):
                    return True

            return False

        @wraps(func)
        async def wrapper(*args, **kwargs):

            def run_download(urls: list[str]) -> list[str]:

                if isinstance(store_settings.source_dirs, list) and len(store_settings.source_dirs) > 0:
                    import shutil

                    source_dirs = [Path(d) for d in store_settings.source_dirs]
                    download_dir = Path(manager.options[
                                            "dir"] if manager.options is not None and "dir" in manager.options else os.curdir)

                    found_files: list[Path | None] = [None] * len(urls)
                    download_files: list[Path | None] = [None] * len(urls)

                    for i, url in enumerate(urls):
                        rel_path = urlparse(url).path.lstrip('/')
                        download_files[i] = download_dir / rel_path

                        for source_dir in source_dirs:
                            file = source_dir / rel_path

                            if file.is_file():
                                found_files[i] = file
                                break

                    if all(f is not None for f in found_files):
                        print(f"Found all files: {found_files}")
                        return [str(p) for p in found_files]

                    for found_file, download_file in zip(found_files, download_files):
                        if found_file is not None:
                            download_file.parent.mkdir(parents=True, exist_ok=True)

                            try:
                                shutil.copy(str(found_file), download_file)
                                print(f"Copy found file completed. File path: {download_file}")
                            except Exception as e:
                                print(f"Copy found file: {found_file} to {download_file} failed. Error: {e}")

                print(f"Downloading files ...: {urls}")

                if not async_call:
                    return [str(os.path.join(results["dir"], results["name"])) for results in
                            manager.download(urls, keep_dirs=True)]
                else:
                    return manager.add_urls(urls, keep_dirs=True)

            if urls_param in kwargs and all(item.startswith(('http', 'https')) and not is_lan_url(item) for item in kwargs[urls_param]):
                kwargs[urls_param] = run_download(kwargs[urls_param])

            return await func(*args, **kwargs)

        return wrapper

    return decorator
