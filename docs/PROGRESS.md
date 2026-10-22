# Tiến độ dự án

## Trạng thái hiện tại

Bước 0, Module B1, giao diện bước 1.5 và bước 1.6 đã triển khai, kiểm thử.
Backend nạp StatsBomb Open Data, chuẩn hóa sự kiện và cung cấp pass network;
frontend có shell điều hướng, sân SVG và trang phân tích trận. Chưa triển khai
xG, sơ đồ đội hình hoặc advisor.

Bước 2 đã có CLI YOLO + ByteTrack xử lý video từng đoạn, chạy được trên clip
thật `data/raw/vid1.mp4` bằng CPU. Chưa hoàn tất nghiệm thu bước 2 trên CUDA.

## Đã làm

- Chốt cấu trúc backend FastAPI và frontend Vite + React + TypeScript.
- Chốt hợp đồng dữ liệu và hệ tọa độ sân chuẩn trong `DATA_CONTRACT.md`.
- Khởi tạo Git, `.gitignore` và môi trường ảo Python 3.11.
- Tạo API health check, schema Pydantic, phép chuyển tọa độ và 11 bài kiểm thử.
- Tạo frontend Vite + React + TypeScript; tích hợp Tailwind CSS, shadcn/ui,
  TanStack Query, Recharts, Framer Motion và lucide-react.
- Hoàn tất dark mode mặc định, màu nền xám than, nhấn xanh lá, và proxy `/api`.
- Xác minh endpoint `/api/health` trả `{"status":"ok"}`, frontend hiển thị
  `Backend: OK`, 11 test pass và build frontend thành công.
- Module B1: loader StatsBomb dùng cache CSV trong
  `data/processed/events_{match_id}.csv` do môi trường không có pyarrow; bổ sung
  pass network và các endpoint competitions, matches, pass-network.
- Nghiệm thu trận World Cup 2018 Brazil–Bỉ (match ID `8650`): 3.589 sự kiện;
  tọa độ x nằm trong `[0.875, 105]`, y trong `[0, 67.15]`.
- `pytest -v`: 20 passed, 1 network test deselected. `pytest -v -m network`:
  1 passed, 20 deselected.
- Smoke test 3 API endpoint thành công; match ID không tồn tại trả HTTP 404.
- Bước 1.5: thêm React Router, shell dark mode, các trang trạng thái "Sắp có",
  component sân SVG theo hệ mét và trang Phân tích trận lấy dữ liệu thật từ API.
- Hợp đồng dữ liệu bổ sung hướng tấn công chuẩn hóa cho StatsBomb; tracking
  video không mặc định có hướng thống nhất.
- Nghiệm thu frontend: `npm run build` thành công; `npm run lint` thành công
  (còn một cảnh báo Fast Refresh có sẵn trong `components/ui/button.tsx`);
  `pytest -v`: 20 passed, 1 network test deselected.
- Kiểm tra giao diện trình duyệt ở 1440px và 768px, có dữ liệu thật Brazil–Bỉ;
  chiều rộng tài liệu không vượt viewport 768px. Đã xem trạng thái trống và
  trạng thái tải/lỗi khi backend tắt.
- Bước 1.6: loader giữ `player_nickname`; mỗi node pass network trả `short_name`
  duy nhất trong đội, ưu tiên nickname và phân biệt họ trùng nhau. Frontend dùng
  tên ngắn trên sân/bảng, giới hạn nhãn sân mặc định cho 6 cầu thủ chuyền nhiều
  nhất; tooltip vẫn hiển thị tên đầy đủ, số chuyền và số chạm.
- Kiểm thử bước 1.6: `pytest -v` — 21 passed, 1 network test deselected;
  `npm run build` thành công; `npm run lint` thành công (còn cảnh báo Fast
  Refresh đã có trong `components/ui/button.tsx`).
- Đã xác nhận dữ liệu thật cho Brazil (14 nút, 57 cạnh) và Bỉ (13 nút, 46 cạnh);
  ảnh nghiệm thu lưu tại `screenshots/pass-network-brazil.png` và
  `screenshots/pass-network-belgium.png`.

## Việc tiếp theo

- Hoàn tất cài PyTorch CUDA 12.8 và chạy lại bước 2 trên RTX 3050.
- Sau nghiệm thu bước 2, tiếp tục phân loại đội theo màu áo ở bước 3.

## Vấn đề tồn đọng

- Chưa có xG, sơ đồ đội hình hoặc advisor; tracking CV mới ở baseline bước 2.
- Không có lỗi tồn đọng trong phạm vi bước 0. Môi trường CV đang được cài ở
  bước 2; PyTorch CPU hoạt động, chưa xác nhận PyTorch/CUDA.

## Phiên triển khai bước 2 — 22/10/2026

- Kiểm tra GPU: NVIDIA RTX 3050 6GB, driver 581.86.
- Thêm `backend/cv/track_video.py`: YOLO phát hiện lớp person, supervision
  ByteTrack, ghi video MP4 có khung và ID, không âm thanh. Đọc/ghi từng frame
  trong đoạn, giữ tracker qua ranh giới đoạn; không giữ cả clip trong RAM.
- Không đổi API hay schema tọa độ; bước 2 chưa xuất tọa độ sân theo mét.
- Thêm hướng dẫn tại `docs/CV_TRACKING.md` và test kiểm tra đầu vào, bảo vệ
  file đầu ra, vòng đọc/ghi video và ID qua các đoạn.
- Test API cần chạy ngoài sandbox do Windows socketpair bị treo trong sandbox.
- Đã cài OpenCV, supervision 0.26.1, Ultralytics 8.3.221 và dependency.
- Test toàn bộ sau triển khai: 30 passed, 1 network test deselected; còn cảnh
  báo deprecation của Starlette TestClient. Nhóm test CV có 9 test, gồm trường
  hợp không có detection. Test video dùng codec và ByteTrack thật, detector
  được giả lập; chưa phải đo độ chính xác YOLO.
- Clip đầu vào `vid1.mp4`: 867 frame, 1920 × 1080, 50 FPS, 17,34 giây.
- Đã cài PyTorch 2.8.0+cpu và torchvision 0.23.0; `pip check` không có lỗi.
- Chạy YOLO11 nano + ByteTrack thật trên CPU: 867 frame, 2 đoạn (10 giây/đoạn),
  tốc độ xử lý khoảng 9 FPS. Video `data/processed/vid1_tracked_cpu.mp4` giữ
  đúng 867 frame, 1920 × 1080 và 50 FPS; không có âm thanh.
- Đã xem ảnh mẫu đầu clip và quanh ranh giới đoạn: ID 90, 230 không bị reset
  giữa frame 499 và 500. Clip có thay đổi góc/zoom; ID có thể thay đổi khi mất
  dấu, chưa đo IDF1 hay xác nhận định danh cầu thủ xuyên suốt clip. Baseline
  cũng có thể phát hiện trọng tài/người ngoài sân.
- Kết quả đối chiếu nằm ở `data/processed/vid1_tracking_validation.json` và
  ảnh `vid1_tracked_frame_{0,499,500,866}.jpg` (dữ liệu cục bộ, không commit).
- Tải wheel CUDA 12.8 từ nguồn chính thức quá chậm; đã tạm dừng và lưu tiến độ
  cục bộ tại `.tmp/torch-download.json`. Có thể tiếp tục bằng
  `.\.venv\Scripts\python.exe -B .tmp/download_torch.py` trong workspace này;
  script kiểm tra SHA256 chính thức khi tải xong. `.tmp` không được commit;
  checkout khác dùng hướng dẫn cài đặt trong `docs/CV_TRACKING.md`.
- Chưa xác nhận inference GPU, chưa đánh dấu hoàn tất bước 2.

## Quyết định đã chốt

- Python 3.11; FastAPI; Pydantic v2.
- Gốc tọa độ sân chuẩn ở góc trái dưới, đơn vị mét, sân 105 × 68.
- Không cài PyTorch trong requirements ở bước này; phần CV có file dependency riêng.
- Frontend dùng dark mode mặc định, nền xám than và màu nhấn xanh lá.
- Tailwind CSS: `4.3.3`; shadcn CLI/UI: `4.21.4` (khởi tạo thành công ngày 2026-10-08).
