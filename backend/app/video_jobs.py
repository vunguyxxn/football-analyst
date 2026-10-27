"""Local upload/job API. Image-space boxes are separate from TrackingRow."""
import asyncio
import hashlib
import json
from pathlib import Path
import re
import threading
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from backend.cv.upload_analysis import AnalysisCancelled, analyze, video_info

router = APIRouter(prefix="/api/video-jobs", tags=["video jobs"])
ROOT = Path(__file__).resolve().parents[2] / "data/processed/video_jobs"
MAX_BYTES = 500 * 1024 * 1024
_slot = threading.Lock()
_lock = threading.Lock()
_active = {}


def folder_for(job_id):
    if not re.fullmatch(r"[0-9a-f]{32}", job_id):
        raise HTTPException(404, "Không tìm thấy tác vụ.")
    return ROOT / job_id


def write_status(folder, payload):
    temporary = folder / "status.tmp"
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(folder / "status.json")


def read_status(job_id):
    folder = folder_for(job_id)
    with _lock:
        if not (folder / "status.json").is_file():
            raise HTTPException(404, "Không tìm thấy tác vụ.")
        status = json.loads((folder / "status.json").read_text(encoding="utf-8"))
        if status["status"] in ("queued", "running") and job_id not in _active:
            status.update(status="failed", stage="Xử lý đã bị gián đoạn do máy chủ khởi động lại. Hãy chọn video và thử lại.")
            write_status(folder, status)
    if status["status"] == "completed" and "result" in status and "source_sha256" not in status["result"]:
        source = next(folder.glob("source.*"), None)
        if source:
            with source.open("rb") as stream:
                status["result"]["source_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    return status


def run_job(job_id, folder, source, event):
    status = {"id": job_id, "status": "running", "progress": 0, "stage": "Đang nạp mô hình AI"}
    def update(**fields):
        status.update(fields)
        with _lock:
            write_status(folder, status)
    try:
        update()
        result = analyze(source, folder, update, event.is_set)
        if event.is_set():
            raise AnalysisCancelled()
        update(status="completed", progress=100, stage="Đã phân tích xong", result=result,
               processed_frames=result["frames"], total_frames=result["frames"])
    except AnalysisCancelled:
        update(status="cancelled", stage="Đã hủy xử lý. Bạn có thể phân tích video khác.")
    except Exception as error:
        update(status="failed", stage=f"Phân tích thất bại: {str(error)[:300]}")
    finally:
        with _lock:
            _active.pop(job_id, None)
        _slot.release()


@router.get("")
def active_jobs():
    with _lock:
        ids = list(_active)
    return [read_status(job_id) for job_id in ids]


@router.post("", status_code=202)
async def upload(request: Request, extension: str = "mp4"):
    if extension.lower() not in ("mp4", "webm", "mov", "mkv"):
        raise HTTPException(415, "Chọn MP4, WebM, MOV hoặc MKV.")
    if not _slot.acquire(blocking=False):
        raise HTTPException(409, "Máy đang xử lý video khác. Hãy chờ hoặc hủy tác vụ hiện tại.")
    folder = ROOT / uuid4().hex
    handed_off = False
    try:
        folder.mkdir(parents=True)
        source = folder / f"source.{extension.lower()}"
        size = 0
        with source.open("xb") as stream:
            async for block in request.stream():
                size += len(block)
                if size > MAX_BYTES:
                    raise HTTPException(413, "Video vượt 500 MB. Hãy chọn clip ngắn hơn.")
                stream.write(block)
        try:
            await asyncio.to_thread(video_info, source)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        job_id = folder.name
        status = dict(id=job_id, status="queued", progress=0, stage="Đã nhận video, chuẩn bị xử lý AI")
        event = threading.Event()
        with _lock:
            _active[job_id] = event
            write_status(folder, status)
        thread = threading.Thread(target=run_job, args=(job_id, folder, source, event), daemon=True)
        thread.start()
        handed_off = True
        return status
    finally:
        if not handed_off:
            with _lock:
                _active.pop(folder.name, None)
            if folder.exists():
                # Only files created in this request's UUID directory.
                for path in folder.iterdir():
                    path.unlink()
                folder.rmdir()
            _slot.release()


@router.get("/{job_id}")
def status(job_id: str):
    return read_status(job_id)


@router.post("/{job_id}/cancel")
def cancel(job_id: str):
    current = read_status(job_id)
    with _lock:
        event = _active.get(job_id)
        if event:
            event.set()
    return {"id": job_id, "cancellation_requested": event is not None, "status": current["status"]}


@router.get("/{job_id}/chunks/{index}")
def chunk(job_id: str, index: int):
    current = read_status(job_id)
    if current["status"] != "completed":
        raise HTTPException(409, "Kết quả chưa sẵn sàng.")
    if not 0 <= index < current["result"]["chunks"]:
        raise HTTPException(404, "Không có đoạn kết quả này.")
    return json.loads((folder_for(job_id) / f"chunk-{index}.json").read_text(encoding="utf-8"))


@router.get("/{job_id}/summary")
def summary(job_id: str):
    from backend.cv.tracking_summary import summarize
    current = read_status(job_id)
    if current["status"] != "completed":
        raise HTTPException(409, "Kết quả chưa sẵn sàng.")
    try:
        return summarize(folder_for(job_id), current["result"])
    except (ValueError, KeyError, OSError) as error:
        raise HTTPException(422, "Không tổng hợp được kết quả tracking. Hãy phân tích lại video.") from error
