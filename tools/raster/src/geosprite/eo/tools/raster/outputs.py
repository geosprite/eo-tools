import os
import re
import tempfile
import uuid
from datetime import datetime, timezone

from geosprite.eo.store import StoreClient


_SAFE_PATH_RE = re.compile(r"[^A-Za-z0-9_.-/]+")


def _safe_output(value: str) -> str:
    value = value.replace("\\", "/").strip("/")
    value = _SAFE_PATH_RE.sub("-", value)
    return value or "output.tif"


def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _new_run_id() -> str:
    return uuid.uuid4().hex[:8]


def _parts_from_local_path(local_path: str) -> tuple[str, str, str, str]:
    normalized = os.path.normpath(local_path)
    output = os.path.basename(normalized)
    run_dir = os.path.dirname(normalized)
    run_id = os.path.basename(run_dir)
    date_dir = os.path.dirname(run_dir)
    date_key = os.path.basename(date_dir)
    operation_dir = os.path.dirname(date_dir)
    operation = os.path.basename(operation_dir)
    return operation, date_key, run_id, output


def local_output_path(operation: str, output: str, run_id: str | None = None) -> str:
    safe_operation = _safe_output(operation)
    safe_output = _safe_output(output)
    date_key = _today_key()
    run_id = _safe_output(run_id or _new_run_id())
    path = os.path.join(
        tempfile.gettempdir(),
        "earth-raster",
        safe_operation,
        date_key,
        run_id,
        safe_output,
    )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def result_object_key(
    operation: str,
    output: str,
    *,
    date_key: str | None = None,
    run_id: str | None = None,
) -> str:
    safe_operation = _safe_output(operation)
    safe_output = _safe_output(output)
    date_key = _safe_output(date_key or _today_key())
    run_id = _safe_output(run_id or _new_run_id())
    return f"earth-raster/{safe_operation}/{date_key}/{run_id}/{safe_output}"


def publish_output(local_path: str, operation: str, output: str) -> str:
    _, date_key, run_id, _ = _parts_from_local_path(local_path)
    object_key = result_object_key(operation, output, date_key=date_key, run_id=run_id)
    return StoreClient().publish_file(
        local_path,
        object_key,
        content_type="image/tiff",
    )["url"]


__all__ = ["local_output_path", "publish_output", "result_object_key"]
