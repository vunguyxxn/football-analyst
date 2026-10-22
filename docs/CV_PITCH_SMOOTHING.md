# Làm mượt tọa độ và ngắt chuỗi chuyển động

Ngày: 22/10/2026. Phạm vi bước 4: giảm nhiễu điểm giữa cạnh dưới bbox và
không cộng quãng đường qua điểm lỗi. Không đổi tracker, nhãn đội, ma trận
camera, guard 1 m / 90 frame, dependency hoặc schema/API. Chưa có mô hình
phát hiện bàn chân và chưa đo được quãng đường/tốc độ thực địa.

## Cách bật và đầu ra

Thêm `--smooth-pitch` vào lệnh tracking có `--calibration` và `--pitch-output`.
Thiếu hiệu chỉnh thì báo lỗi. Cờ tắt mặc định để có thể giữ phép đo thô và
so sánh, các lệnh cũ tiếp tục tương thích. Trong lần chạy có cờ:

- `tracking_raw.jsonl`: TrackingRow trước bộ lọc, chỉ điểm chiếu hợp lệ
  trong sân và được guard cấp phép. Giữ nguyên dữ liệu này để đối chiếu.
- `tracking.jsonl`: TrackingRow sau lọc; giữ ID/frame/thời gian/nhãn, thay
  tọa độ bằng ước lượng có độ trễ, không nội suy thêm dòng.
- `smoothing_quality.jsonl`: một dòng cho mỗi điểm thô, gồm trạng thái và
  yêu cầu ngắt mốc tính chỉ số. Đây là diagnostic nội bộ, không schema mới.
- `metrics.json`: chỉ cộng điểm đã lọc, có `pitch_smoothing: true`.

Khung và nhãn trên video giữ nguyên, vẫn theo người trong sân. Tổng
`team_observations` CLI là quan sát bbox/nhãn, không bằng số tọa độ sau lọc;
ở chế độ chỉ trong sân, tổng này khớp số dòng **thô**. Heatmap chỉ số sau
lọc đếm các tọa độ được xuất, không tính điểm bị bỏ hay thời gian chưa thấy.

## Bộ lọc nhân quả

`PitchSmoother` tách trạng thái theo `(segment, track_id)`, không dùng frame
tương lai. Trước khi lọc, khoảng cách thô so với điểm thô được chấp nhận gần
nhất phải <= `40/3,6 × dt + 0,5 m`. Phần 0,5 m là dung sai nhiễu heuristic,
không phải chứng nhận sai số hoặc giới hạn tốc độ từng frame.

Điểm vượt điều kiện bị bỏ và ngắt mốc tính quãng đường ngay. Ba điểm mới liên
tiếp nhất quán có thể mở chuỗi cục bộ mới, không nối tới vị trí cũ. Khoảng
vắng >0,25 giây khởi tạo lại; segment/ID mới cũng không nối lịch sử. Trạng
thái vắng >1 giây bị xóa, kiểm tra cả frame không có điểm chiếu hợp lệ.

Lấy trung vị ba điểm thô gần nhất, sau đó EMA theo thời gian với hằng số
0,08 giây (`alpha = 1 - exp(-dt/0,08)`). Đây là trung vị + làm mượt tọa độ,
không cắt tốc độ về 40. Chờ ít nhất 3 điểm và khoảng thời gian >=0,08 giây;
giữ lịch sử tối đa 0,2 giây. Với 60 FPS, đầu chuỗi bỏ 5 frame khởi tạo.
Không chiếu/ép điểm vượt biên trở lại vạch sân.

`PitchMetrics.break_chain` xóa anchor ngay khi bộ lọc yêu cầu, giữ tổng của
các phần quan sát hợp lệ. Ngưỡng >40 km/h trên cặp lấy mẫu 0,5 giây cũ vẫn
được giữ riêng. `rejected_steps` của metrics không bao gồm mọi lần bộ lọc
tọa độ bỏ điểm; xem diagnostic để tránh nhầm hai bộ đếm.

## Kết quả replay cùng clip

Nguồn là 5.215 dòng / 30 ID của `team_roles_final`, SHA256 bản cắt
`86f6f04ce05ac464269dfa4d831bef0c12c3654acdd2fa3c1b6379f864597b2e`.

| Mục | Thô | Sau lọc |
|---|---:|---:|
| Dòng tọa độ | 5.215 | 4.935 |
| ID có tọa độ | 30 | 27 |
| Cặp cùng ID ở hai frame liên tiếp | 5.169 | 4.847 |
| Cặp suy ra tốc độ >40 km/h | 761 | 16 |
| p95 tốc độ từng frame (diagnostic) | 79,16 | 23,47 km/h |

Có 177 điểm chờ khởi tạo, 90 `jump_rejected`, 13 `reacquiring`, 4.935
`accepted`. 135 yêu cầu ngắt mốc gồm cả khởi tạo/gap, không tương đương 135
biến cố vật lý độc lập. Ba ID ngắn không đủ khởi tạo nên chưa có tọa độ lọc;
không phải xóa danh tính khỏi tracker.

Để tách hiệu quả bỏ điểm khỏi làm mượt, so sánh trên đúng cùng 4.847 cặp
frame/ID còn lại: dữ liệu thô có 648 cặp >40, sau lọc có 16; p95 71,11 ->
23,47 km/h. p50 lại tăng 4,90 -> 7,20 km/h; không khẳng định mọi mức tốc độ
đều giảm hoặc bộ lọc làm quãng đường chính xác hơn. Đây là số suy từ chuyển
tọa độ từng frame, không phải tốc độ cầu thủ thực tế.

Đã xem đường x/y của ID 1 (di chuyển), 6 (đoạn di chuyển ít), 14 (nhiễu lớn
khi gần cầu thủ). Đồ thị có chỗ trễ và khoảng trống, không nối các frame bị
thiếu. Chưa có bằng chứng người nào thật sự đứng yên trên sân hay vị trí
chuẩn từng frame để tính sai số thực của clip này.

## Kiểm tra có vị trí chuẩn biết trước

- Điểm đứng yên (40,34), nhiễu đều ±0,1 m theo hai trục, seed 42: RMSE
  thô 0,0806 m -> lọc 0,0320 m trên phần sau khởi tạo.
- Đi 2 m/s rồi dừng: độ lệch vị trí tối đa 0,1773 m (khoảng 89 ms độ trễ
  trong chuyển động đều); sau dừng 250 ms sai khác tối đa còn 0,0078 m.
- Test đường thẳng 2 m/s kiểm tra tốc độ lấy mẫu gần 7,2 km/h, quãng đường
  trên khoảng thời gian được cộng sai khác <0,15 m. Thời gian khởi tạo và
  đuôi ngắn hơn 0,5 giây không được coi là đã đo đủ.
- Điểm nhảy đơn, nhảy vị trí kéo dài, khoảng mất dấu và biên hiệu chỉnh:
  không cộng khoảng nhảy vào tổng; các ID không dùng chung lịch sử.
- Chuyển động thử >40 vẫn có thể cho ước lượng >40, chứng minh không có
  thao tác ép số về 40; bộ metrics tự loại cặp vượt ngưỡng của nó.

Đây là test tổng hợp chức năng và sai số có kiểm soát, không thay thế dữ liệu
tracking đã gán nhãn ngoài thực tế. Làm mượt có thể giảm tốc độ đỉnh, cắt góc
đường chạy và gây trễ; chia chuỗi làm thiếu quãng đường. Camera/ID sai mà
vẫn qua các ngưỡng vẫn có thể tạo chỉ số sai. 16 cặp nhanh còn lại cho thấy
chưa được nghiệm thu tốc độ/quãng đường của clip chỉ từ diagnostic.

## Lệnh kiểm tra

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp/pytest_pitch_full
```

**128 passed, 1 network test deselected**, cảnh báo Starlette cũ. Test mới
gồm giảm nhiễu, trễ/dừng, chuyển động biết trước, mất dấu/nhảy/đổi segment,
không ép tốc độ và pipeline codec/ByteTrack có/không detection/phân đội.

Helpers cục bộ `.tmp/replay_pitch_smoothing.py`, `.tmp/evaluate_pitch_smoothing.py`
và artifacts `data/processed/clip_11f23eea/pitch_smoothing_check/` gồm báo cáo,
tọa độ/metrics replay và `coordinate_comparison.png`. Helper chưa được đóng
gói cho fresh clone; không commit cache, ảnh hoặc video.

## Chạy lại pipeline đầy đủ

Lệnh từ gốc repo (cần đầu ra mới khi chạy lại):

```powershell
$env:YOLO_CONFIG_DIR = "$PWD\data\processed"
$env:MPLCONFIGDIR = "$PWD\.tmp\matplotlib"
$env:TORCH_HOME = "$PWD\data\processed\.torch"
$env:YOLO_AUTOINSTALL = 'false'
.\.venv\Scripts\python.exe -m backend.cv.track_video data/processed/clip_11f23eea/vid1_11f23eea_clean.mp4 data/processed/clip_11f23eea/pitch_smoothed.mp4 --weights data/raw/yolo11n.pt --device 0 --image-size 1280 --chunk-seconds 10 --team-samples docs/fixtures/vid1_11f23eea_team_samples.json --calibration data/processed/clip_11f23eea/recalibration_check/return_calibration.json --pitch-output data/processed/clip_11f23eea/pitch_smoothed --compensate-camera --landmark-checks data/processed/clip_11f23eea/recalibration_check/return_checks.json --on-pitch-only --smooth-pitch
```

Hoàn thành 1.800 frame / 3 chunk, CUDA device 0, 6,92 FPS. Guard không đổi:
1.499 ngoài hiệu chỉnh / 30 chờ / 271 cấp phép. Đối chiếu đủ 5.215 điểm thô
với bản trước: khóa/nhãn/tọa độ không đổi; 4.935 tọa độ lọc và toàn bộ state
metrics khớp replay. Diagnostic có đúng một dòng cho mỗi điểm thô và đúng
4.935 `accepted` tương ứng từng khóa đầu ra.

Tọa độ lọc từ frame 1086 đến 1350, có 27 ID và A/B/referee/unknown =
2176/2187/139/433. Số nhãn CLI vẫn 2220/2232/139/624 theo bbox thô, không
lấy hai tổng này thay cho nhau. Tổng heatmap/samples bằng 4.935. Tốc độ
metrics lưu đều trong giới hạn; ngưỡng 0,5 giây không loại thêm bước nào,
không có nghĩa các sai số từng frame đã hết.

Ví dụ ID 1: trước lọc quãng đường quan sát 7,251 m / 4,0 giây có cặp đo;
sau lọc 5,685 m / 3,5 giây. ID 6: 2,497 -> 2,459 m, đều 4,0 giây. Đây là
phần quan sát được cộng, không so sánh như hai tổng có cùng coverage hoặc
khẳng định số thấp hơn đúng hơn. Khi ngắt chuỗi, phần đuôi chưa đủ 0,5 giây
cũng không được cộng, do đó có thể thiếu quãng đường đáng kể.

Giải mã lại nguồn/video đầu ra đều đủ 1.800 frame; video cửa sổ 271 frame,
1280 × 720 / 60 FPS. Schema, hữu hạn/phạm vi, thời gian, khóa, tổng samples/
heatmap và đối chiếu nhãn CLI với dữ liệu thô đều qua. Hợp đồng không đổi.

Artifacts cuối `data/processed/clip_11f23eea/pitch_smoothed/`: hai file tọa
độ, hai diagnostic camera/smoothing, metrics, validation, video cửa sổ và
bản đồ QA. Video đầy đủ `pitch_smoothed.mp4`, stdout `pitch_smoothed_run.json`
ở cạnh thư mục. Biểu đồ trước/sau ở `pitch_smoothing_check/coordinate_comparison.png`.
Helper `.tmp/validate_pitch_pipeline.py`, `.tmp/compare_pitch_pipeline.py`
chỉ dùng cục bộ. Giữ các bộ kết quả trước đó.

Nghiệm thu chức năng giảm nhiễu, giữ dữ liệu thô và ngắt mốc chuyển động.
Chưa nghiệm thu vị trí/tốc độ/quãng đường thực địa và chưa chuyển bước 5.
Cần đối chiếu tracking có tọa độ chuẩn độc lập, kiểm tra thêm chuyển hướng,
tăng tốc, đứng yên thật và camera/ID sai trước khi dùng làm số liệu báo cáo.
