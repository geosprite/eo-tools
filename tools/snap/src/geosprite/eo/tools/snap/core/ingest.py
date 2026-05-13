# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

import os
from urllib.parse import urlparse

import aria2p


class Aria2Manager:

    def __init__(self, download_dir: str | None = None):
        rpc_secret = os.environ.get("ARIA2_RPC_SECRET", None)

        if rpc_secret:
            client = aria2p.Client(secret=rpc_secret)
        else:
            client = aria2p.Client()

        self.aria2 = aria2p.API(client)

        self.options = {"dir": download_dir} if isinstance(download_dir, str) else None

    def download(self, urls: str | list[str], keep_dirs: bool = False) -> list:

        def on_complete(api, gid):
            for d in results:
                if d["gid"] != gid and self.aria2.get_download(d["gid"]).progress < 100.0:
                    return

            api.stop_listening()

        results = self.add_urls(urls, keep_dirs)

        self.aria2.listen_to_notifications(on_download_complete=on_complete)

        return [self.status(d["gid"]) for d in results]

    def add_urls(self, urls: str | list[str], keep_dirs: bool = False) -> list:
        downloads = []
        options = None

        if isinstance(urls, str):
            urls = [urls]

        if not isinstance(urls, list):
            raise TypeError("urls must be a list or a string.")

        for url in urls:

            if keep_dirs:
                path = os.path.dirname(urlparse(url).path[1:])

                if self.options is None:
                    options = {"dir": path}
                elif "dir" in self.options:
                    options = {"dir": os.path.join(self.options["dir"], path)}

            download = self.aria2.add_uris([url], options)

            downloads.append(download)

        return [self.status(download) for download in downloads]

    def status(self, gid: str | None = None) -> dict | list[dict]:
        results = []

        if gid is None:
            downloads = self.aria2.get_downloads()
        elif isinstance(gid, str):
            downloads = [self.aria2.get_download(gid)]
        elif isinstance(gid, aria2p.Download):
            downloads = [gid]
        else:
            raise TypeError("gid must be a str or aria2p.Download.")

        for download in downloads:
            results.append(self.to_json(download))

        return results if len(results) > 1 else results[0]

    def to_json(self, download: aria2p.Download):

        if self.options is not None and "dir" in self.options:
            path = str(download.dir).removeprefix(self.options.get("dir"))
            path = os.path.join(path[1:], download.name)
        else:
            path = None

        return {
            "gid": download.gid,
            "name": download.name,
            "status": download.status,
            "path": path,
            "dir": str(download.dir),
            "completed_length": download.completed_length,
            "total_length": download.total_length,
            "progress": download.progress,
            "progress_string": f"{download.completed_length_string()}/{download.total_length_string()} ({download.progress_string()})",
            "download_speed": download.download_speed_string()
        }
