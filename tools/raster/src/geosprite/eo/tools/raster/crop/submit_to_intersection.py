from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
import threading
import time
import traceback
from typing import Any
import uuid

from pydantic import BaseModel, Field

from geosprite.eo.jobs import JobState, JobStatus
from geosprite.eo.tools import ToolContext, tool

from ..common import BaseRasterTool, raster_asset
from .core import (
    RasterItem,
    crop_group_to_intersection,
    crop_output_url,
    output_folder,
    prepare_items_for_crop,
    publish_crop_files,
)

_MAX_WORKERS = int(os.environ.get("EARTH_RASTER_CROP_MAX_WORKERS", "2"))
_JOBS: dict[str, dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()
_EXECUTOR = ThreadPoolExecutor(max_workers=_MAX_WORKERS)


class CropJobItem(BaseModel):
    name: str = Field(description="Logical item name used as the item key in results")
    assets: dict[str, str | dict] = Field(description="Band name to raster path, remote URL, or asset descriptor")
    id: str | None = Field(default=None, description="Original catalog item id")
    collection: str | None = Field(default=None, description="Original catalog collection")
    datetime: str | None = Field(default=None, description="Item acquisition datetime")
    tile: str | None = Field(default=None, description="Spatial tile/path-row token")
    geometry: dict | None = Field(default=None, description="Original catalog item geometry in WGS84")

    def to_model(self) -> RasterItem:
        return RasterItem(
            name=self.name,
            assets=dict(self.assets),
            item_id=self.id,
            collection=self.collection,
            datetime=self.datetime,
            tile=self.tile,
            geometry=self.geometry,
        )


class CropToIntersectionJobIn(BaseModel):
    items: list[CropJobItem]
    spatial_key: str
    time_key: str
    anchor_item: str | None = None
    resampling: str = "bicubic"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _items_by_name(items: list[CropJobItem]) -> dict[str, RasterItem]:
    return {item.name: item.to_model() for item in items}


def _extent_payload(extent) -> dict[str, Any]:
    return {
        "anchor_item": extent.anchor_item,
        "crs": extent.crs,
        "bounds": extent.bounds,
        "intersection_wgs84": extent.intersection_wgs84,
    }


def _assets_by_item(urls_by_item: dict[str, dict[str, str]]) -> dict[str, Any]:
    return {
        item_name: [
            raster_asset(url, title=band, band=band).model_dump(mode="json")
            for band, url in urls.items()
        ]
        for item_name, urls in urls_by_item.items()
    }


def _run_crop_to_intersection(inputs: CropToIntersectionJobIn) -> dict[str, Any]:
    items = prepare_items_for_crop(_items_by_name(inputs.items))
    local_output_folder = output_folder(inputs.spatial_key, inputs.time_key)
    result = crop_group_to_intersection(
        items_by_name=items,
        output_folder=local_output_folder,
        spatial_key=inputs.spatial_key,
        time_key=inputs.time_key,
        anchor_item=inputs.anchor_item,
        resampling=inputs.resampling,
    )
    urls_by_item = publish_crop_files(result.files_by_item, spatial_key=result.spatial_key, time_key=result.time_key)
    return {
        "spatial_key": result.spatial_key,
        "time_key": result.time_key,
        "output_folder": crop_output_url(result.spatial_key, result.time_key),
        "extent": _extent_payload(result.extent),
        "assets_by_item": _assets_by_item(urls_by_item),
    }


def _set_job(job_id: str, **updates: Any) -> None:
    with _JOBS_LOCK:
        job = _JOBS[job_id]
        job.update(updates)
        job["updated_at"] = _now()


def _run_crop_to_intersection_job(job_id: str, payload_data: dict[str, Any]) -> None:
    started = time.perf_counter()
    try:
        payload = CropToIntersectionJobIn.model_validate(payload_data)
        _set_job(job_id, status="running", phase="cropping", message="Computing common extent and cropping rasters")
        result = _run_crop_to_intersection(payload)
        _set_job(
            job_id,
            status="succeeded",
            phase="done",
            message="Crop job completed",
            finished_at=_now(),
            duration_seconds=round(time.perf_counter() - started, 3),
            result=result,
        )
    except Exception as exc:
        _set_job(
            job_id,
            status="failed",
            phase="failed",
            message=str(exc),
            error={"type": exc.__class__.__name__, "message": str(exc), "traceback": traceback.format_exc()},
            finished_at=_now(),
            duration_seconds=round(time.perf_counter() - started, 3),
        )


@tool
class CropToIntersectionJobTool(BaseRasterTool):
    name = "raster.crop_submit_to_intersection"
    domain = "raster"
    summary = "Submit crop-to-intersection job."
    description = "Submits an asynchronous crop-to-intersection job and returns the job status object."
    InputModel = CropToIntersectionJobIn
    OutputModel = JobStatus

    async def run(self, ctx: ToolContext, inputs: CropToIntersectionJobIn) -> JobStatus:
        ctx.logger.info("raster.crop_submit_to_intersection item_count=%s", len(inputs.items))
        job_id = f"crop-{uuid.uuid4().hex[:12]}"
        submitted_at = datetime.now(timezone.utc)
        with _JOBS_LOCK:
            _JOBS[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "phase": "queued",
                "message": "Waiting for a crop worker",
                "created_at": submitted_at.isoformat(),
                "updated_at": submitted_at.isoformat(),
                "request": {
                    "spatial_key": inputs.spatial_key,
                    "time_key": inputs.time_key,
                    "item_count": len(inputs.items),
                    "asset_count": sum(len(item.assets) for item in inputs.items),
                },
                "result": None,
                "error": None,
            }
        _EXECUTOR.submit(_run_crop_to_intersection_job, job_id, inputs.model_dump(mode="json"))
        return JobStatus(
            job_id=job_id,
            state=JobState.QUEUED,
            progress=None,
            submitted_at=submitted_at,
            message="Waiting for a crop worker",
        )
