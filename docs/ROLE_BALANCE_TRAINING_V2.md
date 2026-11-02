# Cân bằng ROI và huấn luyện lại small

Ngày 02/11/2026. Thử nghiệm small trên gói nhãn trọng tài đã rà ở bước
trước. Giữ nguyên detector đang phục vụ upload, TrackingRow và hệ tọa
độ sân; không thêm dependency.

## Dữ liệu và số lần lấy mẫu

Đầu vào là dataset v1 và `referee_annotations_v2.json`, kiểm bytes video,
frame và ROI trước khi xuất. Chỉ cắt đúng ROI có nhãn; không đưa phần
chưa gán nhãn của cả frame vào train dưới dạng nền. Bbox lân cận bị cắt
ở mép crop được giữ và đổi sang tọa độ chuẩn hóa của ROI.

Loại **5 ảnh train toàn cảnh** có nhãn thuộc quarantine khỏi bản dataset
mới. Không chỉ xóa nhãn nghi ngờ rồi giữ ảnh đó làm nền. Các vùng khác
đã rà rõ trong cùng nguồn vẫn được phép dùng riêng ở dạng ROI. Dataset
v1 và raw không bị sửa.

| Nhóm | ROI khác nhau | Số lần/ROI | Mục ảnh đưa vào train |
|---|---:|---:|---:|
| Trọng tài xanh nhạt | 33 | 1 | 33 |
| Trọng tài vàng | 10 | 3 | 30 |
| Trọng tài đỏ | 3 | 6 | 18 |
| Trọng tài đen | 1 | 6 | 6 |
| Cầu thủ đối chiếu | 30 | 1 | 30 |
| Nhân viên/camera làm nền | 6 | 2 | 12 |

Tổng 83 ROI thật tạo **129 lượt ROI**. Giới hạn tối đa 6 lần/ROI;
lặp ảnh không tạo thêm người, góc quay hoặc trận đấu độc lập. Có 30
lượt trọng tài mới từ video cục bộ và 17 nhãn nguồn được rà lại.
Mẫu đen vẫn chỉ có một lượt quan sát thật, dù xuất hiện 6 lần khi học.

| Tập | Mục ảnh | Bbox player | Bbox goalkeeper | Bbox referee |
|---|---:|---:|---:|---:|
| Train | 341 | 4.277 | 187 | 588 |
| Validation | 128 | 2.557 | 92 | 292 |
| Test hồi quy | 35 | 695 | 12 | 76 |

Train gồm 212 ảnh toàn cảnh và 129 lượt ROI. Đây là cân bằng tần suất
ROI, lớp player vẫn chiếm nhiều bbox nhất. Không tăng trọng số tới mức
biến một crop trọng tài hiếm thành hàng chục mẫu độc lập giả.

Đã so đường dẫn/hash ảnh và nhãn của toàn bộ validation/test với v1:
giữ nguyên. Các nguồn Euro đỏ–trắng mới vẫn chỉ ở train. Tập test đã
được xem ở v1, vì vậy lượt này là **kiểm hồi quy trên tập đã biết**,
không phải test mù hoặc đánh giá độc lập trên trận mới.

Snapshot dữ liệu: `fixtures/role_balance_dataset_summary_v2.json`;
protocol: `fixtures/role_balance_protocol_v2.json`.

## Huấn luyện và quy tắc đối chiếu

Bắt đầu từ small tốt nhất của v1, SHA-256
`5b07c6ed1e7374c21656dad5e64dfc4d0a0f3e4f66b0068fdaeb051bc7602958`.
Tạo AdamW mới, không khôi phục trạng thái optimizer cũ. Học bổ sung
20 epoch, imgsz 640, batch 4, lr 0,0003, AMP tắt, workers 0,
seed 20261102, mosaic 0,5 và tắt ở ba epoch cuối. Dùng CUDA trên
RTX 3050 6GB; không tự chuyển CPU hoặc nâng thư viện.

Checkpoint được chọn theo validation fitness. Trước khi mở test hồi
quy, đối chiếu với weights small cũ trên cùng validation và khóa lựa
chọn. Quy tắc đã ghi trước trong protocol:

- AP50 trọng tài tăng tối thiểu 0,05 (5 điểm phần trăm).
- mAP50–95 tổng không giảm quá 0,03.
- AP50 cầu thủ không giảm quá 0,03; AP50 thủ môn không giảm quá 0,05.

Đo thêm ở confidence 0,25, ghép bbox một-một theo IoU ≥ 0,5 trước khi
chấm vai trò. Sai vai trò tính FN cho lớp đúng và FP cho lớp dự đoán;
không bỏ các box dư hoặc chọn box thuận lợi bằng cách nhìn lớp. Báo
riêng player bị gọi referee và referee/keeper bị gọi player. Phép đo
detector không dùng bộ lọc biên sân để che các lỗi phân loại.

Các gate trên phục vụ lựa chọn checkpoint nghiên cứu, không tự duyệt
đưa vào upload. Nhãn nguồn/agent chưa độc lập, số trận chưa xác minh và
số mẫu thủ môn test còn ít. Huấn luyện bổ sung, khởi tạo warm-start và
sampling cùng thay đổi; không có ablation để quy mọi chênh lệch chỉ
cho việc cân bằng mẫu.

## Kết quả đã đo

Đã học đủ 20 epoch bổ sung và chọn checkpoint tốt nhất theo validation.
Lượt chính mất khoảng 995 giây; peak tensor allocated 2.948 MiB, không
phải tổng VRAM. PyTorch 2.8.0+cu128, Ultralytics 8.3.221 trên RTX 3050
6GB. Baseline được chạy lại bằng cùng bộ đo, không chỉ chép số cũ.

| Validation | Small v1 | Small cân bằng v2 |
|---|---:|---:|
| mAP50–95 tổng | 37,15% | 39,87% |
| AP50 player | 85,76% | 84,07% |
| AP50 goalkeeper | 74,96% | 81,84% |
| AP50 referee | 6,45% | 6,71% |

AP50 trọng tài chỉ tăng **0,25 điểm phần trăm**, chưa đạt mức tăng 5
điểm đã khóa trước. Ba gate giữ chất lượng tổng/player/keeper đều đạt,
gate trọng tài không đạt. `selection-before-test.json` đã chọn giữ
baseline trước khi chạy test. Không lấy tăng mAP tổng để duyệt model.

| Test hồi quy đã biết | Small v1 | Small cân bằng v2 |
|---|---:|---:|
| mAP50–95 tổng | 41,23% | 41,12% |
| AP50 player | 95,07% | 95,30% |
| AP50 goalkeeper | 47,69% | 44,85% |
| AP50 referee | 24,57% | 28,29% |

Ở confidence cố định 0,25, kết quả khác với recall tối ưu trên đường
cong F1 của validator; không trộn hai cách đo:

| Chỉ số cố định | Small v1 | Small cân bằng v2 |
|---|---:|---:|
| Validation: referee đúng / 292 nhãn | 35 | 39 |
| Validation: FP referee theo nhãn hiện có | 907 | 1.058 |
| Validation: player bị gọi referee / 2.557 nhãn | 757 | 940 |
| Test: referee đúng / 76 nhãn | 10 | 13 |
| Test: FP referee theo nhãn hiện có | 0 | 9 |
| Test: recall referee | 13,16% | 17,11% |
| Test: precision referee | 100% | 59,09% |

Test nhận thêm ba lượt trọng tài nhưng cũng có thêm box không khớp
nhãn. FP/recall phụ thuộc bộ nhãn nguồn/agent chưa độc lập; không gọi
mọi box không khớp là người sai vai trò đã được xác minh bằng mắt.
Validation còn giảm recall player ở ngưỡng cố định, từ 62,73% xuống
57,10%, dù AP50 player chỉ giảm 1,69 điểm.

Đã xem lại 15 crop player bị gọi referee từ bốn prefix validation.
Các crop cho thấy cầu thủ áo vàng, có số áo và tư thế thi đấu, bị gán
referee với confidence khoảng 0,41–0,87. Đây là một dạng lỗi đã thấy
trực tiếp, không khẳng định là nguyên nhân duy nhất. Baseline cũng có
nhiều lỗi này; không nói 15 lỗi được xem đều mới xuất hiện sau cân bằng.
Ảnh/chi tiết local:
`role_balance_training_v2/comparison/validation-player-as-referee.jpg`
và `.json`.

## Quyết định bàn giao

**Không chọn v2 thay baseline nghiên cứu, không đưa vào upload.**
Ứng dụng vẫn dùng detector/palette đang có; baseline small v1 cũng chưa
được duyệt cho runtime từ phiên trước. Tăng mẫu referee ở màu vàng
chưa đủ để model phân biệt cầu thủ cũng áo vàng. Các mẫu player ROI
mới chủ yếu đỏ/trắng; không suy rằng chỉ cần lặp ROI nhiều hơn hoặc
thêm epoch sẽ khắc phục được lỗi.

Hướng tiếp theo là mẫu đối chiếu cùng màu giữa cầu thủ và trọng tài
và các góc có thêm ngữ cảnh từ nguồn train mới, đồng thời rà lại nhãn
validation. Không chuyển ảnh sân vàng của validation vào train để làm
đẹp số; cần nguồn khác hoặc protocol/tập kiểm mới được khai báo rõ.
Chưa làm các thay đổi dữ liệu đó trong lượt cân bằng/huấn luyện này.

Weights mới giữ local để nghiên cứu:
`data/processed/role_balance_training_v2/small/training/weights/best.pt`,
SHA-256 `ef24764d1d84702932aca1714a5f5d96bc89bfeab41800b3672597d49f7a81ce`.
Dataset: `data/processed/role_balanced_dataset_v2/`.
Báo cáo máy đọc: `fixtures/role_balance_result_v2.json`; bản local đầy
đủ trong `data/processed/role_balance_training_v2/comparison/`.

**518 test Python đạt**, 1 network deselected, 4 warning thư viện cũ.
16 test mới kiểm cap sampling, tọa độ ROI, dữ liệu kiểm giữ nguyên,
ghép vai trò không thiên lệch lớp, FP/FN/box dư và gate validation.
Đã đối chiếu lại hash dataset/weights và khóa lựa chọn trước test.

## Lệnh chạy lại

Cần đầy đủ dữ liệu/weights local đúng hash, output phải là thư mục mới:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.balance_role_dataset `
  --protocol docs/fixtures/role_balance_protocol_v2.json `
  --output data/processed/role_balance_dataset_rerun
.\.venv\Scripts\python.exe -m backend.cv.finetune_roles train `
  --dataset data/processed/role_balance_dataset_rerun `
  --protocol docs/fixtures/role_balance_protocol_v2.json `
  --output data/processed/role_balance_small_rerun --model small
.\.venv\Scripts\python.exe -m backend.cv.compare_role_models `
  --dataset data/processed/role_balance_dataset_rerun `
  --protocol docs/fixtures/role_balance_protocol_v2.json `
  --run data/processed/role_balance_small_rerun `
  --output data/processed/role_balance_comparison_rerun
```

Ảnh/crop/dataset và weights giữ local, chỉ commit mã, metadata và báo
cáo. Nhãn quarantine không được dùng làm mẫu nền hoặc đối tượng phụ
trong ROI mới.
