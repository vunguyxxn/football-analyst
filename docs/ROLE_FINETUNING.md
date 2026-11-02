# Bổ sung nhãn và huấn luyện vai trò

Ngày 02/11/2026. Thử nghiệm ba lớp `player`, `goalkeeper`, `referee`
cho YOLO11 nano và small trên RTX 3050 6GB. Đây là thí nghiệm ngoại tuyến;
chưa thay model của luồng upload, tracking hoặc DATA_CONTRACT.

## Nhãn và nguồn

Khôi phục nhãn vai trò từ dữ liệu gốc, không dùng nhãn person đã gộp ở
bước 5b cũ. Nguồn [martinjolif/football-player-detection](https://huggingface.co/datasets/martinjolif/football-player-detection/tree/e8b8cea002692efd74c945fcdad63e729adc5671)
được khóa revision `e8b8cea002692efd74c945fcdad63e729adc5671`;
dataset card công bố CC BY 4.0, ghi nguồn Football project/Roboflow.
Kiểm từng file ảnh/nhãn theo inventory hash đã lưu của dự án.
Chuyển lớp gốc: ball bỏ; goalkeeper → 1, player → 0, referee → 2.
Giữ nguyên nhãn thủ môn, không gộp vào tuyến ngoài hoặc suy đội bằng áo.

Bổ sung **177 bbox có vai trò trên 8 frame** từ 4 video cục bộ:

| Clip | Frame | Tập | Tuyến ngoài | Thủ môn | Trọng tài |
|---|---|---|---:|---:|---:|
| Project 15 mẫu | 930, 1350 | train | 38 | 2 | 5 |
| Project 15(1) | 538, 800 | train | 40 | 2 | 5 |
| Project 15(2) | 1214, 1500 | train | 37 | 2 | 4 |
| Project 12 | 704, 1000 | test | 38 | 0 | 4 |

Đề xuất bbox từ COCO11n ở imgsz 1280/conf 0,15; agent đã xem cả frame
có số và từng crop trước huấn luyện. Loại nhân viên/vest, camera,
người ngoài cuộc và một box trùng; không coi chúng là cầu thủ tuyến
ngoài. Thêm tay một trọng tài biên xa bị detector bỏ sót ở Project 12
frame 704. Cập nhật này diễn ra trước test; bỏ lượt train preflight cũ,
khóa lại nhãn/dataset rồi huấn luyện lại từ weights COCO ban đầu.
Lượt bỏ dở giữ cục bộ ở `role_training_v1/nano`, không dùng checkpoint.

Nhãn hướng tới toàn bộ đối tượng mục tiêu nhìn thấy, không tự thêm người
bị che hoặc ngoài camera. Các bbox còn phụ thuộc proposal; nhãn do cùng
agent rà, chưa có người kiểm độc lập nên vẫn có thể bỏ sót hoặc lệch
box. Fixture `local_role_annotations_v1.json` lưu tọa độ, vai trò, frame,
hash video và PNG gốc đã xem. Không gọi đây là ground truth độc lập.

`referee` bao gồm trọng tài chính và trọng tài biên. Đây là lớp ngữ
nghĩa: người mặc áo trọng tài ngoài đường biên vẫn có thể được detector
nhận ra; bộ lọc đường biên của sản phẩm phải tiếp tục loại họ khỏi ID/
phân tích sân. Nhân viên và người dự bị ngoài cuộc không phải target.

## Tách nguồn trước khi học

Không dùng random frame split. Các prefix có thể cùng sân/màu áo được
gom vào nhóm lớn; toàn bộ một clip cục bộ chỉ thuộc một tập. Nguồn
`08fd33` nhìn thấy cùng bối cảnh/áo trắng–sẫm với Project 12 được giữ
chung trong test. Bốn prefix sân vàng gom chung validation. Các nguồn
sân đỏ còn lại gom train, cùng ba clip Euro đỏ–trắng cục bộ.

Đây là nhóm bảo thủ theo hình ảnh/nguồn, **chưa xác minh danh tính trận
chính thức**. Không tuyên bố đã có bộ test tách trận được xác nhận. Bộ
test cũng chỉ có một nhóm nguồn trắng–sẫm; chưa đại diện nhiều giải/sân.

| Tập | Ảnh | Player | Goalkeeper | Referee |
|---|---:|---:|---:|---:|
| Train | 217 | 4.329 | 190 | 513 |
| Validation | 128 | 2.557 | 92 | 292 |
| Test | 35 | 695 | 12 | 76 |

Kiểm không giao nhóm/source/hash pixel giữa các tập; từ chối ảnh gần
trùng khác tập với dHash ≤ 4 và thumbnail MAE ≤ 3. Không chia lại theo
kết quả model. 372 ảnh nguồn và 8 ảnh cục bộ được giữ, tổng 380 ảnh.
Nguồn/nhãn/model/YAML/manifest có hash để từ chối bản thay đổi giữa
chuẩn bị, huấn luyện và kiểm tra.

## Cấu hình đã khóa

Protocol: `fixtures/role_finetune_protocol_v1.json`. Hai model bắt đầu
từ COCO pretrained, không từ checkpoint person cũ hoặc model medium
đã thấy dữ liệu bóng đá. Nano dùng `data/raw/yolo11n.pt`; small dùng
asset chính thức [Ultralytics v8.3.0/yolo11s.pt](https://github.com/ultralytics/assets/releases/tag/v8.3.0),
asset ID 196201263, SHA-256
`85a76fe86dd8afe384648546b56a7a78580c7cb7b404fc595f97969322d502d5`.
API nguồn không cung cấp asset digest; hash này ghi từ file tải qua URL
release chính thức, không được gọi là hash do nhà phát hành chứng thực.

Cả hai chạy 20 epoch, imgsz 640, batch 4, AdamW/lr 0,001, seed 20261102,
AMP tắt, workers 0, mosaic 0,5 và tắt ở 3 epoch cuối. Không thêm gói,
không nâng Ultralytics và không thử nhiều seed để chọn kết quả đẹp.
Một lượt có seed chưa đủ chứng minh ổn định giữa các lần huấn luyện.

Chọn checkpoint tốt nhất riêng từng model theo validation fitness;
chọn ưu tiên nano/small bằng validation macro mAP50–95 trước khi mở
test. Tập test chỉ đánh giá sau khi cả hai lượt train hoàn tất. Đo
mAP ở conf 0,001, NMS IoU 0,7, tối đa 300 detection. Precision/recall
của validator là theo đường cong F1 của bộ đo, không phải mặc nhiên
hiệu năng tại confidence 0,25 trong luồng thực tế.

## Kết quả huấn luyện và tập test

Đã chạy xong cả hai model, 20 epoch/model, không mở test trước khi cả
hai lượt hoàn tất. Small được chọn ưu tiên bằng validation trước khi
đo test; không đảo lựa chọn dựa trên test.

| Model | mAP50–95 validation | mAP50–95 test | mAP50 test | Thời gian lượt chính |
|---|---:|---:|---:|---:|
| Nano | 25,00% | 25,93% | 40,13% | 471 giây |
| Small | 37,15% | 41,23% | 55,78% | 577 giây |

AP50 từng vai trò trên test và recall từ validator:

| Model | Player AP50 / recall | Goalkeeper AP50 / recall | Referee AP50 / recall |
|---|---|---|---|
| Nano | 92,05% / 92,95% | 4,43% / 0% | 23,91% / 9,21% |
| Small | 95,07% / 96,98% | 47,69% / 41,67% | 24,57% / 13,16% |

Đây là AP/recall trên bộ nhãn đã mô tả, không phải “độ chính xác toàn
bộ video”. Recall trọng tài của small còn thấp, bỏ sót phần lớn trong
76 lượt có nhãn. Test thủ môn chỉ có 12 lượt. Nano không đạt cho vai
trò hiếm; small tốt hơn về tổng thể/thủ môn nhưng chưa đủ ổn định để
thay detector đang phục vụ người dùng.

Peak tensor allocated trong lượt train: nano 1.337 MiB, small 2.328 MiB;
không phải tổng VRAM. Máy chạy được batch 4 trên RTX 3050 6GB; số đo
không bao gồm workload đồng thời khác. PyTorch 2.8.0+cu128,
Ultralytics 8.3.221, Python 3.11.3. Một seed và một ngân sách 20 epoch
chỉ cho kết luận thí điểm; chưa có khoảng tin cậy hoặc kiểm định nhiều
lần chạy, không khẳng định đã hội tụ.

## Kiểm lại video ở confidence cố định

Chạy thêm bộ 15 frame/4 clip đã dùng để sàng lọc model medium ở phiên
trước, cùng các gate ghép và conf 0,25, cả imgsz 640/1280. Đây là phép
kiểm sau huấn luyện, không dùng để chọn checkpoint/kích thước ảnh hay
chỉnh ngưỡng. **Ba clip đỏ–trắng đã tham gia train**, một số frame trùng
ảnh học. Vì vậy không dùng tổng 4 clip để khẳng định tổng quát hóa.

| Model / imgsz | Tuyến ngoài đúng | Thủ môn đúng | Trọng tài đúng | Vai trò hiếm bị gọi player |
|---|---:|---:|---:|---:|
| Nano / 640 | 200/201 | 0/10 | 0/15 | 25/25 |
| Nano / 1280 | 196/201 | 0/10 | 0/15 | 25/25 |
| Small / 640 | 201/201 | 10/10 | 9/15 | 6/25 |
| Small / 1280 | 197/201 | 8/10 | 10/15 | 7/25 |

Ở small/1280 còn 3 cầu thủ bị gọi trọng tài và 1 không ghép được.
Ở small/640, riêng nguồn Project 12 chưa học có 12/12 cầu thủ và 2/2
trọng tài đúng; không có mẫu thủ môn trong bộ điểm thưa của clip này.
Hai lượt gần nhau của một trọng tài không đại diện độ tin cậy cả trận.
Tại ba nguồn đã học, small/640 đúng 7/13 trọng tài và 10/10 thủ môn;
vẫn chưa phân vai trò ổn định ngay cả trên nguồn đã thấy.

Model medium cũ tại 640 chỉ đúng 6/10 thủ môn, 0/15 trọng tài trên cùng
bộ mẫu; phép so này cho thấy small đã thích nghi tốt hơn trên dữ liệu
hiện có, **không phải phép so công bằng trên các trận chưa học**, do
small mới được bổ sung ảnh từ ba clip. Không gọi kết quả này là test
độc lập hoặc dùng 10/10 để tuyên bố thủ môn đạt 100% tổng quát.

Đã xem lại contact sheet 25 crop vai trò hiếm của small/640; giữ nguyên
nhãn. Các đoạn trọng tài áo xanh bị gọi player còn thấy rõ. Artifact
local `role_training_v1/video_diagnostic/` và protocol/snapshot trong
`fixtures/role_finetune_video_diagnostic_protocol_v1.json` /
`fixtures/role_finetune_video_diagnostic_result_v1.json` cho phép đối chiếu.

## Quyết định và bàn giao

Giữ **small làm checkpoint nghiên cứu ưu tiên**, chưa nối vào upload.
Không thay `data/raw/yolo11n.pt`, bộ lọc ngoài sân, palette/unknown hoặc
ngầm gán nhãn model thành vai trò đã được người rà xác nhận.
Không thay TrackingRow hoặc hợp đồng tọa độ. Tập test đã được mở ở cuối
phiên; các lần cải tiến tiếp theo phải coi đây là bộ hồi quy đã biết,
không tiếp tục gọi nó là một phép kiểm mù mới.

Phần cần cải thiện tiếp là độ phủ nhãn trọng tài ở nhiều màu áo, kích
thước nhỏ và góc quay; cân nhắc crop/oversampling vai trò hiếm trong
train, kiểm trên nguồn/trận mới và đo ổn định theo track. Những hướng
này chưa được chứng minh bằng thử nghiệm hiện tại. Không tăng confidence
để che các lượt bỏ sót hoặc bịa vai trò cho các quan sát chưa rõ.

Weights cục bộ:

- Nano: `data/processed/role_training_v1/nano_final/training/weights/best.pt`,
  SHA-256 `e83de19daea1222c2600bad7e2ca367fcde9c82e0730a1a645acb51c5af4f6a5`.
- Small: `data/processed/role_training_v1/small_final/training/weights/best.pt`,
  SHA-256 `5b07c6ed1e7374c21656dad5e64dfc4d0a0f3e4f66b0068fdaeb051bc7602958`.

Dataset: `data/processed/role_dataset_v1_final/`. Chỉ dùng các lượt
`nano_final`, `small_final`, `final_test`, không dùng preflight đã bỏ.
Snapshot `fixtures/role_finetune_result_v1.json` và
`fixtures/role_dataset_summary_v1.json` khóa kết quả/hash để bàn giao.
Kiểm mã: **489 test Python đạt**, 1 network deselected, 4 warning hiện
có; 11 test mới về mapping vai trò, tách nguồn/pixel, hash và metric IDs.

## Chạy lại

Cần video/weights/dữ liệu gốc cục bộ đúng hash. Từ gốc repo:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.prepare_role_dataset `
  --protocol docs/fixtures/role_finetune_protocol_v1.json `
  --output data/processed/role_dataset_rerun
.\.venv\Scripts\python.exe -m backend.cv.finetune_roles train `
  --dataset data/processed/role_dataset_rerun `
  --protocol docs/fixtures/role_finetune_protocol_v1.json `
  --output data/processed/roles_nano_rerun --model nano
.\.venv\Scripts\python.exe -m backend.cv.finetune_roles train `
  --dataset data/processed/role_dataset_rerun `
  --protocol docs/fixtures/role_finetune_protocol_v1.json `
  --output data/processed/roles_small_rerun --model small
.\.venv\Scripts\python.exe -m backend.cv.finetune_roles test `
  --dataset data/processed/role_dataset_rerun `
  --protocol docs/fixtures/role_finetune_protocol_v1.json `
  --runs data/processed/roles_nano_rerun data/processed/roles_small_rerun `
  --output data/processed/roles_test_rerun
```

Các lệnh từ chối ghi đè output. Mỗi lượt lưu cấu hình, tiến độ, log,
checkpoint, hash và trạng thái. Dữ liệu, ảnh và weights ở local, không
đẩy vào Git. Chỉ mã, nhãn tọa độ, protocol và báo cáo được commit.
