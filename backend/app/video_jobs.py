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
    if status["status"] == "completed" and "result" in status:
        status["result"]["ball_events_available"] = (folder / "ball_research/report.json").is_file()
        status["result"]["pitch_estimate_available"] = (folder / "pitch_estimate/report.json").is_file()
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


@router.get("/{job_id}/ball-events")
def ball_events(job_id: str):
    current = read_status(job_id)
    if current["status"] != "completed":
        raise HTTPException(409, "Kết quả chưa sẵn sàng.")
    path = folder_for(job_id) / "ball_research/report.json"
    if not path.is_file():
        return {"status": "not_available", "possible_passes": [], "confirmed_passes": None, "shots": None}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (payload["person_job_id"] != job_id or payload["source_sha256"] != current["result"]["source_sha256"]
                or payload["frames"] != current["result"]["frames"]):
            raise ValueError("Research/source mismatch")
        for event in payload["possible_passes"]:
            if (event["kind"] != "possible_pass" or event["status"] != "unverified"
                    or event["group"] not in ("A", "B") or event["from_id"] == event["to_id"]
                    or not 0 <= event["start_s"] < event["end_s"] <= current["result"]["frames"] / current["result"]["fps"]):
                raise ValueError("Invalid research event")
        validation = None
        audit_path = path.with_name("validation.json")
        if audit_path.is_file():
            validation = json.loads(audit_path.read_text(encoding="utf-8"))
            with path.with_name("ball.jsonl").open("rb") as stream:
                sequence_hash = hashlib.file_digest(stream, "sha256").hexdigest()
            if (validation["kind"] != "ball_sequence_development_audit_v1"
                    or validation["source_sha256"] != payload["source_sha256"]
                    or validation["person_job_id"] != job_id
                    or validation["input_sha256"]["predictions"] != hashlib.sha256(path.read_bytes()).hexdigest()
                    or validation["input_sha256"]["sequence"] != sequence_hash):
                raise ValueError("Audit/source/prediction mismatch")
            validation["independently_validated"] = False
        return {**payload, "status": "research_candidates", "confirmed_passes": None, "shots": None, "validation": validation}
    except (KeyError, ValueError, OSError) as error:
        raise HTTPException(422, "Kết quả thử nghiệm không khớp video; chưa thể hiển thị.") from error


@router.get("/{job_id}/pitch-estimate")
def pitch_estimate(job_id: str):
    current = read_status(job_id)
    if current["status"] != "completed":
        raise HTTPException(409, "Video chưa xử lý xong.")
    path = folder_for(job_id) / "pitch_estimate/report.json"
    if not path.is_file():
        return {"status": "not_available"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if (payload["person_job_id"] != job_id or payload["source_sha256"] != current["result"]["source_sha256"]
                or payload["pitch_m"] != [105, 68] or payload["origin"] != "bottom_left"):
            raise ValueError("Pitch/source mismatch")
        return {**payload, "status": "provisional_estimate", "independently_validated": False}
    except (KeyError, ValueError, OSError) as error:
        raise HTTPException(422, "Ước lượng sân không khớp nguồn video.") from error


@router.get("/{job_id}/pitch-tracking")
def pitch_tracking(job_id: str):
    from backend.common.schemas import TrackingRow
    report = pitch_estimate(job_id)
    if report["status"] != "provisional_estimate":
        raise HTTPException(404, "Chưa có tọa độ sân cho video này.")
    path = folder_for(job_id) / "pitch_estimate/tracking.jsonl"
    try:
        if path.stat().st_size > 20 * 1024 * 1024:
            raise ValueError("Tracking too large")
        if "publication" in report:
            with path.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != report["publication"]["tracking_sha256"]:
                    raise ValueError("Tracking/publication mismatch")
        rows = []
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    row = TrackingRow.model_validate_json(line)
                    if not 0 <= row.x_m <= 105 or not 0 <= row.y_m <= 68:
                        raise ValueError("Outside pitch")
                    rows.append(row.model_dump())
                    if len(rows) > 200000:
                        raise ValueError("Too many rows")
        return rows
    except (OSError, ValueError, KeyError) as error:
        raise HTTPException(422, "Không đọc được tọa độ ước lượng hợp lệ.") from error


@router.get("/{job_id}/tactics")
def spatial_tactics(job_id: str):
    """Internal video DTO, computed from source-matched calibrated positions only."""
    from backend.tactics.video_tactics import build_report
    report = pitch_estimate(job_id)
    if report["status"] != "provisional_estimate":
        return {"status": "not_available", "windows": [],
                "message": "Clip đã có tracking nhưng chưa có hiệu chỉnh sân. Cần mốc sân hợp lệ theo chuyển động camera để tính heatmap và cự ly theo mét."}
    try:
        current = read_status(job_id)["result"]
        rows = pitch_tracking(job_id)
        result = build_report(rows, report, current["fps"], current["frames"])
        result["input_sha256"] = {
            "calibration": hashlib.sha256((folder_for(job_id) / "pitch_estimate/report.json").read_bytes()).hexdigest(),
            "positions": hashlib.sha256((folder_for(job_id) / "pitch_estimate/tracking.jsonl").read_bytes()).hexdigest()}
        return result
    except (KeyError, ValueError, TypeError, OSError) as error:
        raise HTTPException(422, "Không đủ dữ liệu sân hợp lệ để phân tích chiến thuật.") from error
