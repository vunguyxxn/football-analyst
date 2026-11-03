# Huấn luyện small trên dữ liệu ghép v8/v9 (v10)

## Kế hoạch đã khóa trước huấn luyện

- Nền: toàn bộ dataset sạch v6, giữ nguyên 369 lượt train, 128 ảnh val,
  35 ảnh test và mọi hash image/label của val/test.
- Thêm đúng 9 ROI train v8/v9 của match 117093 và 118575; mỗi ROI lặp 4
  lượt bất kể vai trò. Tổng train 405 lượt. 36 lượt mới tương ứng 9 ảnh
  khác nhau, không phải 36 nguồn độc lập. Thêm 184/24/16 lượt box
  player/goalkeeper/referee; quan sát không lặp là 46/6/4.
- Match 128057 giữ riêng toàn trận, không thêm vào train hoặc val.
  Bốn ROI kiểm chứng có 31 player, 1 goalkeeper, 3 referee. Một phần đã
  xem kết quả ở v8; chỉ là chẩn đoán khác miền, không phải kiểm mù.
- Khởi tạo COCO YOLO11s, fresh AdamW; 20 epoch, imgsz640, batch4,
  AMP=false, lr0=0.0003, seed20261102, mosaic0.5/close_mosaic3,
  workers0, multi_scale=false. Cùng thông số v6; không warm-start v7.
- Chọn best checkpoint theo validation fitness sẵn có. Không chọn size,
  confidence hoặc checkpoint dựa trên known test/match mới.
- So cả ba lớp ở 640 và 1280; AP conf0.001, phép chấm cố định conf0.25,
  NMS IoU0.7, matching IoU0.5, max_det300, không dedup vai trò.
- Gate quyết định giữ nguyên các mức số: ref AP50 tăng >=0.05; overall
  mAP50-95 giảm <=0.03; player AP50 giảm <=0.03; keeper AP50 giảm <=0.05.
  Lần này đối chiếu **v6 tại 640**, không đối chiếu v1. Khóa kết quả val
  của hai model trước khi mở known test và diagnostic match 128057.
- Không tự thay model trong ứng dụng, kể cả qua gate. Không sửa schema.

Protocol: `docs/fixtures/role_sources_training_protocol_v10.json`.
Plan snapshot: `docs/fixtures/role_sources_training_plan_v10.json`.
Plan có `training_started=false` là ảnh chụp lúc chuẩn bị, không phải trạng
thái live; trạng thái live tại `data/processed/role_sources_training_v10/small/status.json`.
Các trường thống kê ROI cũ được kế thừa từ manifest nền là lịch sử v2/v6;
quy mô phần bổ sung v10 được ghi riêng bằng `new_unique_train_rois` và
`new_train_exposures`, không đọc các số lịch sử là tổng bộ nhãn mới.

## Kiểm tra và tái tạo

```powershell
.\.venv\Scripts\python.exe -m backend.cv.merge_role_sources
.\.venv\Scripts\python.exe -m backend.cv.finetune_roles train --dataset data/processed/role_sources_training_v10/dataset --protocol docs/fixtures/role_sources_training_protocol_v10.json --output data/processed/role_sources_training_v10/small --model small
.\.venv\Scripts\python.exe -m backend.cv.compare_role_sources
```

Các output phải chưa tồn tại khi tái tạo. Các hash nguồn/release/protocol,
nhãn ROI và split match được kiểm trước khi ghép. Test chặn đổi vai trò
nhãn, ghi lại split của release và đưa heldout vào train. Val/test bảo vệ
bằng danh sách đường dẫn/hash đối chiếu toàn bộ, không chỉ kiểm số lượng.

## Giới hạn

Nhãn mới do agent rà với COCO hỗ trợ, chưa kiểm độc lập. Footage trận thật
nhưng camera followcam là crop ảo; chưa đại diện đầy đủ video broadcast.
Một seed, số bước cập nhật và dữ liệu thay đổi đồng thời; không kết luận
quan hệ nhân quả riêng của sampling. Không lấy mAP trên train làm kết quả.
Tốc độ chẩn đoán đo predict trên 20 ảnh val đầu, ba warmup, một lượt
liên tiếp, loại thời gian đọc đĩa; không gọi là FPS xử lý video toàn luồng.

## Kết quả

Hoàn tất 20 epoch liên tục; thời gian train kèm validation cuối 1014.36s. CUDA tensor peak allocated 2949.11 MiB, không phải tổng VRAM. Weights SHA256 `70e44344f01d9190daa7cae276a290b057e09f911ce9398cc2ab7115a10cdd2f`.

### Validation: AP50 và phép chấm conf0.25

| Size | Vai trò | AP50 v6 | AP50 v10 | TP/FP/FN v6 | TP/FP/FN v10 |
|---|---|---:|---:|---|---|
| 640 | player | 0.9087 | 0.9214 | 1971/386/586 | 2113/400/444 |
| 640 | goalkeeper | 0.7933 | 0.8066 | 50/28/42 | 34/6/58 |
| 640 | referee | 0.1046 | 0.1131 | 63/511/229 | 25/326/267 |
| 1280 | player | 0.9364 | 0.9607 | 2336/472/221 | 2368/442/189 |
| 1280 | goalkeeper | 0.4701 | 0.6618 | 22/38/70 | 34/21/58 |
| 1280 | referee | 0.2050 | 0.3626 | 91/354/201 | 101/232/191 |

Nhầm player→referee trên val: 640: 409→269, 1280: 155→127.

### Known test: 35 ảnh cũ

| Size | Vai trò | TP/FP/FN v6 | TP/FP/FN v10 |
|---|---|---|---|
| 640 | player | 670/98/25 | 678/93/17 |
| 640 | goalkeeper | 6/6/6 | 5/2/7 |
| 640 | referee | 15/8/61 | 6/1/70 |
| 1280 | player | 683/92/12 | 685/83/10 |
| 1280 | goalkeeper | 2/4/10 | 5/4/7 |
| 1280 | referee | 23/15/53 | 15/18/61 |

### Diagnostic: 4 ROI cùng match 128057

| Size | Vai trò | TP/FP/FN v6 | TP/FP/FN v10 |
|---|---|---|---|
| 640 | player | 30/8/1 | 29/5/2 |
| 640 | goalkeeper | 0/0/1 | 1/0/0 |
| 640 | referee | 0/0/3 | 1/3/2 |
| 1280 | player | 26/19/5 | 29/4/2 |
| 1280 | goalkeeper | 0/1/1 | 1/0/0 |
| 1280 | referee | 0/1/3 | 2/1/1 |

### Tốc độ predict

| Size | v6 FPS | v10 FPS |
|---|---:|---:|
| 640 | 36.81 | 39.05 |
| 1280 | 23.99 | 22.96 |

Một lượt đo liên tiếp trên cùng 20 ảnh val, không đọc là FPS xử lý video.

### Gate tại 640 so với v6

- `referee_ap50_gain`: không đạt.
- `overall_map_guard`: đạt.
- `player_ap_guard`: đạt.
- `keeper_ap_guard`: đạt.

Không tự promote. Kết quả đầy đủ (precision/recall, ma trận nhầm lẫn và hash) tại `docs/fixtures/role_sources_training_result_v10.json`.

### Nhận xét và bước tiếp theo

Ở 640, nhầm player thành referee giảm 409→269 nhưng nhận đúng referee
giảm 63→25 và keeper giảm 50→34. Đây là đánh đổi với recall, không gọi
là sửa xong lỗi phân vai trò chỉ vì false positive giảm. AP là phép tổng
hợp nhiều ngưỡng; AP50 tăng nhẹ không bảo đảm tốt hơn ở conf0.25.

Ở 1280, val cải thiện cả ba lớp: ref AP50 0.2050→0.3626,
FP ref 354→232, keeper TP22→34; mAP50-95 tổng 0.3682→0.4548.
Tuy nhiên known test ref TP23→15 và FP15→18. Không chọn lại gate ở 1280
sau khi thấy kết quả, không điều chỉnh confidence hoặc train thêm epoch.

Trên bốn ROI match 128057, v10 ở 1280 nhận đúng keeper 1/1, ref 2/3,
so với v6 đều 0; vẫn có 1 FP ref. Chỉ một match với nhãn agent hỗ trợ,
đã xem một phần trước đó, không coi là bằng chứng kiểm chứng độc lập.

Bước tiếp theo: rà các keeper/ref nhận đúng ở v6 nhưng mất ở v10 trên
**val**, xem ảnh toàn cảnh và phân nhóm kích thước/màu áo/score/khung trùng.
Dùng kết quả audit val để chốt nhu cầu bổ sung nguồn train khác trận,
không đưa match 128057 hay test cũ vào train và không sửa phép chấm.
Giữ nguyên model ứng dụng trong lúc chốt dữ liệu bổ sung.

Kiểm tra: toàn bộ 564 test Python đạt (1 network deselected, 4 warning cũ);
9 test đích đạt sau khi bổ sung kiểm hash cuối phép so sánh. Các lệnh
ghép/train/compare thực tế đều thành công; hash weights/dataset/release
được kiểm lại sau đánh giá. Không đổi frontend, runtime, dependency/schema.
