# Kiểm chứng detector vai trò

Ngày 02/11/2026. **Ứng viên đã thử chưa đạt để đưa vào luồng upload.**
Model có lớp riêng cho trọng tài/thủ môn nhưng vẫn nhầm phần lớn các
lượt quan sát đó thành cầu thủ. Không thay model đang phục vụ người dùng.

## Model và phép thử

Ứng viên là [martinjolif/yolo-football-player-detection](https://huggingface.co/martinjolif/yolo-football-player-detection/tree/5e83fafa8d564243001ce8e063612a618a138fbe),
YOLO11m, revision `5e83fafa8d564243001ce8e063612a618a138fbe`.
Model card công bố AGPL-3.0; lớp trong checkpoint thực tế:
`0: ball, 1: goalkeeper, 2: player, 3: referee`.
Weights SHA-256:
`69c652bfa9814ef882c439617f04b8fd5749b6b8455aaa3c36110bc2e802aadd`.
Đã kiểm hash khớp LFS từ metadata nguồn trước khi chạy. File 40.583.084
byte lưu cục bộ tại `data/raw/role_detector_v1/`, không commit weights.
Không dùng checkpoint không rõ license của StrikerAI; không thêm thư viện.

Chọn model medium này để sàng lọc một checkpoint có nguồn và lớp vai trò
rõ ràng, không phải quyết định thay nano bằng medium trên RTX 3050 6GB.
Baseline là YOLO11n COCO hiện có, chỉ lớp person; quy đổi person thành
player để thấy giới hạn của detector thuần. **Đây không phải so sánh với
toàn bộ pipeline palette/unknown đã sửa**, cũng không phải so model cùng
kích thước kiến trúc.

Đã khóa protocol trước khi chạy dự đoán:
`fixtures/role_detector_protocol_v1.json`. Hai mức imgsz 640/1280,
confidence 0,25, NMS IoU 0,7, CUDA batch 1. Chỉ chạy player/goalkeeper/
referee; bóng không tham gia. Không huấn luyện hay đổi ngưỡng theo kết quả.

Bộ mẫu gồm 15 frame của 4 clip, tổng 226 lượt có nhãn vai trò: 201 cầu
thủ tuyến ngoài, 10 thủ môn và 15 trọng tài. Có hai nguồn nhãn:

- Clip Project 15 mẫu: 9 frame, 165 cầu thủ, 6 thủ môn, 9 trọng tài;
  bbox đã gán vai trò ở phiên trước, lấy từ detector, không phải nhãn
  đầy đủ cho mọi người trong ảnh. Ghép một-một theo IoU ≥ 0,5.
- Ba clip Project 12/15(1)/15(2): mỗi clip 2 frame, 36 cầu thủ, 4 thủ
  môn, 6 trọng tài; nhãn điểm chân thưa, thêm 6 điểm người ngoài sân
  chỉ dùng đối chiếu, không vào mẫu số vai trò. Ghép một-một theo
  khoảng cách chân ≤ 35 px; kiểm nhạy ở 25/50 px.

Ghép theo vị trí trước khi xem lớp, không dùng nhãn vai trò để chọn
box thuận lợi. Hash nguồn video và file nhãn được kiểm trước suy luận;
giữ cả hai frame khó của Project 15(2) dù baseline tracking cũ thiếu box.
Chưa áp bộ lọc biên sân vào phép đo detector này; chưa đánh giá khả năng
loại người ngoài sân bằng model vai trò.

Các nhãn cũ do agent rà, chưa độc lập hoặc làm mù; các frame gần nhau
có thể chứa cùng người. Chưa đối chiếu tập huấn luyện của model để loại
trừ trùng nguồn. Vì vậy đây là **sàng lọc trên mẫu phát triển**, không phải
accuracy tổng quát hay số người khác nhau. Không công bố precision,
mAP hoặc recall đầy đủ cho mọi người trên sân từ bộ nhãn thiếu này.

## Kết quả

Số đúng / lượt có nhãn, tính cả lượt không ghép được là không đúng:

| Detector / imgsz | Cầu thủ | Thủ môn | Trọng tài | Thủ môn/trọng tài bị gọi là player |
|---|---:|---:|---:|---:|
| COCO11n / 640 | 194/201 | 0/10 | 0/15 | 17/25 |
| COCO11n / 1280 | 201/201 | 0/10 | 0/15 | 25/25 |
| Football11m / 640 | 200/201 | 6/10 | 0/15 | 19/25 |
| Football11m / 1280 | 196/201 | 4/10 | 2/15 | 19/25 |

Ở 640, ứng viên gọi nhầm 1 cầu thủ thành trọng tài. Ở 1280, ứng viên
gọi nhầm 3 cầu thủ thành trọng tài và bỏ sót 2 cầu thủ theo gate ghép.
Tăng kích thước ảnh không cải thiện đồng đều các vai trò. Các gate chân
25/35/50 px cho cùng tổng kết trên bộ mẫu này; không chọn gate sau thử.

Chi tiết ứng viên ở imgsz 1280:

| Clip | Cầu thủ đúng | Thủ môn đúng | Trọng tài đúng |
|---|---:|---:|---:|
| Project 15 mẫu | 160/165 | 2/6 | 1/9 |
| Project 12 | 12/12 | Không có mẫu | 0/2 |
| Project 15(1) | 12/12 | 0/2 | 0/2 |
| Project 15(2) | 12/12 | 2/2 | 1/2 |

Đã xem lại contact sheet 28 crop: toàn bộ 25 lượt trọng tài/thủ môn và
3 cầu thủ bị gán trọng tài ở mức 1280. Ảnh gốc phù hợp với nhãn vai trò
đã có; các lỗi áo xanh nhạt bị gọi là player và áo đỏ bị gọi là referee
không phải chỉ do bảng tổng hợp. Giữ nguyên nhãn, không sửa theo model.
Đây là kiểm lại cùng agent, không biến nhãn thành kiểm định độc lập.

## Tài nguyên và khả năng chạy lại

Đo trên RTX 3050 6GB Laptop GPU, PyTorch 2.8.0+cu128,
Ultralytics 8.3.221. Trung bình 15 lần predict, sau warm-up, có đồng bộ
CUDA; gồm tiền/hậu xử lý, không gồm giải mã video:

| Detector / imgsz | ms/frame | Peak tensor allocated (MiB) |
|---|---:|---:|
| COCO11n / 640 | 25,9 | 58,3 |
| COCO11n / 1280 | 75,8 | 106,4 |
| Football11m / 640 | 81,7 | 157,2 |
| Football11m / 1280 | 99,7 | 294,9 |

Số memory chỉ là tensor của tiến trình thử, không phải tổng VRAM;
15 frame không đủ làm benchmark lâu dài. Không dùng nghịch đảo các số
trên để hứa FPS toàn hệ thống. Model đọc từng frame, không giữ cả video.

```powershell
.\.venv\Scripts\python.exe -m backend.cv.evaluate_role_detector `
  --protocol docs/fixtures/role_detector_protocol_v1.json `
  --output data/processed/role_detector_screening_rerun
.\.venv\Scripts\python.exe -m pytest -q tests/test_role_detector_evaluation.py
```

Lệnh cần weights và video cục bộ đúng hash; từ chối ghi đè thư mục đã
có kết quả. Kết quả máy đọc và hash artifact tại
`fixtures/role_detector_result_v1.json`. Quan sát/prediction đầy đủ và
ảnh kiểm nằm ở `data/processed/role_detector_screening_v1/` (local).

## Quyết định

**Không duyệt ứng viên này cho production/upload.** Chỉ có thêm tên lớp
trong checkpoint chưa đủ chứng minh phân loại vai trò hoạt động tốt.
Luồng hiện tại tiếp tục giữ unknown khi màu ngoài hai đội; không lấy
nhãn player của ứng viên làm bằng chứng người đó là cầu thủ tuyến ngoài.

Hướng kế tiếp phù hợp là chuẩn bị bộ nhãn vai trò đầy đủ, tách theo trận
train/val/test rồi thử YOLO nano/small trong stack hiện có. Giữ lớp thủ
môn riêng, đo lỗi nhầm vào tuyến ngoài và chi phí GPU. Cần nhãn độc lập,
đa màu áo và các góc quay trước khi duyệt kết quả tốt; không chỉ tăng
confidence hoặc cố định màu trọng tài của một clip. Chưa triển khai
huấn luyện hoặc tích hợp trong nhiệm vụ kiểm chứng này. DATA_CONTRACT,
tracking, hiệu chỉnh sân và giao diện không đổi.

Kiểm tra mã: 4 test mới đạt; toàn bộ bộ test Python đạt 478 test,
1 network test deselected và 4 warning từ thư viện hiện có.
