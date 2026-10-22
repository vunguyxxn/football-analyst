# Tiến độ dự án

## Trạng thái hiện tại

Bước 0, Module B1, giao diện bước 1.5 và bước 1.6 đã triển khai, kiểm thử.
Backend nạp StatsBomb Open Data, chuẩn hóa sự kiện và cung cấp pass network;
frontend có shell điều hướng, sân SVG và trang phân tích trận. Chưa triển khai
xG, sơ đồ đội hình hoặc advisor.

Bước 2 đã triển khai và nghiệm thu chức năng CLI YOLO + ByteTrack xử lý video
từng đoạn trên clip thật `data/raw/vid1.mp4`, chạy được cả CPU và CUDA 12.8 trên
RTX 3050 6GB. Chưa đo độ chính xác tracking bằng dữ liệu gán nhãn.

Bước 3 đã có baseline K-means phân đội theo màu áo, nhãn trọng tài riêng và
`unknown`, tích hợp tùy chọn vào CLI. Đã chạy clip thật; kết quả trên clip cũ
là 24/28 mẫu đúng, 39 test qua ở phiên triển khai đầu. Nhãn do agent quan sát
ảnh, chưa được người gán nhãn độc lập rà soát. Trên clip cũ còn nhầm thủ môn
áo yếm vàng với trọng tài.

Nguồn `data/raw/vid1.mp4` hiện đã đổi sang clip mới SHA256 bắt đầu `11f23eea`,
51,28 giây, 720p/60 FPS. Đã hiệu chỉnh và chạy lại bước 2–3 trên bản cắt giây
10–40, thêm chế độ áo trắng/đen riêng theo fixture. Kiểm tra sơ bộ đúng 63/67
box, A/B 54/54; vẫn có staff bị gán nhầm. Các số liệu clip sân nhỏ ở trên thuộc
nguồn cũ `fa6ea680`, không dùng fixture cũ cho file mới cùng tên.

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

- Nhóm rà soát nhãn/box mẫu bước 3, nhất là áo thủ môn và người ngoài sân;
  mở rộng đánh giá sang clip khác trước khi dùng số liệu trong báo cáo.
- Bước 4 đã triển khai chức năng và kiểm thử bằng dữ liệu kiểm soát (chi tiết
  bên dưới). Cần clip camera cố định, chọn 4 điểm và kiểm tra mốc độc lập để
  nghiệm thu sai số thực tế; clip hiện tại vẫn lia máy, không dùng một
  homography cố định xuyên suốt 30 giây. Chưa chuyển sang bước 5.

## Vấn đề tồn đọng

- Chưa có xG, sơ đồ đội hình hoặc advisor; tracking CV mới ở baseline bước 2.
- Môi trường PyTorch/CUDA đã hoạt động. Tracking có thể mất/đổi ID khi che
  khuất, zoom hoặc chuyển cảnh; chưa đo IDF1 hay xác nhận định danh cầu thủ
  xuyên suốt clip.
- Bước 3 là baseline riêng theo clip; có nhầm áo yếm vàng thành trọng tài,
  nhãn màu có thể dao động, chưa phân đội thủ môn khác màu bằng ngữ cảnh.

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
- Ban đầu tải wheel CUDA 12.8 chậm nên tạm dùng CPU; sau đó người dùng đã tải
  xong, script xác minh SHA256 thành công. Kết quả GPU được ghi bên dưới.

## Nghiệm thu CUDA bước 2 — 22/10/2026

- Người dùng đã xem video CPU và xác nhận khung bám người.
- Kiểm tra lại SHA256 wheel PyTorch từ nguồn chính thức trước khi cài; cài
  `torch 2.8.0+cu128`, `torchvision 0.23.0+cu128` từ wheel cục bộ.
- `pip check`: không có dependency lỗi. `torch.cuda.is_available()` trả True,
  CUDA runtime 12.8, GPU NVIDIA GeForce RTX 3050 6GB Laptop GPU. Phép nhân ma
  trận CUDA chạy thành công.
- Chạy cùng YOLO11 nano, clip `vid1.mp4`, kích thước inference 640 và đoạn
  10 giây trên device 0: 867 frame, 2 đoạn, tốc độ xử lý toàn pipeline khoảng
  20,84 FPS. Lần chạy CPU trước khoảng 9 FPS; đây là số đo tham khảo một lượt
  cho mỗi thiết bị, gồm đọc, inference, tracking, vẽ và ghi video.
- Đầu ra `data/processed/vid1_tracked_gpu.mp4` đọc lại đủ 867 frame, đúng
  1920 × 1080 và 50 FPS; video không âm thanh. Đã xem ảnh mẫu frame 499–500:
  ID 90 và 230 giữ nguyên qua ranh giới đoạn.
- Thông số chạy tại `data/processed/vid1_tracking_gpu_run.json`, đối chiếu
  video tại `data/processed/vid1_tracking_gpu_validation.json`, ảnh mẫu tại
  `data/processed/vid1_gpu_frame_{0,499,500,866}.jpg`; không commit dữ liệu.
- Test toàn bộ sau khi cài CUDA: 30 passed, 1 network test deselected; còn
  cảnh báo deprecation Starlette TestClient đã có. Không thay đổi mã nguồn
  ứng dụng hay hợp đồng dữ liệu trong phiên nghiệm thu này.
- Hoàn tất nghiệm thu chức năng bước 2; bước tiếp theo là bước 3. Chưa tuyên
  bố độ chính xác detection/tracking hay định danh cầu thủ xuyên suốt clip.

## Triển khai baseline bước 3 — 22/10/2026

- Người dùng xác nhận: A áo tím/trắng, B áo xanh ngọc, trọng tài vàng chanh.
- Thêm `backend/cv/team_classifier.py`: trích màu Lab vùng thân áo, K-means
  hai cụm trên mẫu cầu thủ hiệu chỉnh, ánh xạ cụm sang A/B bằng nhãn hiệu chỉnh;
  mẫu màu trọng tài được xử lý riêng. Có ngưỡng trả `unknown`.
- Thêm `--team-samples` vào CLI bước 2; A/B/referee/unknown có màu và nhãn
  riêng. Trọng tài không gán A/B; `team_observations` là lượt quan sát qua
  frame, không phải số cầu thủ duy nhất. Mặc định không bật tùy chọn vẫn là
  pipeline bước 2. Không thêm dependency, không đổi API/hợp đồng dữ liệu.
- Khắc phục lỗi supervision 0.26.1 khi dùng custom color lookup với nhiều
  detection: dùng bản sao chỉ phục vụ vẽ với mã màu theo role; giữ nguyên
  class detection gốc. Test tích hợp kiểm tra nhiều người và dữ liệu gốc.
- Fixture `docs/fixtures/vid1_team_samples.json` có 101 box tham chiếu:
  15 hiệu chỉnh (frame 0, 50), 58 phát triển, 28 kiểm tra cuối ở các frame khác.
  Tên/SHA256 nguồn và frame split được kiểm tra, không fit bằng nhãn kiểm tra.
- Nhãn do Codex gán qua quan sát ảnh; người dùng xác nhận quy ước màu, chưa
  rà soát độc lập từng box. Hai proposal gần trùng đã loại trước đánh giá.
  Bộ phát triển dùng phát hiện/sửa lỗi bộ lọc cỏ loại nhầm áo huỳnh quang;
  kết quả kiểm tra cuối được đo trên frame khác sau sửa lỗi này.
- Kiểm tra cuối: đúng 24/28 (85,71%); phân đội 17/20 (85%, tính unknown là sai);
  trọng tài precision/recall 3/3, unknown đúng 4/5. Chỉ là phân loại màu trên
  box tham chiếu cùng một clip, không phải mAP/IDF1 hay độ chính xác nhiều trận.
- Tập phát triển còn 4/13 mẫu unknown bị nhầm trọng tài; ảnh mẫu frame 350
  cũng cho thấy thủ môn áo yếm vàng bị nhầm. Không tuyên bố đã giải quyết
  phân biệt thủ môn/trọng tài hoặc lọc mọi người ngoài sân.
- GPU chạy `vid1_teams.mp4`: đủ 867 frame qua 2 đoạn, giữ 1920 × 1080/50 FPS,
  tốc độ toàn pipeline khoảng 11,62 FPS trong lượt đo này. Đã xem frame 0,
  350, 500 và đọc lại toàn bộ video để đối chiếu metadata/số frame.
- Kết quả cục bộ: `data/processed/vid1_teams.mp4`, `vid1_team_run.json`,
  `vid1_teams_validation.json`, `vid1_team_final_evaluation.json` và ảnh mẫu
  `vid1_team_frame_*.jpg`; không commit media/dữ liệu sinh ra.
- Toàn bộ test cuối: 39 passed, 1 network test deselected; còn cảnh báo
  Starlette TestClient đã có. Hướng dẫn, confusion matrix và giới hạn tại
  `docs/CV_TEAMS.md`. Cần nhóm rà soát nhãn trước khi công bố số liệu.

## Kiểm tra clip mới cùng tên vid1.mp4 — 22/10/2026

- SHA256 nguồn mới: `11f23eead918e838cb39fdb1ef98179dc93f86574fdb6d38bb6cd8ced3e01ed1`.
  3077 frame, 1280 × 720, 60 FPS, 51,28 giây. Đã xem ảnh mẫu đầu/giữa/cuối:
  OBS che hình đầu/cuối, có lia camera. Góc rộng phù hợp thử tracking/phân đội;
  chưa đủ điều kiện coi camera cố định cho homography toàn clip.
- Tạo bản cắt từ frame nguồn 600 đến trước 2400 (giây 10–40), 1800 frame,
  giữ 720p/60 FPS, MP4V không âm thanh, tại
  `data/processed/clip_11f23eea/vid1_11f23eea_clean.mp4`.
  SHA256 bản cắt: `86f6f04ce05ac464269dfa4d831bef0c12c3654acdd2fa3c1b6379f864597b2e`.
  Không ghi đè nguồn hay kết quả cũ; metadata lineage tại `preparation.json`.
- Người dùng xác nhận A áo trắng, B áo sẫm/đen, trọng tài xanh nhạt. Tạo
  fixture mới `docs/fixtures/vid1_11f23eea_team_samples.json`, giữ fixture cũ
  và cơ chế kiểm tra hash để tránh dùng nhãn sai nguồn.
- Thêm feature_mode foreground cho áo trắng/đen, giữ pixel ít bão hòa và tối;
  tránh loại áo đen ám xanh cùng cỏ. Mặc định chromatic giữ hành vi clip cũ.
  Không thêm thư viện, không đổi API hoặc hợp đồng tọa độ.
- Bộ mẫu tham chiếu mới: 22 hiệu chỉnh (10 A, 10 B, 2 referee), 45 phát triển,
  67 kiểm tra ở frame khác. Nhãn do agent quan sát ảnh, quy ước màu đã được
  người dùng xác nhận, từng box chưa được rà soát độc lập. Không dùng nhãn
  kiểm tra để chỉnh mô hình/ngưỡng. Đây vẫn là đánh giá cùng clip có người lặp.
- Kiểm tra cuối: đúng chung 63/67 (94,03%), A/B 54/54, referee recall 4/4,
  precision 4/5. Unknown: đúng 5/9; ba mẫu bị gán B, một mẫu gán referee.
  Không suy ra độ chính xác toàn bộ detection/tracking hay nhiều trận.
- Chạy GPU image_size 1280, đoạn 10 giây: 1800 frame qua 3 đoạn, khoảng
  8,54 FPS toàn pipeline trong lượt đo này. Đầu ra
  `data/processed/clip_11f23eea/teams.mp4`; JSON chạy và đánh giá ở cùng thư mục.
- Đã đọc lại đủ 1800 frame của bản cắt và kết quả, đúng 1280 × 720/60 FPS;
  xem ảnh mẫu frame 0 và 1200. Đối chiếu tại `validation.json`, ảnh mẫu
  `teams_frame_*.jpg` trong cùng thư mục cục bộ.
- Test sau cập nhật: 41 passed, 1 network test deselected; cảnh báo Starlette
  TestClient đã có. Bổ sung test áo trắng/đen, áo đen ám xanh và truyền chế độ
  nhất quán qua hiệu chỉnh/đánh giá; chế độ chromatic vẫn được kiểm tra.
- Clip mới vẫn có người ngoài sân mặc áo gần màu đội; chưa bổ sung lọc sân
  hay homography trong phiên này. Hướng dẫn/ma trận nhầm lẫn ở `CV_TEAMS.md`.

## Triển khai chức năng bước 4 — 22/10/2026

- Thêm `backend/cv/homography.py`: công cụ OpenCV chọn tay 4 điểm gắn tọa
  độ mét đã biết, kiểm tra suy biến và ràng buộc sân 105 × 68; lưu SHA256,
  kích thước video, phạm vi frame. Đọc các đoạn hiệu chỉnh không chồng lấn.
- Thêm `--calibration` và `--pitch-output` vào CLI tracking. Chiếu giữa đáy
  bbox lên sân, ghi từng `TrackingRow` vào JSONL, bỏ ngoài sân/ngoài phạm vi
  hiệu chỉnh. Giữ schema và API hiện tại, không thêm dependency.
- Thêm `backend/cv/pitch_metrics.py`: thống kê theo từng ID/đoạn, lấy mẫu
  khoảng 0,5 giây, ngắt khi khoảng cách thời gian > 1 giây hoặc đổi đoạn.
  Bước nhảy > 40 km/h bị đếm lỗi và loại, không clamp tốc độ. Không nối
  thành danh tính cầu thủ hoặc tổng quãng đường cả trận.
- Xuất `metrics.json` chứa AnalysisResult, thống kê chất lượng và heatmap
  21 × 14 ô đếm frame quan sát; chưa triển khai giao diện bước 8. Heatmap
  là quan sát gốc, có thể chứa vị trí của bước chuyển động bị loại.
- Kiểm thử phối cảnh với điểm nội suy độc lập, đơn vị/trục sân, hash/range,
  suy biến, quãng đường biết trước, tốc độ, teleport, khoảng mất dấu, tách
  ID/đoạn và heatmap. Tích hợp codec + ByteTrack thật với detector giả lập.
- Hướng dẫn chọn điểm/lệnh chạy và giới hạn tại `docs/CV_HOMOGRAPHY.md`.
  Đã kiểm tra CLI `--help`. Chưa chạy giao diện click để hiệu chỉnh clip thật;
  cần người chọn mốc sân và kiểm tra sai số độc lập. Không bịa bộ 4 điểm
  hay số liệu tốc độ cho clip đang lia máy. Bước 4 mới nghiệm thu chức năng,
  chưa nghiệm thu độ chính xác thực địa.
- Toàn bộ kiểm thử: 54 passed, 1 network test deselected; còn cảnh báo
  Starlette TestClient đã có. Không thay đổi mã frontend.

## Quyết định đã chốt

- Python 3.11; FastAPI; Pydantic v2.
- Gốc tọa độ sân chuẩn ở góc trái dưới, đơn vị mét, sân 105 × 68.
- Không cài PyTorch trong requirements ở bước này; phần CV có file dependency riêng.
- Frontend dùng dark mode mặc định, nền xám than và màu nhấn xanh lá.
- Tailwind CSS: `4.3.3`; shadcn CLI/UI: `4.21.4` (khởi tạo thành công ngày 2026-10-08).
