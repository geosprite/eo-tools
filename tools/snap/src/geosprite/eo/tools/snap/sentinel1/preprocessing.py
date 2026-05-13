# Copyright (c) GeoSprite. All rights reserved.
#
# Author: JH Zhang
#

import asyncio
import os
import re
import tempfile
from urllib.parse import urlparse

from geosprite.eo.tools.snap.core.store import auto_download
from geosprite.eo.store import StoreClient


@auto_download(urls_param="inputs")
async def download(inputs: list[str]) -> list[str]:
    return inputs


_SAFE_OBJECT_RE = re.compile(r"[^A-Za-z0-9_.\-/]+")


def _safe_object_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip("/")
    normalized = _SAFE_OBJECT_RE.sub("-", normalized)
    return "/".join(part.strip(".-") or "part" for part in normalized.split("/") if part.strip("/"))


def _local_output_dir(scene_rel_path: str) -> str:
    safe_scene = _safe_object_path(scene_rel_path)
    path = os.path.join(tempfile.gettempdir(), "earth-snap", "preprocessing", safe_scene, "measurement")
    os.makedirs(path, exist_ok=True)
    return path


def _publish_output(local_path: str, scene_rel_path: str, out_name: str) -> str:
    object_key = f"earth-snap/preprocessing/{_safe_object_path(scene_rel_path)}/measurement/{_safe_object_path(out_name)}"
    return StoreClient().publish_file(
        local_path,
        object_key,
        content_type="image/tiff",
    )["url"]


async def preprocess_sentinel1(inputs: list[str]):
    """
    使用 ESA SNAP 引擎对 Sentinel-1 合成孔径雷达 (SAR) 数据进行标准化预处理。

    ### 功能说明：
    1. **自动资源发现**：根据提供的基准 URL，自动定位并下载 .safe 目录结构下的必要组件（Manifest, Measurement, Annotation）。
    2. **核心算法**：执行热噪声去除、轨道校正、辐射定标 (Calibration) 以及多普勒地形校正 (Terrain Correction)。
    3. **双极化支持**：自动识别并处理 VV 和 VH 极化数据。
    4. **幂等性检查**：如果目标文件已存在于存储中，则直接返回现有 URI。
    5. **处理量**：一次只处理一景影像，无法处理多景

    ### 参数要求 (Args):
    - **inputs** (list[str]):
        - 必须是关于manifest字符串的url。
        - 推荐格式：`["https://sentinel-s1-l1c.s3.amazonaws.com/GRD/2021/8/14/IW/DV/S1A_IW_GRDH_1SDV_20210814T231207_20210814T231232_039232_04A1BB_2997/manifest.safe"]` 。

    ### 返回结果 (Returns):
    - **dict**: 包含 `result` 键的字典，其值为处理后的 GeoTIFF 文件的完整 URI 列表。
    - 示例返回值：
      ```json
      {
          "result": [
              "http://10.168.162.112:8092/snap/preprocessing/S1A_.../measurement/iw-vv.tiff",
              "http://10.168.162.112:8092/snap/preprocessing/S1A_.../measurement/iw-vh.tiff"

          ]
      }
      ```
    """

    def normalize_scene_base(scene: str) -> str:
        scene = scene.strip()
        if scene.lower().endswith("manifest.safe"):
            scene = scene.rsplit("manifest.safe", 1)[0]

        if scene.endswith("/"):
            scene = scene[:-1]
        return scene

    try:
        from geosprite.eo.tools.snap.core.preprocessing import sentinel1
    except ImportError as e:
        raise RuntimeError(f"ESA SNAP snappy module not available: {str(e)}") from e

    # snappy可用性检查
    if not inputs or len(inputs) == 0:
        raise ValueError("Missing input. Provide either one scene base URL.")

    # 输入合法性检查
    if len(inputs) == 1:
        scene_base = normalize_scene_base(inputs[0])

        if not scene_base.startswith(("http", "https")):
            raise ValueError("In new mode, input must be a http/https scene base URL.")

        suffixes = [
            "manifest.safe",
            "preview/quick-look.png",
            "measurement/iw-vv.tiff",
            "measurement/iw-vh.tiff",
            "annotation/calibration/noise-iw-vv.xml",
            "annotation/calibration/noise-iw-vh.xml",
            "annotation/calibration/calibration-iw-vv.xml",
            "annotation/calibration/calibration-iw-vh.xml",
            "annotation/iw-vv.xml",
            "annotation/iw-vh.xml",
        ]
        urls = [f"{scene_base}/{s}" for s in suffixes]
        downloaded = await download(inputs=urls)

        manifest_path = downloaded[suffixes.index("manifest.safe")]
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Manifest file not found after download: {manifest_path}")

        # Output path: temp/earth-snap/preprocessing/<scene_rel_path>/measurement,
        # published to shared MinIO through eo-store.
        scene_rel_path = urlparse(scene_base).path.lstrip("/")
        output_dir = _local_output_dir(scene_rel_path)

        # Determine available polarizations by checking downloaded measurement files
        polarizations: list[str] = []
        if os.path.isfile(downloaded[suffixes.index("measurement/iw-vv.tiff")]):
            polarizations.append("VV")
        if os.path.isfile(downloaded[suffixes.index("measurement/iw-vh.tiff")]):
            polarizations.append("VH")
        if len(polarizations) == 0:
            polarizations = ["VV", "VH"]

        desired_name_by_pol = {
            "VV": "iw-vv.tiff",
            "VH": "iw-vh.tiff",
        }

        try:
            result_uris: list[str] = []
            for pol in polarizations:
                out_name = desired_name_by_pol.get(pol, f"iw-{pol.lower()}.tiff")
                out_path = os.path.join(output_dir, out_name)

                if os.path.isfile(out_path):
                    result_uris.append(_publish_output(out_path, scene_rel_path, out_name))
                    continue

                # Run SNAP in a worker thread so the asyncio loop keeps serving GET / (K8s probes).
                generated_files = await asyncio.to_thread(
                    sentinel1.preprocess,
                    input_file=manifest_path,
                    polar_list=[pol],
                    output_dir=output_dir,
                )

                if not generated_files:
                    raise RuntimeError(f"SNAP preprocessing produced no output for polarization {pol}")

                generated = generated_files[0]
                if os.path.normpath(generated) != os.path.normpath(out_path):
                    if os.path.isfile(out_path):
                        os.remove(out_path)
                    os.rename(generated, out_path)

                result_uris.append(_publish_output(out_path, scene_rel_path, out_name))

            return {"result": result_uris}
        except Exception as e:
            raise RuntimeError(f"Preprocessing failed: {str(e)}") from e

    return None
