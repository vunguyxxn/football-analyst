# Bước 4 — Hiệu chỉnh sân và chỉ số tracking

Đã có công cụ chọn tay 4 điểm và pipeline xuất tọa độ, quãng đường quan sát,
tốc độ, heatmap dạng JSON. Chưa nghiệm thu độ chính xác trên video thật:
`vid1.mp4` hiện tại có lia máy. Đã bổ sung tùy chọn bù chuyển động camera sau
hiệu chỉnh tay theo phạm vi được người dùng xác nhận ngày 22/10/2026.
Không dùng một ma trận cố định cho toàn clip đó.
Không thay đổi `TrackingRow`, `MetricItem`, `AnalysisResult` hay API hiện có.

## Chọn điểm

### Camera lia: chế độ mới

Dùng cùng công cụ chọn điểm trên **frame đầu mỗi đoạn hiệu chỉnh tay** rồi
thêm `--compensate-camera` khi chạy `backend.cv.track_video`. Không cần camera
cố định trong đoạn này. Bốn mốc phải nhìn thấy tại frame đầu, có tọa độ biết
trước, không nhất thiết nhìn thấy liên tục. Các lệnh `fixed.mp4` phía dưới
chỉ minh họa chế độ cũ; chế độ mới dùng video lia thực tế của nhóm.

Sau mỗi mốc tay, dùng đặc trưng Shi–Tomasi trên vùng cỏ thuộc sân đã hiệu
chỉnh, loại bbox person YOLO (gồm cả detection chưa có track ID, nới 12 px).
Optical flow Lucas–Kanade hai chiều loại cặp lệch > 1 px. Homography RANSAC
ước lượng phép biến đổi ảnh trước → ảnh sau; phép chiếu mới bằng phép chiếu
cũ nhân nghịch đảo biến đổi này. Không dùng chuyển động cầu thủ để suy ra
chuyển động camera. Mặt nạ màu cỏ là heuristic, vẫn có thể lọt người hoặc
overlay, và bỏ mất đặc trưng hữu ích trên vạch trắng.

Ngưỡng hiện tại: ít nhất 20 inlier, tỷ lệ >= 70%, diện tích bao điểm >= 3%
ảnh, sai số median <= 1,5 px; tỷ lệ diện tích ảnh sau biến đổi trong khoảng
0,8–1,25, góc ảnh dịch < 15% cạnh lớn nhất mỗi frame. Mỗi chuỗi tự động tối
đa 300 bước frame, sau đó yêu cầu mốc tay mới để hạn chế tích lũy trôi.
Đây là ngưỡng kỹ thuật baseline, chưa được hiệu chỉnh/đánh giá độc lập trên
nhiều trận, không phải độ tin cậy xác suất hay chứng nhận sai số theo mét.

Khi thiếu đặc trưng, cảnh cắt hoặc biến đổi không qua ngưỡng: trạng thái
`lost`, ngừng xuất tọa độ/chỉ số và **không tự khôi phục bằng ma trận cũ**.
Đến `start_frame` của segment tiếp theo mới dùng bộ 4 điểm tay mới. Không
nối quãng đường giữa hai segment. Trạng thái được vẽ trên video và ghi từng
frame ở `camera_quality.jsonl`: `manual_anchor`, `tracked`, `lost`, hoặc
`uncalibrated`. Kiểm tra frame đầu có trạng thái lost để chọn lại mốc từ
frame đó hoặc trước đó; kết hợp các đoạn đã chọn trong file calibration,
rồi chạy lại với đầu ra mới. Không cần sửa video gốc.

Mẫu lệnh sau khi đã tạo calibration đúng nguồn bản cắt hiện tại:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.track_video data/processed/clip_11f23eea/vid1_11f23eea_clean.mp4 data/processed/clip_11f23eea/moving_pitch.mp4 --weights data/raw/yolo11n.pt --device 0 --image-size 1280 --team-samples docs/fixtures/vid1_11f23eea_team_samples.json --calibration data/processed/clip_11f23eea/calibration.json --pitch-output data/processed/clip_11f23eea/moving_pitch --compensate-camera
```

`calibration.json` chưa có mốc thực địa đã xác minh; cần chọn tay, không tự
đoán tọa độ sân từ 4 điểm ảnh tùy ý. Test pan/zoom nhân tạo kiểm tra tính đúng
phép ghép và cơ chế mất dấu; chưa thay thế nghiệm thu sai số trên video thật.
Chuyển cảnh có thể qua lọt ngưỡng, tích lũy trôi và parallax vẫn có thể xảy
ra dù báo `tracked`. Cần đối chiếu mốc sân độc lập trong từng đoạn trước khi
dùng tốc độ/quãng đường cho báo cáo. Không tuyên bố hỗ trợ mọi góc quay/zoom.

### Camera cố định: chế độ cũ

Chọn 4 giao điểm vạch sân biết tọa độ mét, phân bố rộng, không có ba điểm
thẳng hàng. Không cần là bốn góc toàn sân, nhưng phải biết chính xác vị trí
tương ứng. Không đoán vị trí góc bị khuất. Hệ chuẩn: x từ 0 đến 105, y từ
0 đến 68, gốc trái dưới; không tự lật hướng tấn công giữa hai đội.

Ví dụ với video camera cố định mới `data/raw/fixed.mp4` có ít nhất 600 frame,
thấy đủ bốn góc sân (đây là ví dụ, không phải file sẵn có):

```powershell
.\.venv\Scripts\python.exe -m backend.cv.homography data/raw/fixed.mp4 data/processed/fixed_calibration.json --frame 0 --end-frame 600 --pitch-points '[[0,0],[105,0],[105,68],[0,68]]'
```

Cửa sổ hiện frame gốc, click theo đúng thứ tự tọa độ đã nhập. R chọn lại,
Enter lưu sau 4 điểm, Esc hủy. Điểm ảnh tính trên ảnh gốc, không resize.
Đổi danh sách `--pitch-points` nếu dùng giao điểm khác; phải tuân thủ kích
thước sân chuẩn. Nếu kích thước sân thực khác 105 × 68 thì tốc độ/quãng đường
ở đây là theo sân chuẩn hóa, chưa phải phép đo thực địa đã xác minh.

File hiệu chỉnh chứa SHA256 nguồn, kích thước ảnh và danh sách `segments`:
`start_frame` bao gồm, `end_frame` không bao gồm, bốn `image_points` và bốn
`pitch_points`. Có thể ghép các đoạn đã chọn riêng vào cùng danh sách, theo
thứ tự và không chồng lấn. Mỗi đoạn phải giữ camera cố định; ranh giới đoạn
xử lý 10 giây không tự động là ranh giới hiệu chỉnh hợp lệ. Khi camera đang
lia/zoom liên tục, chia mỗi 10 giây vẫn không giải quyết sai số; cần video
cố định hoặc hiệu chỉnh dày hơn đã kiểm chứng. Chưa có nội suy/ước lượng
chuyển động camera tự động trong chế độ cũ; bật `--compensate-camera` để dùng
baseline bù camera mô tả ở trên.

## Chạy pipeline

```powershell
$env:YOLO_CONFIG_DIR = "$PWD\data\processed"
$env:MPLCONFIGDIR = "$PWD\.tmp\matplotlib"
.\.venv\Scripts\python.exe -m backend.cv.track_video data/raw/fixed.mp4 data/processed/fixed_tracked.mp4 --weights data/raw/yolo11n.pt --device 0 --chunk-seconds 10 --calibration data/processed/fixed_calibration.json --pitch-output data/processed/fixed_pitch
```

Có thể thêm `--team-samples` tương ứng đúng video để có nhãn A/B/referee;
không có tùy chọn này thì `team=unknown`. Fixture clip khác sẽ bị từ chối
theo hash. Video và thư mục đầu ra phải mới, không ghi đè. Nếu chạy lỗi giữa
chừng, JSONL/video có thể dở dang; chỉ có `metrics.json` sau khi xử lý xong.

- `tracking.jsonl`: mỗi dòng là `TrackingRow` theo hợp đồng hiện có, dùng
  điểm giữa đáy bbox làm vị trí chân. Frame/thời gian tính theo nguồn đầu vào.
  Ngoài phạm vi hiệu chỉnh, ngoài sân, hoặc phép chiếu không hữu hạn thì bỏ
  quan sát; không ép người ngoài sân về đường biên. Phép chiếu trong sân
  không đảm bảo loại hết staff hay xác nhận vị trí chân chính xác.
- `metrics.json`: `analysis` theo `AnalysisResult`; thêm báo cáo nội bộ CLI
  `tracks` và metadata hiệu chỉnh. Các chỉ số có subject
  `segment:N/track:ID`; không gộp qua đoạn hoặc qua ID. Không phải danh tính
  cầu thủ và không phải tổng quãng đường cả trận. Chưa thêm endpoint/frontend.
- Heatmap: lưới 21 cột × 14 hàng, đếm lượt frame quan sát trong từng ô.
  `heatmap[0][0]` ở góc trái dưới. Không nội suy vùng mất dấu. Bao gồm cả mẫu
  đơn lẻ và tọa độ của bước nhảy bị loại khỏi chỉ số chuyển động, nên phải
  xem cùng `rejected_steps`; chưa phải heatmap đã làm sạch định danh.

## Cách tính và giới hạn

Giữ một điểm neo mỗi track/đoạn, đo sau ít nhất 0,5 giây để giảm nhiễu bbox
từng frame. Khoảng cách Euclid theo mét; tốc độ = khoảng cách / giây × 3,6.
Nếu khoảng từ neo đến mẫu mới > 1 giây thì ngắt chuỗi. Nếu tốc độ > 40 km/h
thì tăng `rejected_steps`, bỏ bước và ngắt chuỗi, không cắt tốc độ về 40.
Trung bình = tổng khoảng cách hợp lệ / tổng thời gian hợp lệ, gồm đứng yên.
`duration_s` là thời gian có cặp đo hợp lệ, không phải thời lượng xuất hiện.
Đoạn cuối ngắn hơn 0,5 giây không được cộng quãng đường. Không nối qua
khoảng hiệu chỉnh khác. Báo cáo không cộng thời gian/đường bị mất dấu.

Ngưỡng tốc độ không chứng minh hiệu chỉnh đúng: camera lia, đổi ID và nhiễu
có thể tạo tốc độ sai nhưng dưới 40. Mẫu chỉ có một điểm trả 0 cho chỉ số
chuyển động; xem `samples` và `duration_s` trước khi diễn giải. Quãng đường
lấy mẫu bỏ qua đường cong giữa hai mốc và có thể bị thiếu hoặc tăng bởi
nhiễu. Cần kiểm tra điểm mốc độc lập, cầu thủ đứng yên và đường di chuyển
biết trước trên clip camera cố định trước khi đưa số liệu vào báo cáo.

Đọc/ghi từng frame và từng dòng JSONL; chỉ giữ thống kê/lưới và một neo cho
mỗi ID/đoạn trong RAM, không giữ toàn bộ video hay toàn bộ tọa độ trong RAM.

## Kiểm tra

```powershell
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m backend.cv.homography --help
.\.venv\Scripts\python.exe -m backend.cv.track_video --help
```

Test kiểm tra phối cảnh bằng điểm trong sân độc lập với 4 điểm fit, đúng
chiều trục/đơn vị, suy biến, hash nguồn, khoảng frame, khoảng trống, ngắt
qua đoạn/ID, bước nhảy > 40 km/h, heatmap và đường đi biết trước 2 m/s.
Test tích hợp dùng codec + ByteTrack thật, detector giả lập, xuất JSONL qua
ranh giới đoạn xử lý, cả trường hợp có/không có người và phân đội.
Đây là nghiệm thu chức năng bằng dữ liệu kiểm soát, chưa đo sai số video thật.
