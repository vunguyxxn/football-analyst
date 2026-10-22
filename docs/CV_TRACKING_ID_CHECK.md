# Kiểm tra khung trùng và tính liên tục ID

Ngày: 22/10/2026. Phạm vi: sửa nguyên nhân khung trùng trước ByteTrack,
đối chiếu trước/sau trên đoạn cuối hiện có. Giữ bộ lọc người trong sân,
guard 1 m / 90 frame, cấu hình camera và phân đội. Không đổi hợp đồng,
dependency hoặc nhận diện danh tính cầu thủ thật.

## Nguyên nhân và thay đổi

Tại frame 1200, YOLO11n trả hai bbox cho cùng vùng một cầu thủ áo đen:

| Bbox (x1, y1, x2, y2), pixel | Confidence |
|---|---:|
| (576,97; 343,38; 605,38; 384,46) | 0,5545 |
| (577,17; 343,90; 594,68; 385,20) | 0,2622 |

IoU khoảng 0,602. Cả hai lọt qua NMS mặc định của detector và có thể tạo
track riêng. Supervision ByteTrack không loại tất cả cặp trùng đang active;
vì vậy chỉ ẩn bớt nhãn khi vẽ sẽ vẫn làm sai thống kê.

Thêm `suppress_duplicate_people` trong `backend/cv/track_video.py`: gọi
`Detections.with_nms(threshold=0.5)` của supervision đang có, giữ bbox có
confidence cao hơn. Áp dụng sau lọc trong sân và **trước** ByteTrack, phân
đội, xuất JSON và vẽ. Không gom người theo khoảng cách mét, không gộp ID
hậu kỳ. CameraMotion vẫn nhận đủ bbox thô như trước để giữ cách ước lượng
camera. Thay đổi áp dụng mặc định, không cần cờ mới.

Các ngưỡng ByteTrack, buffer và minimum_consecutive_frames giữ nguyên.
Đã thử xác nhận 3 lần trong helper nghiên cứu: giảm thêm track ngắn nhưng
không giảm số lần đổi ID trong mẫu đánh giá, nên không đưa vào ứng dụng.

## So sánh trên cùng detection

Nguồn bản cắt SHA256
`86f6f04ce05ac464269dfa4d831bef0c12c3654acdd2fa3c1b6379f864597b2e`,
frame 1080–1350, 1280 × 720 / 60 FPS. Chạy YOLO11n CUDA, image size 1280,
confidence 0,1 để lưu bbox/confidence; dùng ma trận guard replay đã có
để giữ cùng vùng sân. ByteTrack nhận 1080 bước rỗng trước đoạn này để tái
tạo trạng thái của chế độ chỉ trong sân. Baseline tái hiện đúng 5.365 quan
sát / 50 ID của lượt `on_pitch_only` trước sửa.

| Chỉ số trong cửa sổ | Trước | Sau NMS 0,5 |
|---|---:|---:|
| Quan sát tracker xuất | 5.365 | 5.215 |
| ID khác nhau | 50 | 30 |
| Track dưới 30 quan sát | 17 | 5 |
| Cặp bbox đầu ra IoU > 0,5 (cộng qua frame) | 134 | 0 |

834 detection đầu vào bị loại, khác mức giảm 150 quan sát vì nhiều detection
chưa được tracker xác nhận. Số cặp IoU bằng 0 là thuộc tính của bộ lọc,
không chứng minh không còn trùng người hoặc không lọc nhầm mọi tình huống.
30 ID không phải 30 cầu thủ; vẫn còn gãy ID khi che khuất.

## Mẫu định danh quan sát thưa

Fixture `docs/fixtures/vid1_11f23eea_id_samples.json` có 49 bbox vẽ từ ảnh
nguồn không overlay: 7 người tại frame 1100/1140/1180/1220/1260/1300/1340.
Định danh chỉ dùng trong đoạn ngắn này. Có cầu thủ áo trắng gần camera,
cầu thủ áo đen giữa sân, các cầu thủ gần nhau và cặp cầu thủ/trọng tài che
khuất. Nhãn do agent quan sát, chưa được người độc lập rà soát.

Ngưỡng NMS 0,5 đã khóa trước khi vẽ bộ nhãn này; frame phát triển 1200/1310
không thuộc bộ nhãn. Đánh giá vẫn là kiểm tra sơ bộ trên cùng clip, chưa là
tập kiểm định độc lập hoặc đo IDF1/MOTA đầy đủ.

Ghép mỗi bbox dự đoán vào bbox nhãn có IoU lớn nhất nếu >=0,3. Một nhãn có
nhiều bbox được tính là nhiều ID; chọn bbox IoU cao nhất làm ID đại diện
để đếm thay đổi giữa hai quan sát có ghép liên tiếp của cùng người. Không
coi dự đoán không ghép là false positive toàn ảnh vì chỉ gán nhãn 7 người.

| Trên 49 quan sát có nhãn | Trước | Sau |
|---|---:|---:|
| Quan sát ghép được | 48 | 48 |
| Quan sát ghép nhiều ID | 2 | 0 |
| Lần đổi ID giữa các ảnh mẫu | 10 | 2 |

Sáu trong bảy người không đổi ID giữa các mẫu sau sửa. Cầu thủ `white_runner`
vẫn đổi ID hai lần ở đầu đoạn; trọng tài bị thiếu ghép ở frame 1300 khi che
khuất, cả trước và sau. Không suy từ 48/49 thành recall toàn clip. Không
khẳng định mọi người đứng sát nhau đều được giữ, nhất là khi IoU >0,5 do
che khuất thật. Đây là giới hạn cần đánh giá thêm trên dữ liệu khó hơn.

## Kiểm thử

`tests/test_tracking_duplicates.py` dùng ByteTrack thật để kiểm tra cặp bbox
thực ở trên xuất một ID duy nhất xuyên qua giai đoạn có detection trùng và
mất detection ngắn 5 frame. Kiểm tra thêm người đứng gần, người nhỏ bị che
một phần (không dùng intersection-over-smaller để gộp), và đầu vào rỗng.
Các test pipeline cũ tiếp tục kiểm tra codec, chunk, lọc ngoài sân và guard.

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp/pytest_id_full
```

Kết quả: **105 passed, 1 network test deselected**, cảnh báo Starlette cũ.
Các helper nghiên cứu `.tmp/cache_id_check.py`, `.tmp/replay_id_check.py`,
`.tmp/evaluate_id_samples.py` dùng cache cục bộ, không được đóng gói cho
fresh clone. Cache và kết quả replay nằm trong
`data/processed/clip_11f23eea/id_check/`, không commit media/cache.

## Chạy lại pipeline đầy đủ

Giữ lệnh lần lọc ngoài sân, chỉ đổi tên đầu ra mới; NMS được bật mặc định:

```powershell
$env:YOLO_CONFIG_DIR = "$PWD\data\processed"
$env:MPLCONFIGDIR = "$PWD\.tmp\matplotlib"
$env:TORCH_HOME = "$PWD\data\processed\.torch"
$env:YOLO_AUTOINSTALL = 'false'
.\.venv\Scripts\python.exe -m backend.cv.track_video data/processed/clip_11f23eea/vid1_11f23eea_clean.mp4 data/processed/clip_11f23eea/id_deduplicated.mp4 --weights data/raw/yolo11n.pt --device 0 --image-size 1280 --chunk-seconds 10 --team-samples docs/fixtures/vid1_11f23eea_team_samples.json --calibration data/processed/clip_11f23eea/recalibration_check/return_calibration.json --pitch-output data/processed/clip_11f23eea/id_deduplicated --compensate-camera --landmark-checks data/processed/clip_11f23eea/recalibration_check/return_checks.json --on-pitch-only
```

Lệnh hoàn thành 1.800 frame / 3 chunk, CUDA device 0, trung bình 7,66 FPS.
Guard giữ 1.499 ngoài hiệu chỉnh / 30 chờ / 271 cấp phép. Có 5.215 tọa độ,
30 ID, 19 track ít nhất 120 mẫu; nhãn A/B/referee/unknown = 2450/2354/312/99.
Tọa độ vẫn chỉ frame 1081–1350, không mở rộng sang đoạn chưa đạt.

Đối chiếu từng khóa frame+ID và tọa độ với replay: khớp đủ 5.365 dòng
baseline và 5.215 dòng sau sửa, sai khác tọa độ lớn nhất khoảng 3,04e-14 m
(do số học). Nhờ đó kết quả đối chiếu bbox của replay áp dụng được cho lượt
pipeline này. Đây không phải sai số so với vị trí thật trên sân.

Giải mã nguồn/đầu ra đủ 1.800 frame, bản cắt cửa sổ đủ 271 frame, cùng
1280 × 720 / 60 FPS. Schema, khóa, thời gian, phạm vi, heatmap/samples và
tổng nhãn CLI khớp số tọa độ đều qua. Đã xem ảnh 1200/1300/1310: cầu thủ
áo đen giữa sân giữ ID 13, không còn cặp khung trùng đã thấy ở 1200/1310;
người ngoài sân gần camera vẫn không có khung. Nhãn đội/trọng tài còn rung.

761/5169 cặp frame liên tiếp vẫn cho tốc độ suy thô >40 km/h; bộ chỉ số
0,5 giây không loại bước nào. Không dùng kết quả này để nghiệm thu tốc độ
hay quãng đường: nhiễu bbox và các lần đổi ID còn lại chưa được xử lý xong.

Artifacts mới ở `data/processed/clip_11f23eea/id_deduplicated/`: JSONL,
metrics, validation, `accepted_window.mp4`, ảnh kiểm tra và bản đồ QA.
Video đầy đủ `id_deduplicated.mp4`, stdout `id_deduplicated_run.json` ở
cạnh thư mục. Helper kiểm tra `.tmp/validate_id_fix.py` và đối chiếu
`.tmp/compare_id_pipeline.py` chỉ dùng cục bộ; giữ nguyên kết quả trước sửa.

Nghiệm thu sửa khung trùng và cải thiện ID trên đoạn đã kiểm tra. Chưa có
ReID/danh tính thật, chưa bảo đảm ID liên tục qua mọi che khuất hoặc cắt
cảnh; chưa chuyển bước 5. Việc tiếp theo là ổn định nhãn vai trò và điểm
chiếu rồi đánh giá lại chỉ số, đồng thời mở rộng bộ nhãn tracking khó hơn.
