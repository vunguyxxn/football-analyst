# Huấn luyện small v14 và đối chiếu v6/v11

Ngày 05/11/2026. Một cấu hình, một seed, ngoại tuyến; không đổi model ứng dụng.

## Cấu hình và bằng chứng khóa

Giữ nguyên dataset/protocol/parent ledger v14. Snapshot train riêng có manifest byte-identical,418 lượt train/324 đơn vị pixel–label/260 ảnh-khung nguồn;128val/35known test không đổi ảnh/nhãn/hash. Mỗi ROI mới1 lượt; ảnh29 vùng sân và âm chung parent,79/186 chung nhóm WOB–RBL. Không đổi repeats hoặc nhãn.

Plan giữ `training_started=false` như ảnh chụp trước chạy; trạng thái hiện tại là `small/status.json: complete`. Plan khóa hash trước train; preflight không có job train khác. COCO YOLO11s fresh AdamW20epoch640/batch4/FP32/lr0.0003/seed20261102/workers0/mosaic0.5/close_mosaic3/multi_scale=False. Giữ warmup1,deterministic=True,cache=False và mọi giá trị mặc định thực tế của v11. Không resume, không train thêm lần hai.

Cấu hình thực tế chỉ khác v11 ba đường dẫn data/project/save_dir. Python3.11.3,torch2.8.0+cu128,Ultralytics8.3.221;NVIDIA GeForce RTX 3050 6GB Laptop GPU. Train kèm selected-validation cuối: **946.60s**; CUDA peak allocated **3000.16MiB**, không phải tổng VRAM thiết bị. GPU danh định6144MiB. CSV20epoch hoàn tất; best fitness ở epoch17 theo mAP50-95 của Ultralytics8.3.221, không theo known test.

Weights SHA256: `8e5d7e812c517302261761c374c660a9eea5b05c93c789e7526ee00dc50b59cc`.
Plan SHA256: `34cacedc239532dddb094fd95c1c99ffc9d2ddcf542846d1baab67a871fa5ae0`.
Protocol SHA256: `1f25d9d504c4c56b3160cb1b560dfec16e145223cb8b092084a73decf37e54ab`.
Manifest SHA256: `36ccf26608d992315715b6fd3b58d37e71d1b9fecd0ec10603834b5e4049933f`.

AP dùng conf0.001; chấm vận hành conf0.25,NMSIoU0.7,matchingIoU0.5,max_det300,FP32,không cross-role dedup. Khóa kết luận validation/gate ở640 đối chiếu v6 trước mọi inference35 known regression test. **Không inference match128057**; chỉ val/test của snapshot được truyền cho evaluator. Plan phạm vi phiên này thay phần diagnostic được nhắc trong protocol cũ. Không đo FPS.

Precision/recall dưới đây lấy tại conf0.25; AP50/AP50-95 lấy từ validator AP, không phải P/R tại ngưỡng vận hành.

## Validation:128 ảnh

| Size | Role | Model | TP | FP | FN | Precision | Recall | AP50 | AP50-95 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 640 | player | v6 | 1971 | 386 | 586 | 83.62% | 77.08% | 0.9087 | 0.6556 |
| 640 | player | v11 | 2184 | 446 | 373 | 83.04% | 85.41% | 0.9194 | 0.6557 |
| 640 | player | v14 | 2104 | 399 | 453 | 84.06% | 82.28% | 0.9236 | 0.6671 |
| 640 | goalkeeper | v6 | 50 | 28 | 42 | 64.10% | 54.35% | 0.7933 | 0.5397 |
| 640 | goalkeeper | v11 | 66 | 18 | 26 | 78.57% | 71.74% | 0.8604 | 0.5646 |
| 640 | goalkeeper | v14 | 53 | 14 | 39 | 79.10% | 57.61% | 0.8474 | 0.5609 |
| 640 | referee | v6 | 63 | 511 | 229 | 10.98% | 21.58% | 0.1046 | 0.0581 |
| 640 | referee | v11 | 46 | 310 | 246 | 12.92% | 15.75% | 0.1298 | 0.0745 |
| 640 | referee | v14 | 49 | 358 | 243 | 12.04% | 16.78% | 0.1305 | 0.0733 |
| 1280 | player | v6 | 2336 | 472 | 221 | 83.19% | 91.36% | 0.9364 | 0.6459 |
| 1280 | player | v11 | 2459 | 437 | 98 | 84.91% | 96.17% | 0.9777 | 0.6644 |
| 1280 | player | v14 | 2392 | 365 | 165 | 86.76% | 93.55% | 0.9762 | 0.6553 |
| 1280 | goalkeeper | v6 | 22 | 38 | 70 | 36.67% | 23.91% | 0.4701 | 0.3397 |
| 1280 | goalkeeper | v11 | 50 | 49 | 42 | 50.51% | 54.35% | 0.7349 | 0.5219 |
| 1280 | goalkeeper | v14 | 68 | 110 | 24 | 38.20% | 73.91% | 0.6522 | 0.4512 |
| 1280 | referee | v6 | 91 | 354 | 201 | 20.45% | 31.16% | 0.2050 | 0.1189 |
| 1280 | referee | v11 | 143 | 230 | 149 | 38.34% | 48.97% | 0.5178 | 0.3157 |
| 1280 | referee | v14 | 115 | 186 | 177 | 38.21% | 39.38% | 0.4942 | 0.2925 |

## Known regression test:35 ảnh

| Size | Role | Model | TP | FP | FN | Precision | Recall | AP50 | AP50-95 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 640 | player | v6 | 670 | 98 | 25 | 87.24% | 96.40% | 0.9596 | 0.7321 |
| 640 | player | v11 | 676 | 138 | 19 | 83.05% | 97.27% | 0.9651 | 0.7418 |
| 640 | player | v14 | 667 | 91 | 28 | 87.99% | 95.97% | 0.9564 | 0.7472 |
| 640 | goalkeeper | v6 | 6 | 6 | 6 | 50.00% | 50.00% | 0.4533 | 0.3230 |
| 640 | goalkeeper | v11 | 6 | 4 | 6 | 60.00% | 50.00% | 0.5384 | 0.3672 |
| 640 | goalkeeper | v14 | 7 | 5 | 5 | 58.33% | 58.33% | 0.5395 | 0.3821 |
| 640 | referee | v6 | 15 | 8 | 61 | 65.22% | 19.74% | 0.4236 | 0.2436 |
| 640 | referee | v11 | 12 | 5 | 64 | 70.59% | 15.79% | 0.4265 | 0.2683 |
| 640 | referee | v14 | 11 | 4 | 65 | 73.33% | 14.47% | 0.5423 | 0.3239 |
| 1280 | player | v6 | 683 | 92 | 12 | 88.13% | 98.27% | 0.9650 | 0.6472 |
| 1280 | player | v11 | 686 | 93 | 9 | 88.06% | 98.71% | 0.9887 | 0.7636 |
| 1280 | player | v14 | 675 | 85 | 20 | 88.82% | 97.12% | 0.9881 | 0.7472 |
| 1280 | goalkeeper | v6 | 2 | 4 | 10 | 33.33% | 16.67% | 0.3174 | 0.2124 |
| 1280 | goalkeeper | v11 | 5 | 3 | 7 | 62.50% | 41.67% | 0.6223 | 0.4308 |
| 1280 | goalkeeper | v14 | 7 | 15 | 5 | 31.82% | 58.33% | 0.5678 | 0.4034 |
| 1280 | referee | v6 | 23 | 15 | 53 | 60.53% | 30.26% | 0.5639 | 0.3210 |
| 1280 | referee | v11 | 39 | 43 | 37 | 47.56% | 51.32% | 0.5915 | 0.3597 |
| 1280 | referee | v14 | 28 | 27 | 48 | 50.91% | 36.84% | 0.6582 | 0.4114 |

## Gate validation tại640 so v6

| Điều kiện khóa | Kết quả |
|---|---|
| referee_ap50_gain | Không đạt |
| overall_map_guard | Đạt |
| player_ap_guard | Đạt |
| keeper_ap_guard | Đạt |

Gate tổng: **không đạt**. Không đổi gate theo1280 hoặc known test; model ứng dụng giữ nguyên.

## Đánh đổi so v11

| Size | Role | ΔTP | ΔFP | ΔFN | ΔAP50 |
|---|---|---:|---:|---:|---:|
| 640 | player | -80 | -47 | +80 | +0.0042 |
| 640 | goalkeeper | -13 | -4 | +13 | -0.0130 |
| 640 | referee | +3 | +48 | -3 | +0.0007 |
| 1280 | player | -67 | -72 | +67 | -0.0014 |
| 1280 | goalkeeper | +18 | +61 | -18 | -0.0827 |
| 1280 | referee | -28 | -44 | +28 | -0.0235 |

Ở640, so v11: player TP2184→2104 và FP446→399; precision83,04%→84,06% nhưng recall85,41%→82,28%. AP50 lại tăng0,9194→0,9236, cho thấy AP trên đường precision–recall không thay thế hành vi tại conf0,25. Keeper TP66→53/92, FP18→14; recall71,74%→57,61%, AP50 giảm0,8604→0,8474. Giảm FP ở hai lớp này đi kèm bỏ sót nhiều hơn, không gọi là cải thiện chung.

Ref640 TP46→49/292 nhưng FP310→358; precision12,92%→12,04%, recall15,75%→16,78%, AP50 chỉ0,129809→0,130525. So v6, TP63→49, AP50 tăng0,104589→0,130525: gain0,025936, dưới yêu cầu0,05 (cần AP50>=0,154589). Ba guard còn lại đạt. mAP50-95 tổng640 v11→v14 là0,431608→0,433775; mức tăng nhỏ này không làm gate referee đạt.

Ở1280, player TP2459→2392/2557, FP437→365: precision84,91%→86,76% nhưng recall96,17%→93,55%; AP50 giảm nhẹ0,9777→0,9762. Keeper TP50→68/92 và FN42→24 nhưng FP49→110, precision50,51%→38,20%; AP50 giảm0,7349→0,6522. Đây là đánh đổi recall lấy thêm nhiều FP, chưa xác định các FP mới là vật thể nền hay nhầm vai trò vì phiên này chưa rà từng box.

Ref1280 TP143→115/292, FP230→186, FN149→177; precision gần như giữ38,34%→38,21% còn recall48,97%→39,38%. AP50 giảm0,5178→0,4942. mAP50-95 tổng1280 giảm0,500642→0,466304 so v11. Không coi giảm44FP referee là thành công khi mất28TP. Dù một số số liệu vẫn hơn v6 ở1280, không chuyển gate sang1280 sau khi xem kết quả.

Known test640 so v11: player TP676→667,FP138→91; keeper TP6→7,FP4→5; ref TP12→11,FP5→4. Known test1280: player TP686→675,FP93→85; keeper TP5→7,FP3→15; ref TP39→28,FP43→27,FN37→48. Ref AP50 test1280 tăng0,5915→0,6582 nhưng recall ở conf0,25 giảm51,32%→36,84%; AP tăng không chứng minh vận hành tốt hơn. Mẫu keeper test chỉ12GT, ref76GT. Không dùng các số test để chỉnh threshold/checkpoint hoặc thay đổi kết luận validation.

Kết luận: v14 **chưa đạt gate và chưa tốt hơn v11 đồng đều**. Không thay model ứng dụng. Các biến động không chứng minh nguồn mới hoặc nền âm gây cải thiện/hồi quy; cần rà lỗi cụ thể trước khi thiết kế thay đổi tiếp theo.

## Kiểm tra và tái hiện

V6/v11 replay khớp TP/FP/FN,P/R,confusion,unmatched và số frame trên cả val/known test ở hai size với fixture v11; AP50/AP50-95 validation lệch dưới1e-6. Không replay diagnostic. Hash dữ liệu nguồn/snapshot/weights/protocol/ledger kiểm lại sau train và sau đánh giá. Không sửa dataset v14 đã phát hành; cache Ultralytics nằm ở snapshot train riêng.

Artifact cục bộ: `data/processed/role_sources_training_v14/` gồm snapshot dataset,small/status/run.log/training/weights,actual-configuration.json và comparison/result.json. Fixture Git: plan,result,replay v14; ảnh/nhãn/weights không commit. `validation-before-test.json` là bản kết luận đã khóa trước test, hash có trong result.

```powershell
.\.venv\Scripts\python.exe -m backend.cv.run_role_training_v14 plan
.\.venv\Scripts\python.exe -m backend.cv.run_role_training_v14 train
.\.venv\Scripts\python.exe -m backend.cv.run_role_training_v14 compare
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp/pytest_training_v14_full
```

Ba lệnh đầu đã thực thi một lần; runner từ chối ghi đè plan/run/comparison. Không chạy lại train để cải thiện số liệu.

Năm test mới kiểm cấu hình v11 bất biến, phát hiện job train khác, chỉ cho thay đường dẫn trong actual args, chặn diagnostic và bảo đảm ghi validation gate trước mọi inference test. 11 test đích đạt; toàn bộ **619 passed,1 network deselected,4 warning cũ** (Starlette/SHAP).

## Giới hạn và bước tiếp

Một lần chạy/một seed; không tách tác động của nguồn mới, ROI nền âm hoặc cấu trúc parent. Số bước cập nhật khác v11 do418 thay409 lượt ảnh. Giữ nguyên bất cân bằng/lặp baseline; ảnh/ROI cùng parent không độc lập. Nhãn agent rà chưa được nghiệm thu độc lập, nhóm bối cảnh chưa phải danh tính trận xác minh. Known regression test đã được xem trước, không phải kiểm mù; không dùng chọn checkpoint/ngưỡng. Không suy ra hiệu quả toàn clip hay quan hệ nhân quả.

Bước tiếp được đề xuất: audit FP goalkeeper tăng và FN referee tăng trên val1280 so v11, xem cả box/context gốc và phân biệt nhầm vai trò, box cạnh tranh, điểm thấp hay localization. Giữ known test khỏi quá trình chọn phương án, không chuyển val/test thành nguồn train. Chưa tăng epoch, đổi threshold/dedup hoặc chạy cấu hình khác.
