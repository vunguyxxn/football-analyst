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
- Bước 4 đã triển khai chức năng và kiểm thử bằng dữ liệu kiểm soát. Người
  dùng đã cho phép mở rộng bù chuyển động camera sau hiệu chỉnh tay, không
  yêu cầu video camera cố định. Cần chọn mốc và đối chiếu sai số độc lập
  trên clip lia máy thực tế. Đã thử frame 600–900 bản cắt: bù lia chạy qua
  300 bước nhưng sai số 6 mốc hình học trung bình 1,20 m, lớn nhất 1,62 m
  trên nhãn bằng mắt/sân giả định; chưa đạt nghiệm thu chỉ số cầu thủ.
  Chi tiết tại `CV_HOMOGRAPHY_CHECK.md`. Chưa chuyển sang bước 5.
- Đã rà lại giao vạch và thêm lựa chọn mốc tay phụ cho hiệu chỉnh. Trên
  cùng frame mới 675/825, 8 mốc theo thời gian giảm trung bình 0,81 → 0,38 m;
  3 điểm hình học mới giảm 0,69 → 0,50 m. Biên xa có mẫu xấu hơn, kích thước
  sân chưa xác minh; chưa nghiệm thu chỉ số cầu thủ. Chi tiết tại
  `CV_HOMOGRAPHY_REFINEMENT.md`. Cần kiểm tra thêm đoạn lia/zoom khác.
- Đã kiểm tra thêm ba đoạn (905 frame): 900 bước tracked, 2 frame ngừng
  do hết chuỗi; stress test ảnh đen khóa tọa độ đúng tới mốc tay mới.
  Sai số mốc theo đoạn trung bình 0,64 / 1,36 / 0,50 m, max tới 3,28 m dù
  tracked; chưa chạy toàn clip để nghiệm thu chỉ số. Chi tiết tại
  `CV_HOMOGRAPHY_MULTI_CHECK.md`. Người dùng chốt tiếp tục dùng 105 × 68 m.
- Đã thêm `--landmark-checks`: mốc tay có thời hạn, chặn tọa độ trước kiểm
  chứng, khi lệch mốc hoặc hết hạn. Replay 905 frame chặn cả ba đoạn ở
  checkpoint đầu (lỗi 2,91 / 3,15 / 1,56 m); không xuất tọa độ nào. Chưa sửa
  sai số hoặc tự tìm mốc sân. Chi tiết tại `CV_LANDMARK_GUARD.md`.
- Hiệu chỉnh lại: đoạn cuối (mốc 1050) sửa biên xa lệch khoảng 4 px, trên
  hai frame mới lỗi trung bình 0,54 → 0,16 m, max mới 0,52 m; guard cấp phép
  frame 1080–1350. Hai đoạn đầu vẫn chưa đạt, có hồi quy và lỗi >1 m giữa
  checkpoint. Chỉ đề xuất thử tích hợp trên đoạn cuối, chưa nghiệm thu toàn
  clip. Chi tiết tại `CV_RECALIBRATION.md`.

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

## Bổ sung bù chuyển động camera bước 4 — 22/10/2026

- Người dùng xác nhận thay đổi phạm vi: hỗ trợ camera lia sau hiệu chỉnh tay.
  Cập nhật ROADMAP: vẫn không tự tìm mốc/khởi tạo homography hoàn toàn tự động.
- Thêm `backend/cv/camera_motion.py`, tùy chọn CLI `--compensate-camera`.
  Theo dõi đặc trưng mặt sân bằng optical flow hai chiều, loại bbox person
  trước ByteTrack, fit homography RANSAC và cập nhật phép chiếu từng frame.
- Kiểm tra số/tỷ lệ inlier, phân bố không gian, sai số, mức thay đổi hình học;
  chuỗi tối đa 300 bước frame giữa hai mốc tay. Đây là ngưỡng heuristic,
  không đảm bảo phát hiện mọi chuyển cảnh hoặc sai lệch tích lũy.
- Khi mất chất lượng, dừng xuất tọa độ tới segment hiệu chỉnh tay tiếp theo;
  không tự nối bằng ma trận cũ. Video vẫn ghi đủ, hiển thị trạng thái; thêm
  `camera_quality.jsonl` để tìm frame cần hiệu chỉnh lại. Giữ TrackingRow/API,
  không thêm dependency; vẫn xử lý từng frame, giữ hai ảnh xám thay vì cả clip.
- Test pan/zoom tổng hợp đối chiếu điểm mặt sân đứng yên; mặt nạ người/sân,
  mất đặc trưng/chuyển sang ảnh đen, khóa trạng thái mất dấu, mốc mới phục hồi,
  hết chuỗi 300 bước. Test tích hợp kiểm tra video ghi đủ và tọa độ ngừng khi
  mất hiệu chỉnh. Toàn bộ: 64 passed, 1 network test deselected; còn cảnh báo
  Starlette TestClient đã có.
- Chưa có hiệu chỉnh tay/mốc kiểm tra độc lập cho clip thật: chưa công bố
  sai số mét, tốc độ hoặc quãng đường cho clip đang lia. Bước tiếp theo là
  chọn các mốc tay cho bản cắt hiện tại, chạy chế độ mới, xem quality và
  kiểm tra vị trí mốc sân ở nhiều frame để đánh giá trôi. Không yêu cầu đổi
  sang camera cố định. Hướng dẫn cập nhật tại `docs/CV_HOMOGRAPHY.md`.

## Kiểm tra thực tế bù camera — 22/10/2026

- Kiểm tra bản cắt nguồn hash `86f6f04c`, frame 600–900 (giây 20–25 của
  video gốc). Chọn 4 mốc tại frame 600 bằng quan sát ảnh; fixture tại
  `docs/fixtures/vid1_11f23eea_homography_check.json`. Nhãn sơ bộ do agent,
  chưa có rà soát độc lập; giả định sân 105 × 68 m chưa được xác minh.
- Chạy YOLO thật CUDA và CameraMotion nguyên trạng: 1 mốc tay + 300 bước
  tracked, không lost trong đoạn thử. Diagnostic đọc lại đủ 301 frame.
  Chỉ khảo sát camera/mốc sân, không tính chỉ số chuyển động cầu thủ.
- 6 điểm vòng tròn không dùng fit: sai số trung bình 1,20 m, max 1,62 m.
  4 điểm duy trì giao đường biên: trung bình 0,54 m, max 1,02 m. Ngay frame
  đầu đã có lỗi khoảng 1 m, nên chưa thể quy toàn bộ sai số cho bù camera.
- Không thay đổi mã thuật toán hay nới ngưỡng. Giữ kết luận chưa nghiệm thu
  tốc độ/quãng đường; cần rà soát hiệu chỉnh và kiểm tra mới trước toàn clip.
  Báo cáo/phương pháp/lệnh tại `docs/CV_HOMOGRAPHY_CHECK.md`; media và JSON
  kết quả ở `data/processed/clip_11f23eea/homography_check_600/`, không commit.
- Kiểm tra fixture khớp hash/kích thước/range bằng loader hiện có. Test hồi
  quy toàn bộ 64 passed, 1 network test deselected; cảnh báo Starlette cũ.

## Rà soát hiệu chỉnh đầu bước 4 — 22/10/2026

- Người dùng không biết link/tên trận/sân. Giữ 105 × 68 m là giả định,
  không xác nhận kích thước thực hoặc tự đoán danh tính sân.
- Phóng lớn frame 600, fit các đoạn vạch được chọn tay để rà bốn giao điểm.
  Chỉ sửa bốn điểm chưa giảm rõ lỗi phát triển. Thêm hai mốc vòng tròn từ
  nhãn cũ làm dữ liệu hiệu chỉnh; nhãn cũ không còn là kiểm tra độc lập.
- `homography.py` giữ chế độ 4 điểm, bổ sung `--extra-pitch-points` cho ít
  nhất 2 mốc tay phụ. Fit sân → ảnh theo sai số pixel rồi nghịch đảo; kiểm
  tra trùng, phạm vi, suy biến, đường chân trời. Không đổi schema/API,
  dependency hoặc thuật toán/ngưỡng CameraMotion.
- Khóa hiệu chỉnh trước khi gán nhãn hai frame mới 675/825. Tính lại camera
  trên 301 frame nguồn với bbox YOLO cache cũ. 300 bước tracked, diagnostic
  đọc lại đủ 301 frame. Không đo throughput YOLO/GPU mới hoặc chỉ số cầu thủ.
- So sánh trên cùng điểm mới: 8 mốc theo thời gian 0,81 → 0,38 m trung bình,
  max mới 0,96 m; 3 mốc hình học mới 0,69 → 0,50 m, max mới 0,87 m. Hai mốc
  biên xa có sai số tăng; không công bố mọi vùng đã đạt độ chính xác cao.
- Fixture mới `docs/fixtures/vid1_11f23eea_homography_refined.json`, giữ bộ
  cũ; báo cáo `CV_HOMOGRAPHY_REFINEMENT.md`. Artifact cục bộ ở thư mục
  `data/processed/clip_11f23eea/homography_refined_600/`, không commit media.
- Toàn bộ 73 test qua, 1 network test deselected, cảnh báo Starlette cũ.
  Tiếp tục kiểm tra đoạn lia/zoom khác, mất dấu, mốc/định danh cầu thủ;
  chưa chuyển bước 5 và chưa nghiệm thu tốc độ/quãng đường thực địa.

## Kiểm tra thêm các đoạn lia bước 4 — 22/10/2026

- Người dùng chốt sân mặc định 105 × 68 m; tiếp tục phát triển theo hệ này.
- Chọn/khóa hiệu chỉnh tại frame 0, 450, 1050, mỗi đoạn có 4 mốc chính +
  2 mốc vòng tròn. Nhãn do agent quan sát, chưa rà soát độc lập. Giữ bộ cũ.
  Frame đánh giá 75/225, 525/710, 1125/1275 không tham gia fit.
- Chạy YOLO11n CUDA thật và CameraMotion không đổi, 905 frame ở ba đoạn,
  không chạy ByteTrack/phân đội hoặc chỉ số cầu thủ. Diagnostic giải mã đủ.
- 24 mốc theo thời gian: sai số trung bình theo đoạn 0,64 / 1,36 / 0,50 m,
  max 2,91 / 3,28 / 1,79 m. 3 điểm hình học mới ở đoạn giữa trung bình
  0,91 m, max 1,07 m. Không coi tracked là tọa độ đúng theo mét.
- Hết chuỗi frame 301–302 trả lost, không xuất tọa độ dù còn detection.
  Chèn ảnh đen trong bộ nhớ: lost, không tự phục hồi khi ảnh sân quay lại,
  mốc tay mới phục hồi. Không tuyên bố đã đo cắt cảnh tự nhiên/zoom mạnh.
- Fixture mới `docs/fixtures/vid1_11f23eea_homography_segments.json`, báo cáo
  `CV_HOMOGRAPHY_MULTI_CHECK.md`, artifact tại thư mục cục bộ
  `data/processed/clip_11f23eea/homography_multi_check/`. Không đổi mã thuật
  toán/ngưỡng/hợp đồng. Chưa chạy toàn clip hoặc chuyển bước 5.
- Kiểm tra fixture, stress assertions, giải mã ba video; toàn bộ 73 test
  qua, 1 network test deselected, cảnh báo Starlette cũ. Cần xử lý sai số
  hiệu chỉnh/trôi tuyệt đối trước nghiệm thu quãng đường/tốc độ.

## Kiểm tra độ trôi bằng checkpoint tay — 22/10/2026

- Thêm `backend/cv/landmark_guard.py`, tích hợp tùy chọn `--landmark-checks`
  vào PitchCalibration/CLI. File kiểm chứng tách khỏi hiệu chỉnh; kiểm tra
  nguồn, kích thước, phạm vi, cặp mốc; không fit lại từ nhãn kiểm chứng.
- Trước lần xác minh đầu không xuất tọa độ. Vượt ngưỡng sai số lớn nhất,
  projection không hữu hạn hoặc quá hạn thì lost, xóa ma trận và khóa tới
  mốc tay mới; mốc mới tiếp tục chờ xác minh. Mặc định 1 m / 30 frame.
- Replay ba đoạn 905 frame, dùng ngưỡng 1 m / 90 frame, optical flow tính
  lại bằng bbox YOLO cache cũ. Các nhãn khảo sát cũ đã chuyển thành runtime
  checkpoints, không còn là tập kiểm tra độc lập. Lỗi đầu 2,91 / 3,15 /
  1,56 m đều bị chặn; 225 frame chờ, 680 lost, 0 tọa độ được xuất. Đủ 905
  frame video diagnostic. Chưa sửa sai số hoặc tự nhận diện mốc/vạch sân.
- Fixture `docs/fixtures/vid1_11f23eea_landmark_checks.json`, hướng dẫn và
  giới hạn tại `CV_LANDMARK_GUARD.md`. Artifact tại thư mục cục bộ
  `data/processed/clip_11f23eea/landmark_guard_check/`, không commit media.
- Toàn bộ 99 test qua, 1 network test deselected; cảnh báo Starlette cũ.
  Test tích hợp chỉ cho phép output trong cửa sổ kiểm chứng hợp lệ; mặc
  định không bật guard vẫn hồi quy qua. Không đổi hợp đồng/API/dependency.
- Tiếp tục cải thiện hiệu chỉnh các đoạn bị chặn, chọn bộ đánh giá mới;
  chưa nghiệm thu tốc độ/quãng đường và chưa chuyển bước 5.

## Hiệu chỉnh lại các đoạn bị guard chặn — 22/10/2026

- Giữ ngưỡng guard 1 m / 90 frame, không nới ngưỡng. Phóng lớn và fit vạch
  từ ảnh để rà mốc biên; tại 1050 sửa y biên xa từ 207 lên khoảng 211,36 px.
  Thử mốc tay mới tại 75/525 cho hai đoạn đầu, khóa cấu hình trước nhãn mới.
- Thử tham chiếu trực tiếp mốc gốc bằng feature/LK/ORB trong helper nghiên
  cứu, chưa đưa vào ứng dụng do mất điểm/coverage hoặc không cải thiện đều.
  Không đổi CameraMotion, guard, hợp đồng, dependency hay mã ứng dụng.
- Frame mới 120/255, 555/690, 1110/1260 tách runtime checkpoints. Cùng mốc
  mới, lỗi trung bình cũ → mới: đầu 0,30 → 0,71 m (hồi quy), giữa 1,12 →
  0,61 m nhưng 4 điểm cung vùng cấm 0,51 → 0,82 m (xấu hơn), cuối 0,54 →
  0,16 m, max cuối 0,52 m. Hai ứng viên đầu không chấp nhận; cuối sơ bộ.
- Replay 755 frame với bbox cache: 70 chờ, 406 cấp phép, 279 lost; đọc lại
  đủ 755 frame. Cửa sổ cuối 1080–1350 có 271 frame cấp phép, không lost.
  Trong cửa sổ đầu/giữa vẫn có mốc đánh giá >1 m giữa checkpoint; không coi
  trạng thái cấp phép là mọi frame chính xác. Chưa chạy chỉ số cầu thủ.
- Hai fixture mới `vid1_11f23eea_recalibrated*.json` trong `docs/fixtures/`,
  báo cáo `CV_RECALIBRATION.md`, artifact cục bộ `recalibration_check/`.
  Đã tạo/kiểm tra cấu hình chỉ đoạn cuối để thử tích hợp tiếp theo. Giữ các
  bộ cũ. Toàn bộ 99 test qua, 1 network test deselected, cảnh báo Starlette cũ.
- Việc tiếp theo: tích hợp tracking/phân đội/tọa độ/heatmap trên phạm vi
  đoạn cuối, kiểm tra ID/điểm chân/noise; chưa nghiệm thu tốc độ/quãng đường,
  chưa chuyển bước 5 hoặc tuyên bố toàn clip đạt.

## Tích hợp tracking/phân đội/tọa độ đoạn cuối — 22/10/2026

- Chạy CLI YOLO11n CUDA + ByteTrack + phân đội + CameraMotion/guard trên
  bản cắt 1.800 frame, image size 1280, chunk 10 giây. Hoàn thành 3 chunk,
  trung bình 6,08 FPS. Không đổi mã ứng dụng, dependency hoặc hợp đồng.
- Giữ guard 1 m / 90 frame và cấu hình chỉ đoạn cuối. 1.499 frame ngoài
  hiệu chỉnh, 30 chờ, 271 cấp phép (1080–1350). Xuất 5.384 TrackingRow,
  không có tọa độ ngoài cửa sổ; A/B/referee/unknown = 2489/2452/334/109.
- Kiểm tra schema, hữu hạn/phạm vi/thời gian, không trùng frame+ID, tổng
  samples/heatmap; giải mã nguồn/đầu ra đủ 1.800 frame và video cửa sổ đủ
  271 frame. Tạo bản đồ vị trí/heatmap QA cục bộ, backend vẫn JSON.
- Chưa đạt chất lượng thống kê cầu thủ: 50 ID trong cửa sổ, 17 track có
  ít nhất 120 mẫu; 19 track đổi vai trò (104 lần). Thấy bbox/ID gần trùng
  cho cùng vùng người (134/306 ở 1200, 134/330 ở 1310), dễ đếm thừa.
- 793/5310 cặp frame liên tiếp suy ra >40 km/h, là diagnostic rung/gán
  điểm, không phải tốc độ thực. Metrics lấy mẫu 0,5 giây chỉ loại 1 bước;
  tốc độ lưu <=40 không chứng minh độ chính xác quãng đường/tốc độ.
- Báo cáo `CV_INTEGRATION_CHECK.md`, artifact cục bộ `return_integrated/`
  cùng video `return_integrated.mp4` dưới `data/processed/clip_11f23eea/`.
  Đã rà mẫu hình ảnh đầu/giữa/cuối và bước nhảy lớn. Không có nhãn IDF1
  hoặc ground truth bàn chân. Toàn bộ 99 test qua, 1 network deselected,
  cảnh báo Starlette cũ. Chưa nghiệm thu toàn clip, chưa chuyển bước 5.
- Việc tiếp theo: xử lý detection/track trùng và gãy ID trên đoạn gán nhãn,
  rồi ổn định vai trò/điểm chiếu, đánh giá lại chỉ số trước khi mở rộng.

## Chỉ theo dõi người trong đường biên — 22/10/2026

- Theo yêu cầu người dùng, thêm CLI `--on-pitch-only`, bắt buộc hiệu chỉnh
  sân. Dùng điểm giữa cạnh dưới bbox chiếu vào sân 105 × 68 m, lọc trước
  ByteTrack, phân đội và vẽ khung. Người ngoài sân không có quan sát/nhãn/
  heatmap; không có hiệu chỉnh hợp lệ thì không vẽ khung người. Lệnh cũ
  không bật cờ vẫn tương thích. Không đổi schema/API/dependency.
- Tách `PitchCalibration.locate` để lọc và xuất tọa độ dùng chung phép chiếu.
  CameraMotion vẫn nhận đủ bbox gốc để loại người khỏi phép đo camera.
  Biên theo homography đang kiểm chứng, không phải phân đoạn vạch trắng tự
  động; sát biên còn phụ thuộc sai số bbox/hiệu chỉnh, chưa nhận diện bàn chân.
- Chạy lại CUDA đủ 1.800 frame / 3 chunk, 7,01 FPS, giữ guard 1 m / 90 frame.
  1.499 ngoài hiệu chỉnh, 30 chờ, 271 cấp phép; 5.365 tọa độ ở 1081–1350,
  frame 1080 chờ xác nhận track. Nhãn A/B/ref/unknown = 2480/2443/333/109;
  tổng nhãn CLI bằng tổng tọa độ, không còn cộng người ngoài sân.
- Đã xem frame 1200/1350: người khu kỹ thuật ngoài biên gần không còn khung;
  frame 1351 ngoài phạm vi không có khung người. Đọc lại đủ nguồn/video
  đầu ra 1.800 frame và video cửa sổ 271 frame; kiểm tra schema, phạm vi,
  thời gian, khóa, heatmap/samples và tổng nhãn qua.
- Artifacts cục bộ `data/processed/clip_11f23eea/on_pitch_only/`, video đầy
  đủ `on_pitch_only.mp4` cạnh thư mục; giữ kết quả cũ. Hướng dẫn cập nhật
  `CV_TRACKING.md`, nghiệm thu bổ sung trong `CV_INTEGRATION_CHECK.md`.
- Test mới kiểm tra lọc trước tracking/phân đội/vẽ, thân chồng sân nhưng
  chân ngoài, chờ/hết hạn checkpoint và hết hiệu chỉnh; toàn bộ 102 test
  qua, 1 network deselected, cảnh báo Starlette cũ. Vẫn có 50 ID; chưa sửa
  ID trùng/nhãn rung, chưa nghiệm thu chỉ số cầu thủ hoặc chuyển bước 5.

## Lọc khung trùng và kiểm tra ID — 22/10/2026

- Người dùng yêu cầu xử lý khung/ID trùng. Xác định YOLO trả cặp bbox cùng
  cầu thủ tại frame 1200, IoU ~0,602, confidence 0,5545/0,2622. Thêm NMS
  IoU 0,5 bằng supervision trước ByteTrack, phân đội, JSON và vẽ. Không
  gộp ID hậu kỳ hoặc theo khoảng cách; giữ bộ lọc trong sân và bbox thô
  cho camera. Không đổi ByteTrack/guard/schema/API/dependency.
- Cache YOLO thật 271 frame, replay cùng detection trước/sau: 5365 -> 5215
  quan sát, 50 -> 30 ID, 17 -> 5 track dưới 30 mẫu, 134 -> 0 cặp IoU >0,5.
  Số cặp bằng 0 là thuộc tính NMS, chưa chứng minh mọi người được giữ đúng.
- Fixture `vid1_11f23eea_id_samples.json`: 49 quan sát thưa của 7 người do
  agent vẽ từ ảnh nguồn, chưa rà soát độc lập. Ngưỡng khóa trước nhãn;
  48/49 ghép được cả trước/sau, mẫu ghép nhiều ID 2 -> 0, đổi ID giữa ảnh
  mẫu 10 -> 2. Sáu người ổn định, white_runner còn đổi 2 lần; không IDF1.
- Chạy pipeline CUDA đầy đủ 1.800 frame/3 chunk, 7,66 FPS. Guard không đổi:
  1499 ngoài hiệu chỉnh/30 chờ/271 cấp phép. Xuất 5215 dòng ở 1081–1350,
  A/B/ref/unknown 2450/2354/312/99, 30 ID, 19 track ít nhất 120 mẫu.
  Từng khóa/tọa độ baseline và sau sửa khớp replay (sai khác số học ~3e-14 m).
- Giải mã đủ nguồn/đầu ra 1800 và cửa sổ 271 frame; kiểm tra schema, khóa,
  phạm vi, thời gian, heatmap và tổng nhãn đều qua. Xem 1200/1300/1310:
  cầu thủ áo đen giữa sân giữ ID 13, không còn khung đôi từng thấy; người
  ngoài sân vẫn được lọc. Vẫn rung vai trò/tọa độ, chưa nghiệm thu chỉ số.
- Test mới có cặp bbox thật, ByteTrack thật, mất detection 5 frame, người
  gần nhau/che một phần và đầu vào rỗng. Toàn bộ 105 test qua, 1 network
  deselected, cảnh báo Starlette cũ. Không tăng minimum_consecutive_frames
  vì thử nghiệm không cải thiện đổi ID mẫu, tránh mất thêm quan sát.
- Báo cáo `CV_TRACKING_ID_CHECK.md`; cache ở `id_check/`, kết quả mới tại
  `id_deduplicated/` và video cùng tên dưới `data/processed/clip_11f23eea/`.
  Giữ bộ cũ. Chưa bảo đảm mọi che khuất/cắt cảnh, chưa chuyển bước 5; tiếp
  theo ổn định vai trò/điểm chiếu và mở rộng bộ nhãn trước đánh giá chỉ số.

## Quyết định đã chốt

- Python 3.11; FastAPI; Pydantic v2.
- Gốc tọa độ sân chuẩn ở góc trái dưới, đơn vị mét, sân 105 × 68.
- Người dùng xác nhận tiếp tục dùng 105 × 68 m làm kích thước sân mặc định
  cho bước 4, không chờ xác minh danh tính sân trong clip.
- Không cài PyTorch trong requirements ở bước này; phần CV có file dependency riêng.
- Frontend dùng dark mode mặc định, nền xám than và màu nhấn xanh lá.
- Tailwind CSS: `4.3.3`; shadcn CLI/UI: `4.21.4` (khởi tạo thành công ngày 2026-10-08).
