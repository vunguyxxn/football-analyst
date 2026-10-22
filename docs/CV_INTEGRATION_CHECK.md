# Kiểm tra tích hợp tracking và tọa độ sân

Ngày kiểm tra: 22/10/2026. Phạm vi là chạy các module hiện có cùng nhau trên
cửa sổ cuối đã hiệu chỉnh; không thêm tính năng, dependency hoặc đổi hợp đồng
dữ liệu. Đây chưa phải nghiệm thu độ chính xác thống kê cầu thủ.

## Nguồn và cấu hình

- Nguồn: `data/processed/clip_11f23eea/vid1_11f23eea_clean.mp4`, SHA256
  `86f6f04ce05ac464269dfa4d831bef0c12c3654acdd2fa3c1b6379f864597b2e`.
  Bản cắt giây 10–40 từ nguồn `11f23eea`, 1.800 frame, 1280 × 720, 60 FPS.
- YOLO11n, CUDA device 0, image size 1280, confidence 0,1; ByteTrack xuyên
  các chunk 10 giây. Fixture phân đội riêng clip: A trắng, B sẫm/đen,
  trọng tài xanh nhạt. Nhãn theo từng box, chưa ổn định theo track.
- Hiệu chỉnh đoạn 1050–1350 và runtime checkpoints 1080/1125/1200/1275,
  tái tạo hai file `return_*.json` theo `CV_RECALIBRATION.md`.
- Giữ guard 1 m / 90 frame, sân giả định 105 × 68 m. Chỉ sau checkpoint đầu
  mới cấp phép tọa độ. Không chiếu hai đoạn đầu chưa đạt.
- Điểm chiếu là giữa cạnh dưới bbox, không phải mô hình phát hiện bàn chân.
  Tracking video giữ hướng tọa độ sân, chưa chuẩn hóa hướng tấn công.

Lệnh đã chạy từ gốc repo (cần đầu ra mới khi chạy lại):

```powershell
$env:YOLO_CONFIG_DIR = "$PWD\data\processed"
$env:MPLCONFIGDIR = "$PWD\.tmp\matplotlib"
$env:TORCH_HOME = "$PWD\data\processed\.torch"
$env:YOLO_AUTOINSTALL = 'false'
.\.venv\Scripts\python.exe -m backend.cv.track_video data/processed/clip_11f23eea/vid1_11f23eea_clean.mp4 data/processed/clip_11f23eea/return_integrated.mp4 --weights data/raw/yolo11n.pt --device 0 --image-size 1280 --chunk-seconds 10 --team-samples docs/fixtures/vid1_11f23eea_team_samples.json --calibration data/processed/clip_11f23eea/recalibration_check/return_calibration.json --pitch-output data/processed/clip_11f23eea/return_integrated --compensate-camera --landmark-checks data/processed/clip_11f23eea/recalibration_check/return_checks.json
```

## Phạm vi kết luận

Mốc kiểm chứng tay thưa chỉ kiểm tra sai số tại các checkpoint. Kết quả mốc
mới 1110/1260 ở lượt trước (max 0,39/0,52 m) không chứng minh độ chính xác
điểm chân hay toàn bộ frame. Không dùng guard `tracked` hoặc giới hạn tốc
độ 40 km/h làm bằng chứng tốc độ thực đúng.

Heatmap đếm số quan sát theo ô 14 × 21, gồm cả điểm có bước chuyển động bị
loại. Tổng quãng đường là theo đoạn và track, chưa phải danh tính cầu thủ,
không phải tổng trận. Các bản đồ QA được vẽ cục bộ để rà soát; backend vẫn
xuất JSON theo hợp đồng.

## Kết quả chạy thật

CLI hoàn thành 1.800 frame, 3 chunk, tốc độ xử lý trung bình 6,08 FPS trên
CUDA. Giải mã lại cả nguồn và video đầu ra đủ 1.800 frame, cùng kích thước
1280 × 720 và 60 FPS. Không suy tốc độ thời gian thực từ kết quả này.

| Mục kiểm tra | Kết quả |
|---|---:|
| Frame ngoài phạm vi hiệu chỉnh (`uncalibrated`) | 1.499 |
| Frame chờ checkpoint đầu | 30 |
| Frame được guard cấp phép | 271 (1080–1350) |
| Bản ghi `TrackingRow` | 5.384 |
| Quan sát A / B / trọng tài / unknown | 2.489 / 2.452 / 334 / 109 |
| ID khác nhau trong cửa sổ | 50 |
| Track có ít nhất 120 quan sát | 17 |
| Track dưới 30 quan sát | 17 |
| Track có khoảng trống giữa các quan sát | 17 |
| Track đổi nhãn vai trò ít nhất một lần | 19 (104 lần đổi) |
| Bước chuyển động 0,5 giây bị ngưỡng tốc độ loại | 1 |

271 frame kéo dài 4,5167 giây video, khoảng cách giữa thời điểm đầu/cuối là
4,5 giây. Tương ứng giây 28,0–32,5 của nguồn thô trước khi cắt. Không có
tọa độ xuất ngoài cửa sổ này; tất cả hữu hạn, trong sân, không trùng cặp
`(frame, track_id)`, thời gian đúng `frame / 60`. Schema TrackingRow và
AnalysisResult đọc lại hợp lệ; tổng samples và tổng các ô heatmap theo
track đều bằng số dòng tọa độ.

Các tổng nhãn trên chỉ tính cửa sổ có tọa độ. Tổng `team_observations` trong
stdout CLI tính cả video, nên không dùng thay các số này.

## Kiểm tra ID và điểm chiếu

Đã xem ảnh đầu/giữa/cuối 1080/1200/1350, các cặp có bước nhảy lớn, ảnh nguồn
phóng vùng cầu thủ/trọng tài và bản đồ vị trí tương ứng. Đây là rà soát mẫu,
chưa phải bộ ground truth để tính IDF1 hoặc độ chính xác bàn chân.

- ID 251, 237, 122, 165 đều có đủ 271 quan sát liên tiếp và nhãn nhất quán
  trong cửa sổ. Điều này chỉ chứng minh tính liên tục quan sát của các ID đó.
- Tại frame 1200, ID 134/306 nằm cách nhau khoảng 0,22 m ở cùng vùng cầu thủ
  áo đen, bbox chồng nhau. Frame 1310 có ID 134/330 cách khoảng 0,18 m ở cùng
  vùng người. Cần xử lý track/detection trùng trước khi cộng heatmap hoặc
  đếm cầu thủ; điều kiện không trùng `(frame, track_id)` chưa ngăn được lỗi này.
- ID 324 có nhãn A 13 lần, trọng tài 37 lần, unknown 4 lần. Nguồn frame
  1296–1298 cho thấy trọng tài và cầu thủ áo trắng gần/chồng nhau. Tọa độ ID
  này nhảy 2,77 rồi 3,80 m trong hai bước frame, là dấu hiệu điểm chiếu hoặc
  gán đối tượng không ổn định; chưa đủ nhãn để quy toàn bộ lỗi cho ID switch.
- Bbox giữa cạnh dưới dao động theo tư thế, che khuất và kích thước người
  xa. Có staff sát biên bị gán B/trọng tài trong video; giới hạn tọa độ sân
  loại được một số quan sát ngoài sân nhưng chưa phải bộ lọc vai trò.
- Trong 5.310 cặp cùng ID ở hai frame liên tiếp, 793 cặp (14,93%) cho tốc độ
  suy trực tiếp >40 km/h; p50 khoảng 5,15, p95 khoảng 80,76 km/h. Đây là
  **diagnostic độ rung**, không phải tốc độ chạy thực tế. Ví dụ lớn nhất
  khoảng 820,49 km/h (3,80 m / 1 frame) cho thấy không được diễn giải trực tiếp.
- Bộ chỉ số lấy mẫu 0,5 giây, khác phép tính từng frame trên: chỉ loại một
  bước của ID 261. Tốc độ lưu đều ≤40 không có nghĩa đã sạch rung, trùng ID
  hoặc sai số nhỏ. Các quãng đường lưu vẫn là kết quả thử nghiệm.

Kết luận: nghiệm thu được việc các module chạy cùng nhau, xuất JSON đúng
phạm vi và tạo dữ liệu heatmap nhất quán. **Chưa nghiệm thu độ chính xác
thống kê cầu thủ, quãng đường/tốc độ hoặc toàn clip; chưa chuyển bước 5.**
Ưu tiên tiếp theo là xử lý detection/track trùng và gãy ID trên một đoạn có
nhãn đối chiếu, sau đó ổn định nhãn vai trò và điểm chiếu trước khi đánh giá
lại chỉ số. Không sửa thuật toán trong lượt kiểm tra này.

## Artifact và kiểm tra

Thư mục cục bộ `data/processed/clip_11f23eea/return_integrated/` chứa:

- `tracking.jsonl`, `camera_quality.jsonl`, `metrics.json`: đầu ra CLI.
- `validation.json`: thống kê theo track, khoảng trống và các bước nhảy lớn.
- `accepted_window.mp4`: 271 frame được cấp phép, đã giải mã kiểm tra đủ.
- `frame_{1080,1200,1350}.jpg`, `jump_*.jpg`, `duplicate_1310.jpg` và
  `source_crop_*.jpg`: ảnh rà soát.
- `pitch_snapshots.png`, `heatmaps.png`, `team_heatmaps.json`: bản đồ QA;
  nhãn đội là dự đoán theo box và có thể đếm trùng người.

Video đầy đủ: `data/processed/clip_11f23eea/return_integrated.mp4`; stdout
lưu tại `return_integrated_run.json` cạnh video. Media không commit.

Helper kiểm tra cục bộ `.tmp/validate_integrated.py` chạy bằng
`$env:PYTHONPATH="$PWD"; .\.venv\Scripts\python.exe .tmp/validate_integrated.py`.
Helper này không được đóng gói cho fresh clone. Các assertions đã chạy:
schema, phạm vi, thời gian, trùng khóa, tổng heatmap/samples, giới hạn tốc
độ đã lưu và giải mã đủ ba video (nguồn, đầy đủ đầu ra, cửa sổ được cắt).

Hồi quy: `.\.venv\Scripts\python.exe -m pytest -q` — **99 passed, 1 network
test deselected**, một cảnh báo Starlette có từ trước. Không thêm thư viện
để xử lý cảnh báo này. Không thay đổi mã ứng dụng hoặc hợp đồng dữ liệu.

## Bổ sung bộ lọc người trong sân — 22/10/2026

Theo yêu cầu chỉ đóng khung/theo dõi/phân tích người trong đường biên trắng,
CLI bổ sung `--on-pitch-only`. `PitchCalibration.locate` dùng chung phép
chiếu điểm giữa cạnh dưới bbox với `project`; lọc detection trước ByteTrack
và phân đội. Không có ma trận hợp lệ thì đầu vào tracker rỗng, không vẽ khung
người. CameraMotion vẫn loại toàn bộ người khỏi vùng ước lượng chuyển động.
Chi tiết giới hạn sát biên và cách bật cờ tại `CV_TRACKING.md`.

Chạy lại đúng lệnh ở trên với tên video `on_pitch_only.mp4`, thư mục đầu ra
`on_pitch_only` và thêm `--on-pitch-only`. Hoàn thành 1.800 frame / 3 chunk,
7,01 FPS. Guard giữ 1.499 uncalibrated / 30 chờ / 271 tracked, không nới ngưỡng.
Xuất 5.365 dòng, A/B/referee/unknown = 2480/2443/333/109. Tổng nhãn CLI bằng
tổng tọa độ trong sân, không còn cộng người ngoài sân vào `team_observations`.
Tọa độ từ frame 1081–1350: frame 1080 đang xác nhận track mới của ByteTrack.
Không coi thay đổi ID/số mẫu so với lượt cũ là tăng độ chính xác tracking.

Đã xem frame 1200/1350: người đứng ngoài đường biên gần camera/khu kỹ thuật
không còn có khung; frame 1351 hết phạm vi hiệu chỉnh không có khung người.
Giải mã nguồn và video đầy đủ đều đủ 1.800 frame, video cửa sổ đủ 271 frame,
cùng 1280 × 720 / 60 FPS. Assertions schema, tọa độ, thời gian, khóa, tổng
heatmap/samples và đối chiếu nhãn CLI đều qua. Helper khảo sát cục bộ là
`.tmp/validate_on_pitch.py`, không được đóng gói cho fresh clone.

Artifacts mới trong `data/processed/clip_11f23eea/on_pitch_only/`: JSONL,
metrics, validation, ảnh `check_*.jpg`, bản đồ QA và `accepted_window.mp4`.
Video đầy đủ `on_pitch_only.mp4`, stdout `on_pitch_only_run.json` nằm cạnh
thư mục này. Giữ nguyên bộ kết quả cũ, không commit media/cache.

Test tích hợp mới dùng codec và ByteTrack thật, detector giả lập có người
trong sân, ngoài biên phải và thân chồng vùng sân nhưng chân ngoài biên gần.
Kiểm tra đầu vào tracker, bbox vẽ, classifier, JSON và samples; kiểm tra cả
chờ checkpoint, hết hạn và hết đoạn hiệu chỉnh. Camera vẫn nhận đủ bbox gốc.
Hồi quy toàn bộ: `python -m pytest -q --basetemp .tmp/pytest_on_pitch` bằng
Python trong `.venv`: **102 passed, 1 network test deselected**, cảnh báo
Starlette cũ. Không đổi schema/API/dependency.

Bộ lọc này giải quyết phạm vi theo dõi, chưa sửa bbox/ID trùng hay nhãn rung.
Vẫn có 50 ID trong cửa sổ; chưa nghiệm thu tốc độ/quãng đường hay bước 5.
