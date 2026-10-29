# Bước 8a — trang video và sân 2D mini đồng bộ

**Clip mẫu hiện tại (27/10/2026): `Video Project 15.mp4`.** Nút Mở clip
mẫu dùng manifest v2 và job `e0eb4128f58d45ea85c4ef0000ca92df`: video
52,3667 giây, 1.571 frame, 6 đoạn kết quả image-space. Kiểm hash video
với source của job trước khi ghép; không gắn tọa độ sân/offset của clip
cũ. Backend phải đang chạy để đọc kết quả mẫu đã xử lý.

Tái lập từ job còn trên máy (không chạy lại YOLO):

```powershell
.\.venv\Scripts\python.exe -m backend.cv.prepare_video_demo --job-id e0eb4128f58d45ea85c4ef0000ca92df --source 'data/raw/Video Project 15.mp4' --name 'Video Project 15.mp4'
```

Lệnh giữ asset cũ và sao lưu manifest trước khi chuyển mẫu. Clip này
chưa có tọa độ sân được nghiệm thu; sân mini của clip cũ không dùng lại.

**Cập nhật 27/10/2026:** đã bổ sung luồng tải video và chạy AI từ giao
diện. Xem `VIDEO_UPLOAD.md`. Mô tả bên dưới ghi lại bước 8a ban đầu;
nhận định "không upload" chỉ còn áp dụng cho việc mở tệp để xem trước,
trước khi người dùng bấm **Phân tích video**.

Ngày 26/10/2026. Đã thay trang chờ `/video` bằng trình phát video cục bộ
và sân mini. Dùng đúng các trường `TrackingRow` hiện có; không thêm API,
đổi DATA_CONTRACT, thư viện hoặc thuật toán CV. Hồ sơ cầu thủ/báo cáo HLV
trên frontend vẫn thuộc các bước sau.

## Sử dụng

Frontend chạy từ thư mục `frontend`:

```powershell
npm run dev -- --host 127.0.0.1 --port 5173
```

Mở `http://127.0.0.1:5173/video`, bấm **Mở clip mẫu**. Clip mẫu được chuẩn
bị sẵn trên máy ở phiên này; tự nhảy đến đoạn có tọa độ. Có thể phát,
tạm dừng, tua bằng thanh thời gian hoặc bàn phím, bật/tắt ID và quay lại
đầu đoạn tracking bằng **Tới đoạn có tọa độ**. Vạch xanh đánh dấu khoảng
video có dữ liệu vị trí. ID là mã tracking, không phải số áo hoặc danh
tính cầu thủ StatsBomb.

Với dữ liệu khác: chọn **Video trận đấu** trước, sau đó **Dữ liệu vị trí**
tương ứng. Đổi video sẽ bỏ tracking cũ để không ghép nhầm. Video mở bằng
object URL trong trình duyệt, tracking đọc trong bộ nhớ; không upload lên
backend hoặc dịch vụ bên ngoài. Trang xem video hoạt động không phụ
thuộc backend phân tích; badge health chung vẫn phản ánh kết nối backend.

Chấp nhận video mà trình duyệt giải mã được, ưu tiên H.264 MP4 hoặc WebM.
Video MP4V/FMP4 từ OpenCV có thể không phát được trong trình duyệt; có
thông báo khi lỗi phát. Không cài bộ chuyển mã hoặc thư viện mới ở bước này.

Tracking là JSONL (mỗi dòng một `TrackingRow`) hoặc JSON array, tối đa
20 MB/200.000 dòng. Kiểm tra kiểu số hữu hạn, frame/track ID nguyên không
âm, thời gian không âm, bốn nhãn đội đã chốt, x trong 0–105, y trong 0–68.
Từ chối file hỏng, trùng frame/ID, nhiều timestamp trong cùng frame hoặc
timestamp không tăng theo frame. Không tự cắt tọa độ lỗi về mép sân.

## Đồng bộ và đoạn thiếu

Trình duyệt hỗ trợ `requestVideoFrameCallback` dùng `mediaTime` của frame
đã hiển thị. Có fallback animation frame/timeupdate khi không hỗ trợ.
Tua video cập nhật vị trí khi seek xong; trong khi seek, sân mini để trống.
Tạm dừng và tua lùi không phụ thuộc lịch sử phát trước đó.

Binary search tìm frame tracking tại thời gian video. Chu kỳ frame được
ước lượng bằng median Δtime/Δframe, không dùng khoảng cách giữa hai frame
có dữ liệu như thời gian giữ điểm. Chỉ hiển thị trong một chu kỳ frame,
tối đa 0,1 giây; với file một frame dùng mặc định 1/30 giây. Không nội
suy, không giữ người qua đoạn mất dữ liệu hoặc chờ hiệu chỉnh. Một ID
biến mất ở frame kế tiếp cũng biến mất khỏi sân mini.

Tọa độ vẽ bằng `toSvg(x_m, y_m)` chung: x giữ nguyên, SVG y=68−y_m.
Không tự lật hướng tấn công video như StatsBomb. Không thêm speed/distance
hoặc coi tọa độ video là phép đo thực địa đã được nghiệm thu.

Mục **Căn chỉnh thời gian** định nghĩa:

```text
thời gian tracking = thời gian video − offset
```

Mở đúng đoạn đã xử lý thì offset 0. Mở video gốc trong khi tracking tạo
từ đoạn cắt bắt đầu giây 10 thì offset +10. File không có metadata nguồn
nên người mở vẫn cần chọn đúng cặp video/tracking; chỉ kiểm được thời
gian có nằm trong video, không xác minh danh tính video của mọi file nhập.
Offset không hợp lệ hoặc tracking nằm ngoài thời lượng video sẽ báo lỗi
và ẩn điểm, không im lặng hiển thị dữ liệu lệch.

## Clip mẫu tái lập

Từ gốc repo, trên máy đã có artifact bước 4:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.prepare_video_demo
```

Lệnh yêu cầu output mới, mặc định `frontend/public/video-demo/`. Không
ghi đè file, không chạy lại detector/tracker. Kiểm raw SHA256 theo
`video_review_plan.json`, tracking theo hash frozen đã kiểm toán trong
`vid1_11f23eea_prediction_samples.json`, cùng 4.735 khóa frame/ID duy nhất.
Chỉ sao chép video H.264 gốc và tracking v3; sinh manifest nội bộ cho demo.
Đây là asset frontend cục bộ, không phải endpoint/hợp đồng backend mới.

- Video gốc SHA256:
  `11f23eead918e838cb39fdb1ef98179dc93f86574fdb6d38bb6cd8ced3e01ed1`.
- Tracking SHA256:
  `ca80546ca739636eb5dc3a387752ed1efd160f8fd9d2b4a64c49948099e9dd77`.
- Offset +10 giây: đoạn clean bắt đầu sau 600 frame của video gốc 60 FPS.
- 4.735 bản ghi/265 frame, clean giây 18,1–22,5167, tương ứng video gốc
  28,1–32,5167. Frame đầu 1086 có 17 đối tượng được hiển thị.

Độ chính xác tọa độ vật lý vẫn theo giới hạn bước 4 ở
`VIDEO_REVIEW_EVALUATION.md`, không được nâng đánh giá nhờ làm giao diện.
Thư mục demo được ignore khỏi Git; nếu build sau khi chuẩn bị thì Vite
sao chép asset cục bộ vào dist theo cách xử lý public thông thường.

## Kiểm chứng phiên này

Từ `frontend`:

```powershell
npm run test
npm run build
npm run lint
```

- Bốn Node test không cần thư viện mới: JSONL/BOM/array, từ chối dữ liệu
  lỗi, frame/timestamp/ID, offset và khoảng trống, tua lùi và sai thời lượng.
- Parse dữ liệu thật: 4.735 dòng/265 frame, chu kỳ 1/60 giây; tại video
  giây 28,1 với offset 10 tìm đúng frame 1086/17 đối tượng; giây 20 rỗng.
- Nghiệm thu trình duyệt: clip mẫu giải mã được, phát tiến và cập nhật
  frame, cuối video xóa điểm, tua về đầu xóa điểm, nút tới tracking khôi
  phục 17 điểm; bật/tắt ID, offset 999 báo không giao video và xóa điểm,
  trả offset 10 khôi phục đồng bộ. Không có console error.
- Bố cục desktop 1280 px có hai cột; 375 px chuyển một cột, không tràn
  ngang. Đã trả viewport về mặc định sau kiểm tra.
- Ảnh giao diện: `data/processed/frontend_video_review_v1/desktop.jpg`.
- Build và lint exit 0; còn cảnh báo bundle >500 kB và Fast Refresh ở
  button UI. Không thay cấu hình để che cảnh báo hoặc thêm thư viện.

Backend từ gốc repo:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp .tmp/pytest_frontend_video_full_v1
```

**280 passed, 1 network deselected**, các cảnh báo Starlette/SHAP đã biết.
Phần tiếp theo là bước 8b hồ sơ cầu thủ và 8c báo cáo HLV, chưa triển khai
trong phiên này.
# Bổ sung demo nghiên cứu ngày 27/10/2026

Cập nhật29/10: artifact mẫu mở rộng hai đoạn30–40s và40–50s với kiểm
tra vạch sân theo lịch. Chọn ID phân biệt theo từng đoạn; sân có vị trí
tại45,1s, không giữ vị trí sau50s. Nhãn ước lượng/chưa kiểm chứng độc
lập vẫn giữ nguyên. Đồng hồ video được dung sai tối đa10 micro giây
để mốc tua bị làm tròn không làm trống frame đầu; không bắc cầu qua
khoảng thiếu tọa độ. Lịch sử bên dưới mô tả bản27/10.

Clip mẫu hiện là đúng Video Project 15.mp4 (52,3667 giây), manifest v2
khớp SHA256 của job hoàn tất. Mở mẫu nạp thêm vị trí sân nếu artifact
khớp nguồn, bắt đầu tại 30,1s. Chỉ đoạn 30–40s có hiệu chỉnh tay tạm;
không giữ vị trí khi tua ra ngoài. Đây chưa phải hiệu chỉnh đã nghiệm thu.

Bên dưới có heatmap theo nhóm áo/ID, quãng đường, tốc độ và thời gian
quan sát hợp lệ, luôn ghi rõ ước lượng và phạm vi. Hai thẻ ứng viên
chuyền tua về 7,5s/45,1s để xem tình huống; không đưa vào tổng chuyền
chính thức. Chưa có kết quả cú sút/gợi ý chiến thuật từ video đã kiểm chứng.
Thông tin frame và ID kỹ thuật được thu gọn. Không gắn dữ liệu mẫu này
vào clip tải mới. Xem VIDEO_FOOTBALL_RESEARCH.md để tái tạo nghiên cứu.
