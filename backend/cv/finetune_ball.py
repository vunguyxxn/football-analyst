"""Pinned single-class ball experiment; no changes to production person model."""
import argparse
from collections import Counter
import contextlib
import gc
import json
import os
from pathlib import Path
import shutil
from time import perf_counter

from backend.cv.prepare_person_dataset import sha256

ROOT = Path(__file__).resolve().parents[2]


def ball_labels(text):
    from backend.cv.prepare_person_dataset import convert_labels
    convert_labels(text)  # validate every original class and normalized box
    return "".join(line.strip() + "\n" for line in text.splitlines() if line.strip() and line.split()[0] == "0")


def prepare(output):
    if output.exists():
        raise FileExistsError(output)
    source = ROOT / "data/raw/football_detection_source_v1"
    manifest = json.loads((ROOT / "data/processed/yolo_person_dataset_v1/manifest.json").read_text(encoding="utf-8"))
    records, seen, balls = [], {}, Counter()
    for record in manifest["files"]:
        split, component = record["split"], record["component"]
        if component in seen and seen[component] != split:
            raise ValueError("Source group leakage")
        seen[component] = split
        image, label = (source / record["source_image"]).resolve(), (source / record["source_label"]).resolve()
        if not image.is_relative_to(source.resolve()) or not label.is_relative_to(source.resolve()):
            raise ValueError("Source paths must remain in verified dataset")
        if sha256(image) != record["image_sha256"] or sha256(label) != record["source_label_sha256"]:
            raise ValueError("Original image/label hash mismatch")
        converted = ball_labels(label.read_text(encoding="utf-8"))
        target_image = output / "images" / split / image.name
        target_label = output / "labels" / split / label.name
        target_image.parent.mkdir(parents=True, exist_ok=True)
        target_label.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(image, target_image)
        target_label.write_text(converted, encoding="utf-8")
        balls[split] += len(converted.splitlines())
        records.append({"image": target_image.relative_to(output).as_posix(), "label": target_label.relative_to(output).as_posix(),
                        "split": split, "component": component, "image_sha256": sha256(target_image), "label_sha256": sha256(target_label)})
    (output / "data.yaml").write_text(f"path: {json.dumps(output.as_posix())}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: ball\n", encoding="utf-8")
    payload = {"images": dict(Counter(record["split"] for record in records)), "balls": dict(balls), "files": records,
               "source_protocol": manifest["protocol"], "limitation": manifest["limitation"]}
    (output / "manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def ball_validator_class(class_id):
    from ultralytics.models.yolo.detect.val import DetectionValidator
    from ultralytics.utils import nms
    class BallValidator(DetectionValidator):
        def postprocess(self, preds):
            outputs = nms.non_max_suppression(preds, self.args.conf, self.args.iou, classes=[class_id],
                                            nc=0 if self.args.task == "detect" else self.nc,
                                            multi_label=True, agnostic=True, max_det=self.args.max_det,
                                            end2end=self.end2end, rotated=self.args.task == "obb")
            for boxes in outputs:
                boxes[:, 5] = 0  # COCO 32 and fine-tuned 0 both map to dataset ball
            return [{"bboxes": x[:, :4], "conf": x[:, 4], "cls": x[:, 5], "extra": x[:, 6:]} for x in outputs]
    return BallValidator


def run(output):
    output = output.resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise ValueError("Use a new workspace output")
    os.environ.update(YOLO_CONFIG_DIR=str(ROOT / "data/processed"), MPLCONFIGDIR=str(ROOT / ".tmp/matplotlib"),
                      TORCH_HOME=str(ROOT / "data/processed/.torch"), YOLO_AUTOINSTALL="false", WANDB_DISABLED="true", COMET_MODE="DISABLED")
    import torch
    from ultralytics import YOLO
    from ultralytics.utils import SETTINGS
    SETTINGS.update({key: False for key in ("sync", "wandb", "mlflow", "comet", "clearml", "dvc", "neptune", "hub", "tensorboard")})
    if not torch.cuda.is_available():
        raise ValueError("This controlled training run requires CUDA")
    protocol = json.loads((ROOT / "docs/fixtures/yolo_ball_protocol_v1.json").read_text())
    weights = ROOT / "data/raw/yolo11n.pt"
    weights_hash = sha256(weights)
    output.mkdir(parents=True)
    dataset = output / "dataset"
    manifest = prepare(dataset)
    (output / "protocol.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    started = perf_counter()
    def evaluate(path, class_id, split, name):
        model = YOLO(str(path))
        if model.names[class_id] not in ("sports ball", "ball"):
            raise ValueError("Ball class mismatch")
        metrics = model.val(validator=ball_validator_class(class_id), data=str(dataset / "data.yaml"), split=split,
                            imgsz=protocol["image_size"], batch=protocol["batch"], device=0, workers=0,
                            half=False, single_cls=True, conf=protocol["test_confidence"], iou=protocol["test_iou"],
                            plots=False, save_json=False, verbose=False, project=str(output / "evaluation"), name=name)
        return {"map50": float(metrics.box.map50), "map50_95": float(metrics.box.map),
                "precision": float(metrics.box.mp), "recall": float(metrics.box.mr)}
    try:
        with (output / "run.log").open("w", encoding="utf-8") as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            baseline_validation = evaluate(weights, 32, "val", "baseline_val")
            model = YOLO(str(weights))
            def progress(trainer):
                (output / "progress.json").write_text(json.dumps({"epoch": trainer.epoch + 1, "epochs": protocol["epochs"],
                    "metrics": {key: float(value) for key, value in trainer.metrics.items()}}, indent=2), encoding="utf-8")
            model.add_callback("on_fit_epoch_end", progress)
            model.train(data=str(dataset / "data.yaml"), epochs=protocol["epochs"], batch=protocol["batch"],
                        imgsz=protocol["image_size"], device=0, workers=0, amp=False, cache=False, plots=False,
                        seed=protocol["seed"], deterministic=True, optimizer=protocol["optimizer"], lr0=protocol["lr0"],
                        warmup_epochs=1., patience=protocol["epochs"], mosaic=.5, close_mosaic=2,
                        project=str(output), name="training", exist_ok=False, verbose=False)
            best = Path(model.trainer.best)
            del model
            gc.collect()
            torch.cuda.empty_cache()
            baseline_test = evaluate(weights, 32, "test", "baseline_test")
            finetuned_test = evaluate(best, 0, "test", "finetuned_test")
        if sha256(weights) != weights_hash:
            raise ValueError("Original weights changed")
        report = {"kind": "ball_finetune_comparison_v1", "protocol": protocol,
                  "images": manifest["images"], "balls": manifest["balls"], "baseline_validation": baseline_validation,
                  "baseline_test": baseline_test, "finetuned_test": finetuned_test,
                  "best_weights": best.relative_to(ROOT).as_posix(), "best_sha256": sha256(best),
                  "original_sha256": weights_hash, "elapsed_s": perf_counter() - started,
                  "limitation": manifest["limitation"], "pipeline_promoted": False}
        (output / "comparison.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
        return report
    except Exception as error:
        (output / "error.json").write_text(json.dumps({"error": str(error)}), encoding="utf-8")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.output)), flush=True)
