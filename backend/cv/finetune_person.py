"""Controlled YOLO11n experiment; person-only fair baseline and held-out test."""
from __future__ import annotations

import argparse
import contextlib
import gc
import json
import os
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter

from backend.cv.prepare_person_dataset import canonical_path, dataset_yaml, sha256


def person_validator_class():
    # Installed 8.3.221 DetectionValidator ignores args.classes in postprocess.
    # Filter before class-agnostic NMS, so a ball/car prediction cannot suppress
    # a person or become a person through single_cls evaluation.
    from ultralytics.models.yolo.detect.val import DetectionValidator
    from ultralytics.utils import nms

    class PersonValidator(DetectionValidator):
        def postprocess(self, preds):
            outputs = nms.non_max_suppression(
                preds, self.args.conf, self.args.iou, classes=[0],
                nc=0 if self.args.task == "detect" else self.nc, multi_label=True,
                agnostic=True, max_det=self.args.max_det, end2end=self.end2end,
                rotated=self.args.task == "obb")
            return [{"bboxes": x[:, :4], "conf": x[:, 4], "cls": x[:, 5], "extra": x[:, 6:]} for x in outputs]
    return PersonValidator


def verify_dataset(dataset):
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    if (dataset / "data.yaml").read_text(encoding="utf-8") != dataset_yaml(dataset):
        raise ValueError("Dataset YAML differs from verified paths/classes")
    seen_components, seen_pixels = {}, {}
    for record in manifest["files"]:
        for key, digest_key in (("image", "image_sha256"), ("label", "label_sha256")):
            path = canonical_path(dataset / record[key])
            if not path.is_relative_to(canonical_path(dataset)) or sha256(path) != record[digest_key]:
                raise ValueError("Dataset artifact hash/path mismatch")
        split = record["split"]
        for seen, key in ((seen_components, record["component"]), (seen_pixels, record["pixel_sha256"])):
            if key in seen and seen[key] != split:
                raise ValueError("Train/val/test leakage")
            seen[key] = split
    if set(manifest["images"]) != {"train", "val", "test"}:
        raise ValueError("Need train, val and held-out test")
    return manifest


def run(dataset, weights, output, protocol, root):
    if output.exists():
        raise FileExistsError(output)
    manifest = verify_dataset(dataset)
    if manifest["protocol"] != protocol:
        raise ValueError("Dataset and training protocol differ")
    os.environ["YOLO_CONFIG_DIR"] = str(root / "data/processed")
    os.environ["MPLCONFIGDIR"] = str(root / ".tmp/matplotlib")
    os.environ["TORCH_HOME"] = str(root / "data/processed/.torch")
    os.environ["YOLO_AUTOINSTALL"] = "false"
    os.environ["WANDB_DISABLED"] = "true"
    os.environ["COMET_MODE"] = "DISABLED"
    font = Path("C:/Windows/Fonts/arial.ttf")
    target_font = root / "data/processed/Arial.ttf"
    if font.exists() and not target_font.exists():
        shutil.copyfile(font, target_font)
    import torch
    import ultralytics
    from ultralytics import YOLO
    from ultralytics.utils import SETTINGS
    SETTINGS.update({k: False for k in ("sync", "wandb", "mlflow", "comet", "clearml", "dvc", "hub", "neptune") if k in SETTINGS})
    if not torch.cuda.is_available():
        raise RuntimeError("This experiment requires CUDA; do not silently switch to CPU")
    torch.set_num_threads(4)
    initial_hash = sha256(weights)
    output.mkdir(parents=True)
    console = sys.stdout
    started = perf_counter()
    configuration = {"protocol": protocol, "dataset_manifest_sha256": sha256(dataset / "manifest.json"),
                     "dataset_yaml_sha256": sha256(dataset / "data.yaml"), "initial_weights_sha256": initial_hash,
                     "initial_weights": weights.relative_to(root).as_posix(), "python": platform.python_version(),
                     "torch": torch.__version__, "ultralytics": ultralytics.__version__,
                     "cuda": torch.version.cuda, "gpu": torch.cuda.get_device_name(0), "status": "running"}
    (output / "configuration.json").write_text(json.dumps(configuration, indent=2), encoding="utf-8")
    validator = person_validator_class()

    def evaluate(path, split, name):
        model = YOLO(str(path))
        if model.names.get(0) != "person":
            raise ValueError("Class 0 must mean person for both models")
        metrics = model.val(validator=validator, data=str(dataset / "data.yaml"), split=split,
                            imgsz=protocol["image_size"], batch=protocol["batch"], workers=0,
                            device=0, half=False, single_cls=True, conf=protocol["test_confidence"],
                            iou=protocol["test_nms_iou"], max_det=protocol["test_max_detections"],
                            plots=False, save_json=False, verbose=False, project=str(output / "evaluation"), name=name)
        return {"map50": float(metrics.box.map50), "map50_95": float(metrics.box.map),
                "precision": float(metrics.box.mp), "recall": float(metrics.box.mr)}

    try:
        with (output / "run.log").open("w", encoding="utf-8") as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            print("baseline validation smoke check", file=console, flush=True)
            baseline_val = evaluate(weights, "val", "baseline_val")
            print("training 15 epochs; test remains unused", file=console, flush=True)
            training = YOLO(str(weights))
            def progress(trainer):
                payload = {"epoch": trainer.epoch + 1, "epochs": protocol["epochs"],
                           "metrics": {k: float(v) for k, v in trainer.metrics.items()}}
                (output / "progress.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
                print(f"epoch {trainer.epoch + 1}/{protocol['epochs']}", file=console, flush=True)
            training.add_callback("on_fit_epoch_end", progress)
            training.train(data=str(dataset / "data.yaml"), epochs=protocol["epochs"],
                           batch=protocol["batch"], imgsz=protocol["image_size"], device=0,
                           workers=protocol["workers"], amp=protocol["amp"], seed=protocol["seed"],
                           deterministic=True, optimizer=protocol["optimizer"], lr0=protocol["lr0"],
                           warmup_epochs=1., patience=protocol["epochs"], mosaic=.5, close_mosaic=2,
                           cache=False, plots=False, save=True, project=str(output), name="training",
                           exist_ok=False, verbose=False)
            best = Path(training.trainer.best)
            del training
            gc.collect()
            torch.cuda.empty_cache()
            print("held-out test: unchanged baseline and best validation checkpoint", file=console, flush=True)
            before = evaluate(weights, "test", "baseline_test")
            after = evaluate(best, "test", "finetuned_test")
        if sha256(weights) != initial_hash:
            raise ValueError("Baseline weights changed during experiment")
        configuration["status"] = "complete"
        report = {"kind": "yolo_person_finetune_comparison_v1", "configuration": configuration,
                  "dataset_images": manifest["images"], "group_audit": manifest["group_audit"],
                  "baseline_validation": baseline_val, "baseline_test": before, "finetuned_test": after,
                  "test_delta": {k: after[k] - before[k] for k in before},
                  "best_weights": best.relative_to(root).as_posix(), "best_weights_sha256": sha256(best),
                  "elapsed_s": perf_counter() - started, "pipeline_promoted": False,
                  "limitations": [manifest["limitation"], "Person detection only; no ball, role classification or tracking accuracy claim",
                                  "Same held-out images and person-only filtering before NMS for both models",
                                  "One seeded run; no independent match identity or confidence interval"]}
        (output / "comparison.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
        (output / "configuration.json").write_text(json.dumps(configuration, indent=2), encoding="utf-8")
        print(json.dumps({"baseline_test": before, "finetuned_test": after, "test_delta": report["test_delta"]}), flush=True)
        return report
    except Exception as error:
        configuration.update(status="failed", error=f"{type(error).__name__}: {error}")
        (output / "configuration.json").write_text(json.dumps(configuration, indent=2), encoding="utf-8")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--weights", type=Path, default=Path("data/raw/yolo11n.pt"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    dataset, weights, output = args.dataset.resolve(), args.weights.resolve(), args.output.resolve()
    if any(not p.is_relative_to(root) for p in (dataset, weights, output)) or output.exists():
        parser.error("All paths must stay inside project; output must be new")
    protocol = json.loads((root / "docs/fixtures/yolo_person_finetune_protocol.json").read_text())
    run(dataset, weights, output, protocol, root)


if __name__ == "__main__":
    main()
