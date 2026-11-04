# Phép thử small v11 sau làm sạch dữ liệu

Ngày 04/11/2026. Phép thử ngoại tuyến, không tự đổi model ứng dụng.

## Cấu hình khóa trước huấn luyện

- Dataset sạch v11: 409 lượt train / 315 đơn vị pixel–label, 128 val,
  35 known test. Tham khảo `ROLE_DATA_CURATION_V11.md` về nhãn và nguồn mới.
- Tạo snapshot train riêng, giữ mọi image/label record của bộ curation.
  Chỉ gắn manifest vào protocol huấn luyện; bản curation giữ nguyên.
- COCO YOLO11s, fresh AdamW, 20 epoch, 640, batch4, FP32, lr0=0.0003,
  seed20261102, workers0, mosaic0.5, close_mosaic3, không multi-scale.
  Các thông số này và weights khởi tạo giống v10, được kiểm bằng test.
- Không đổi số lặp mẫu, ngưỡng hoặc epoch sau khi xem kết quả.
- Chọn best theo validation fitness sẵn có; so v6/v10/v11 ở 640/1280.
  AP confidence0.001; phép chấm vận hành confidence0.25, NMS0.7,
  matching IoU0.5, max_det300, không khử box trùng vai trò.
- Gate tại 640 đối chiếu v6: ref AP50 tăng ít nhất0.05; mAP50-95 giảm
  không quá0.03; player AP50 giảm không quá0.03; keeper AP50 giảm không
  quá0.05. Khóa kết quả val trước khi mở known test và diagnostic heldout.
- Known test đã xem trước đây; bốn ROI match128057 cũng đã kiểm một phần.
  Không gọi hai bộ này là kiểm mù, không chọn checkpoint/ngưỡng theo chúng.

Protocol: `docs/fixtures/role_sources_training_protocol_v11.json`.
SHA256: `92b88f2e2f6f35d082591bb3df6a6ec36d408a616873a2aeb09fb63d81306900`.
Manifest train snapshot:
`560064870de51c8114f5ba358b0382d621e044ecf5127dda3c5fd947b6293243`.
Plan `training_started=false` là ảnh chụp lúc chuẩn bị. Trạng thái thực nằm
ở `data/processed/role_sources_training_v11/small/status.json`.

## Lệnh kiểm tra

```powershell
.venv/Scripts/python.exe -m backend.cv.prepare_role_curation_run
.venv/Scripts/python.exe -m backend.cv.finetune_roles train --dataset data/processed/role_sources_training_v11/dataset --protocol docs/fixtures/role_sources_training_protocol_v11.json --output data/processed/role_sources_training_v11/small --model small
.venv/Scripts/python.exe -m backend.cv.compare_role_sources --version v11
```

Các thư mục đích phải chưa tồn tại; không ghi đè bản đã phát hành.
Ảnh/nhãn/weights có hash, kiểm lại sau train và sau so sánh. Val/test có
cùng đường dẫn và hash như v10. Match128057 không tham gia train/val.

## Giới hạn diễn giải

Một seed và số bước cập nhật khác nhẹ do thay số ảnh; không tách tác động
riêng của sửa nhãn, cách ly ảnh và thêm nguồn. Năm ảnh mới thuộc bốn nhóm
bối cảnh suy theo hình ảnh, chưa xác minh danh tính trận chính thức.
Nhãn do agent rà, chưa kiểm độc lập. Keeper xanh/sáng ưu tiên trong ảnh
mới đang đổ người/ngồi thấp; không coi là đã phủ tốt keeper đứng xa.

Tốc độ đo predict trên 20 ảnh val đầu, ba warmup, không gồm đọc đĩa;
đây không phải tốc độ toàn bộ luồng video. Không tự triển khai ngay cả
khi qua gate. Kết luận phải dựa vào cả ba lớp, recall và FP/FN ở ngưỡng
đã khóa, không chỉ một giá trị mAP.

## Kết quả nghiệm thu

Hoàn tất 20 epoch, train kèm validation cuối 1324.77s. CUDA peak allocated 2944.56 MiB (không phải tổng VRAM). Weights SHA256 `d576a3aceb80bc0a9f797da9b4d4bdba36995c2ea4203eed786ac7c63b89be72`.

### Validation

| Size | Vai trò | AP50 v6 / v10 / v11 | TP/FP/FN v6 | TP/FP/FN v10 | TP/FP/FN v11 |
|---|---|---|---|---|---|
| 640 | player | 0.9087 / 0.9214 / 0.9194 | 1971/386/586 | 2113/400/444 | 2184/446/373 |
| 640 | goalkeeper | 0.7933 / 0.8066 / 0.8604 | 50/28/42 | 34/6/58 | 66/18/26 |
| 640 | referee | 0.1046 / 0.1131 / 0.1298 | 63/511/229 | 25/326/267 | 46/310/246 |
| 1280 | player | 0.9364 / 0.9607 / 0.9777 | 2336/472/221 | 2368/442/189 | 2459/437/98 |
| 1280 | goalkeeper | 0.4701 / 0.6618 / 0.7349 | 22/38/70 | 34/21/58 | 50/49/42 |
| 1280 | referee | 0.2050 / 0.3626 / 0.5178 | 91/354/201 | 101/232/191 | 143/230/149 |

### Known test: 35 ảnh

| Size | Vai trò | TP/FP/FN v6 | TP/FP/FN v10 | TP/FP/FN v11 |
|---|---|---|---|---|
| 640 | player | 670/98/25 | 678/93/17 | 676/138/19 |
| 640 | goalkeeper | 6/6/6 | 5/2/7 | 6/4/6 |
| 640 | referee | 15/8/61 | 6/1/70 | 12/5/64 |
| 1280 | player | 683/92/12 | 685/83/10 | 686/93/9 |
| 1280 | goalkeeper | 2/4/10 | 5/4/7 | 5/3/7 |
| 1280 | referee | 23/15/53 | 15/18/61 | 39/43/37 |

### Diagnostic match128057: bốn ROI

| Size | Model | TP player / keeper / ref | FP player / keeper / ref |
|---|---|---|---|
| 640 | v6 | 30 / 0 / 0 | 8 / 0 / 0 |
| 640 | v10 | 29 / 1 / 1 | 5 / 0 / 3 |
| 640 | v11 | 30 / 1 / 2 | 4 / 1 / 2 |
| 1280 | v6 | 26 / 0 / 0 | 19 / 1 / 1 |
| 1280 | v10 | 29 / 1 / 2 | 4 / 0 / 1 |
| 1280 | v11 | 31 / 1 / 3 | 4 / 3 / 0 |

### Tốc độ predict

| Size | FPS v6 | FPS v10 | FPS v11 |
|---|---|---|---|
| 640 | 35.15 | 37.04 | 58.89 |
| 1280 | 26.43 | 21.76 | 25.98 |

### Gate và kiểm tra đối chiếu

{"checks": {"referee_ap50_gain": false, "overall_map_guard": true, "player_ap_guard": true, "keeper_ap_guard": true}, "preferred_by_validation": "baseline", "candidate_is": "v11", "reference_is": "v6"}

Tái hiện v6/v10 khớp mọi confusion/extras trên val, known test và diagnostic với snapshot cũ; AP50 từng lớp lệch dưới1e-6. Giữ nguyên dữ liệu curation, nguồn, nhãn và weights đối chiếu. Không đổi model ứng dụng.

## Đánh giá kết quả và bước tiếp theo

V11 tốt hơn v10 về recall trên val ở cả hai size. Tại 640, keeper nhận
đúng34→66/92, ref25→46/292; ref FP326→310 nhưng player FP400→446 và keeper
FP6→18. So với v6, ref TP tại640 vẫn giảm63→46. AP50 player giảm nhẹ
0.9214→0.9194 so với v10; không kết luận mọi chỉ số đều tốt hơn.

Tại1280, ref AP50 tăng0.3626→0.5178, TP101→143/292, FP232→230;
player→ref giảm127→57. Keeper TP34→50/92 nhưng FP21→49: precision
giảm61.82%→50.51%. Đây là đánh đổi cần rà, không chỉ nhìn AP tăng.

Known test1280: ref TP15→39/76, đồng thời FP18→43; precision45.45%→47.56%.
Player FP83→93, không phải cải thiện đồng đều trên dữ liệu cũ. Diagnostic
match128057 tại1280 nhận3/3 ref, không có ref FP, nhưng keeper FP0→3.
Chỉ bốn ROI với ba nhãn ref và một keeper, chưa phải độ chính xác cả clip.

Gate vẫn **không đạt**: ref AP50 tại640 tăng0.1046→0.1298 so với v6,
chỉ khoảng0.0252 thay vì tối thiểu0.05. Ba guard khác đạt. Không chuyển
gate sang1280 sau khi thấy kết quả và không thay model ứng dụng.

FPS giữa các lượt cùng kiến trúc chênh khá lớn, có thể chịu ảnh hưởng thứ
tự chạy và trạng thái GPU; phép đo một lượt này không chứng minh v11
nhanh hơn v10. Không quy cải thiện cho riêng năm ảnh hoặc một nhãn đã sửa.

588 test toàn bộ đạt,1 network deselected,4 warning cũ. Có5 test đích về
snapshot, cấu hình đã khóa và đối chiếu nhiều weights. Train/compare hoàn
tất; dữ liệu curation và protocol v10 giữ nguyên hash; các số liệu v6/v10
trong lần đo mới khớp snapshot cũ. Fixtures result/replay lưu đầy đủ số
liệu và bằng chứng hash để đối chiếu.

Bước tiếp theo: rà các FP thủ môn mới và ref biên xa còn bỏ sót trên val1280
so với v10, phân biệt box trùng/nhầm vai trò/ảnh nền trước khi bổ sung
keeper đứng xa xanh/sáng. Chưa tăng epoch, hạ confidence hoặc train tiếp.
