"""Train nano/small role heads; select on validation before opening test."""
from __future__ import annotations

import argparse
import contextlib
import gc
import json
import os
from pathlib import Path
import platform
import sys
from time import perf_counter

from backend.cv.evaluate_role_detector import checked, digest
from backend.cv.prepare_role_dataset import NAMES, verify_dataset


def write_json(path, value):
    temporary = path.with_suffix(".partial")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def setup(root):
    os.environ["YOLO_CONFIG_DIR"] = str(root / ".tmp/ultralytics")
    os.environ["MPLCONFIGDIR"] = str(root / ".tmp/matplotlib")
    os.environ["YOLO_AUTOINSTALL"] = "false"
    os.environ["WANDB_DISABLED"] = "true"
    os.environ["COMET_MODE"] = "DISABLED"
    import torch
    from ultralytics.utils import SETTINGS
    SETTINGS.update({key: False for key in ("sync", "wandb", "mlflow", "comet", "clearml", "dvc", "hub", "neptune") if key in SETTINGS})
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required; no silent CPU fallback")
    torch.set_num_threads(4)
    return torch


def metric_report(metrics):
    per_class = {name: {"precision": 0., "recall": 0., "map50": 0., "map50_95": 0.} for name in NAMES}
    for index, class_id in enumerate(metrics.box.ap_class_index):
        values = metrics.box.class_result(index)
        per_class[NAMES[int(class_id)]] = dict(zip(("precision", "recall", "map50", "map50_95"), map(float, values)))
    return {"map50": float(metrics.box.map50), "map50_95": float(metrics.box.map), "classes": per_class}


def evaluate(path, dataset, protocol, output, split, name):
    from ultralytics import YOLO
    model = YOLO(str(path))
    if list(model.names.values()) != NAMES:
        raise ValueError("Role class map differs from dataset")
    metrics = model.val(data=str(dataset / "data.yaml"), split=split, imgsz=protocol["image_size"], batch=protocol["batch"],
                        workers=0, device=0, half=False, single_cls=False, conf=protocol["test_confidence"],
                        iou=protocol["test_nms_iou"], max_det=protocol["max_detections"], plots=False,
                        save_json=False, verbose=False, project=str(output), name=name)
    return metric_report(metrics)


def train_one(root, dataset, protocol_path, output, model_id):
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    manifest = verify_dataset(root, dataset, protocol_path)
    model_spec = next(item for item in protocol["models"] if item["id"] == model_id)
    weights = checked(root, model_spec["path"], model_spec["sha256"])
    if output.exists():
        raise FileExistsError(output)
    torch = setup(root)
    import ultralytics
    from ultralytics import YOLO
    output.mkdir(parents=True)
    status = {"model_id": model_id, "status": "running", "protocol_sha256": digest(protocol_path),
              "manifest_sha256": digest(dataset / "manifest.json"), "initial_weights_sha256": digest(weights),
              "python": platform.python_version(), "torch": torch.__version__, "ultralytics": ultralytics.__version__,
              "gpu": torch.cuda.get_device_name(0), "test_opened": False}
    write_json(output / "status.json", status)
    console, started = sys.stdout, perf_counter()
    try:
        with (output / "run.log").open("w", encoding="utf-8") as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            training = YOLO(str(weights))
            torch.cuda.reset_peak_memory_stats()
            def progress(trainer):
                write_json(output / "progress.json", {"epoch": trainer.epoch+1, "epochs": protocol["epochs"],
                           "elapsed_s": perf_counter()-started, "metrics": {key: float(value) for key, value in trainer.metrics.items()}})
                print(f"{model_id}: epoch {trainer.epoch+1}/{protocol['epochs']}", file=console, flush=True)
            training.add_callback("on_fit_epoch_end", progress)
            training.train(data=str(dataset / "data.yaml"), epochs=protocol["epochs"], imgsz=protocol["image_size"],
                           batch=protocol["batch"], device=0, workers=0, amp=protocol["amp"], seed=protocol["seed"],
                           deterministic=True, optimizer=protocol["optimizer"], lr0=protocol["lr0"], warmup_epochs=1.,
                           patience=protocol["epochs"], mosaic=protocol["mosaic"], close_mosaic=protocol["close_mosaic"],
                           cache=False, plots=False, project=str(output), name="training", exist_ok=False, verbose=False)
            best = Path(training.trainer.best)
            status["peak_allocated_mib"] = torch.cuda.max_memory_allocated()/1024**2
            del training
            gc.collect()
            torch.cuda.empty_cache()
            validation = evaluate(best, dataset, protocol, output, "val", "selected_validation")
        verify_dataset(root, dataset, protocol_path)
        if digest(weights) != model_spec["sha256"]:
            raise ValueError("Initial weights changed")
        status.update(status="complete", elapsed_s=perf_counter()-started, images=manifest["images"], validation=validation,
                      best_weights=best.relative_to(root).as_posix(), best_weights_sha256=digest(best))
        write_json(output / "status.json", status)
        return status
    except Exception as error:
        status.update(status="failed", error=f"{type(error).__name__}: {error}")
        write_json(output / "status.json", status)
        raise


def final_test(root, dataset, protocol_path, runs, output):
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    manifest = verify_dataset(root, dataset, protocol_path)
    statuses = [json.loads((path / "status.json").read_text()) for path in runs]
    if {s["model_id"] for s in statuses} != {item["id"] for item in protocol["models"]} or len(statuses) != len(protocol["models"]):
        raise ValueError("Need exactly the two locked architectures before test")
    for status in statuses:
        if status["status"] != "complete" or status["protocol_sha256"] != digest(protocol_path) or status["manifest_sha256"] != digest(dataset / "manifest.json"):
            raise ValueError("Incomplete/stale training run")
        checked(root, status["best_weights"], status["best_weights_sha256"])
    # Freeze model preference before any test image is opened by this function.
    preference = max(statuses, key=lambda s: s["validation"]["map50_95"])["model_id"]
    if output.exists():
        raise FileExistsError(output)
    torch = setup(root)
    output.mkdir(parents=True)
    write_json(output / "selection-before-test.json", {"preferred_by_validation": preference, "statuses_sha256": [digest(path / "status.json") for path in runs]})
    reports = []
    with (output / "evaluation.log").open("w", encoding="utf-8") as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        for status in statuses:
            weights = checked(root, status["best_weights"], status["best_weights_sha256"])
            metrics = evaluate(weights, dataset, protocol, output, "test", status["model_id"]+"_test")
            reports.append({**status, "heldout_test": metrics, "test_opened": True})
            gc.collect()
            torch.cuda.empty_cache()
    verify_dataset(root, dataset, protocol_path)
    result = {"kind": "role_finetune_result_v1", "protocol_sha256": digest(protocol_path),
              "manifest_sha256": digest(dataset / "manifest.json"), "images": manifest["images"],
              "preferred_by_validation": preference, "models": reports, "pipeline_promoted": False,
              "limitation": manifest["limitation"], "independently_validated": False}
    write_json(output / "result.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["train", "test"])
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", choices=["nano", "small"])
    parser.add_argument("--runs", nargs="*", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    dataset, output = args.dataset.resolve(), args.output.resolve()
    if any(not path.is_relative_to(root) for path in [dataset, output]+[p.resolve() for p in (args.runs or [])]):
        raise ValueError("All experiment artifacts must stay in workspace")
    protocol = checked(root, args.protocol)
    if args.action == "train":
        if not args.model:
            parser.error("train requires --model")
        train_one(root, dataset, protocol, output, args.model)
    else:
        final_test(root, dataset, protocol, [path.resolve() for path in (args.runs or [])], output)
