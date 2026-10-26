# Tiến độ dự án

## Trạng thái hiện tại

Ngày 26/10/2026: bước 8b đã có trang `/players`, hai nguồn StatsBomb
(27 hồ sơ trận 8650) và Metrica (22 hồ sơ Game 1, giây 60–120). Có tìm
kiếm/lọc đội, vai trò và truy vết sự kiện, chỉ số chuyển động/bao phủ và
heatmap; không ghép danh tính giữa nguồn hoặc gọi dữ liệu một cửa sổ là
toàn trận. 8 test frontend qua, build/lint exit 0, 280 test Python qua.
Xem `FRONTEND_PLAYERS.md`. Tiếp theo bước 8c báo cáo HLV.

Ngày 26/10/2026: bước 8a đã có trang `/video`, video cục bộ và sân 2D
mini đồng bộ theo frame. Có clip mẫu một nút, đọc TrackingRow JSONL/JSON,
tua về đoạn có dữ liệu, ID/màu đội và căn chỉnh offset; không giữ tọa độ
qua khoảng thiếu hoặc seek. Không thêm API/schema/thư viện. Đã nghiệm
thu trình duyệt desktop/mobile; 4 test frontend qua, build/lint exit 0,
280 test Python qua. Chi tiết `FRONTEND_VIDEO.md`. Tiếp theo 8b/8c.

Ngày 23/10/2026: bước 7 đã có advisor ngoại tuyến cho rà soát cú sút:
xG + Tree SHAP và ba luật cố định, báo cáo JSON/Markdown tiếng Việt,
mỗi gợi ý truy tới event ID, chỉ số và đóng góp feature. Trận 8650 sinh
hai gợi ý, đã kiểm tra truy vết và SHAP khôi phục đúng dự đoán với 66 cây
tốt nhất. Chưa có HLV nghiệm thu hiệu quả khuyến nghị; không gọi luật
heuristic là mô hình học chiến thuật. 280 test qua. Xem
`ADVISOR_BASELINE.md`; chưa thêm API/giao diện hoặc đổi hợp đồng dữ liệu.

Ngày 23/10/2026: bước 6 đã có baseline xG ngoại tuyến bằng XGBoost,
huấn luyện trên World Cup 2018 + Euro 2020, giữ World Cup 2022 để test.
Test 64 trận/1.430 cú sút không penalty: AUC 0,7665, Brier 0,08467;
StatsBomb tham chiếu 0,8148 / 0,07619. Tốt hơn xác suất cố định nhưng
chưa bằng StatsBomb. Có model JSON, inference, calibration bins và
bootstrap theo trận; 273 test qua tại phiên bước 6. Xem `XG_BASELINE.md`.
Advisor đã có baseline ngoại tuyến; phần tiếp theo theo ROADMAP là bước 8.

Đã đối chiếu video sau bước 5b: cùng clip/cấu hình 1280/conf 0,1 và bộ
lọc trong sân. Fine-tuned ghép 150/154 thay 146/154, nhưng nhiều khung
chồng, 55 thay 2 dự đoán chưa ghép cần rà; đổi ID biểu kiến 6 thay 1 trên
87 khoảng chung. Giữ trọng số gốc làm mặc định. Nhãn agent/thưa, không
phải accuracy tracking độc lập; chi tiết `CV_FINETUNE_VIDEO.md`.
264 test qua; đã chốt so sánh 5b, bước tiếp theo theo ROADMAP là xG.

Ngày 23/10/2026, bước 5b đã hoàn tất một lượt fine-tune YOLO11n trên
372 ảnh bóng đá chia theo nhóm tên file/ảnh gần trùng. Trên 73 ảnh test
giữ riêng: mAP50 71,04% → 91,67%; mAP50–95 39,62% → 56,40%.
Đã lưu protocol, nguồn/hash, trọng số và kết quả trước/sau; 261 test qua.
Đây là đánh giá detection trên bộ ảnh công khai, chưa xác minh độc lập
theo trận hoặc chất lượng tracking video. Trọng số mới chưa thay mặc định.
Chi tiết `CV_FINETUNE_YOLO.md`; giới hạn bước 4–5 bên dưới vẫn áp dụng.

Cập nhật 23/10/2026: đã bắt đầu bước 5 với baseline hình dạng đội hình
ngoại tuyến trên Metrica, hồ sơ cầu thủ/báo cáo hai đội và tham chiếu
sơ đồ/lineup StatsBomb theo thời điểm; chức năng ngoại tuyến đã có,
chưa nghiệm thu chất lượng nhận diện chiến thuật. Đã có tùy chọn so khớp
mẫu và bộ đánh giá tái lập, vẫn giữ gap mặc định. Đã rà nháp 24 cửa sổ
Metrica; chưa có nhãn độc lập để nghiệm thu, xem `FORMATION_AGENT_REVIEW.md`.
Kiểm tra thêm 24 cửa sổ mới giây 120–180: không nhãn nào đủ đồng thuận
4/5 ảnh thời điểm; xem `FORMATION_TEMPORAL_CHECK.md`. Đây là chẩn đoán,
không phải bằng chứng accuracy hay thay đổi mặc định sản phẩm.
Đã thêm thử nghiệm `aligned` cho tuyến nghiêng/lệch cánh: 54/54 ca stress
giả lập và 1/24 cửa sổ có hỗ trợ thời gian, chưa đủ căn cứ đổi mặc định.
Chi tiết `FORMATION_ALIGNED.md`; chất lượng chiến thuật chưa nghiệm thu.
Đã bổ sung bộ đọc Metrica Game 3 và đối chiếu bố trí vai trò từ metadata
chính nguồn: aligned khớp 2, khác 1, từ chối 21 trên 24 cửa sổ. Metadata
vai trò không phải nhãn chiến thuật từng frame; xem `METRICA_GAME3_REFERENCE.md`.
Đã có thêm 27 hồ sơ sự kiện StatsBomb cùng lineup trận 8650, truy theo ID
và index sự kiện; xem `STATSBOMB_PLAYER_PROFILES.md`. Không ghép người khác
nguồn, không dùng thống kê sự kiện để nâng đánh giá chất lượng nhận diện.
Xem thêm `FORMATION_TEMPLATE_EVALUATION.md`,
`STEP5_PLAYER_PROFILES.md`, `FORMATION_BASELINE.md`,
`STATSBOMB_FORMATION_REFERENCE.md` và mục cuối trang. Bộ lọc tọa độ v3 giảm MAE tốc
độ với nhiễu độc lập và cải thiện hồi phục sau lỗi ngắn so v2.1. Với nhiễu
tương quan thời gian, sai số vẫn chưa cải thiện; cửa sổ dài hơn phản ứng
dừng/rẽ kém hơn. Chưa nghiệm thu số liệu thực địa từ video.
Chi tiết `METRICA_FILTER_V3.md` và mục cuối trang.

Người dùng đã giao agent tự đánh dấu. Đã hoàn tất bản nhãn nháp 20 ảnh,
411 điểm người và 46 mốc sân trong `human_review_v1/agent_review_v1`;
trang xem đã điền sẵn, người dùng không phải nhập lại. Đây là nhãn agent,
chưa có kết quả sai số video theo dữ liệu chuẩn độc lập. Chi tiết
`VIDEO_AGENT_REVIEW.md`; hướng dẫn nhập tay cũ ở `VIDEO_HUMAN_REVIEW.md`.

Đã đối chiếu tám ảnh return với dự đoán đã khóa: còn thiếu điểm và hai
trường hợp nghi đổi ID; độ lệch pixel trên cùng tập cặp trước/sau lọc gần
như bằng nhau. Chốt dùng video cho minh họa chức năng và cửa sổ tọa độ có
guard, chưa dùng số mét/km/h như phép đo thực địa. Đợt rà soát bước 4 này
đã kết thúc; đang dùng Metrica cho bước 5 theo phương án dự phòng.
Xem VIDEO_REVIEW_EVALUATION.md.

Bước 0, Module B1, giao diện bước 1.5 và bước 1.6 đã triển khai, kiểm thử.
Backend nạp StatsBomb Open Data, chuẩn hóa sự kiện và cung cấp pass network;
frontend có shell điều hướng, sân SVG và trang phân tích trận. xG đã có
baseline ngoại tuyến, advisor đã có bản rà soát cú sút; sơ đồ đội hình mới có
baseline ngoại tuyến, chưa lên giao diện.

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

## Ổn định nhãn đội/trọng tài theo ID — 22/10/2026

- Thêm TrackRoleSmoother sau classifier từng box: cửa sổ quá khứ 0,5 giây,
  tối thiểu 3 frame, ít nhất max(3, ceil(FPS*0,1)) phiếu và >=70%. Nhãn
  hiện tại phải đồng thuận, mâu thuẫn/thiếu bằng chứng trả unknown. Unknown
  làm giảm tỷ lệ, không bỏ phiếu đội. Không khóa nhãn ban đầu; xóa track
  vắng hết cửa sổ, kể cả frame trống; giữ lịch sử qua chunk, bộ nhớ giới hạn.
- Bật tự động khi track_video có team-samples; nhãn dùng chung cho vẽ,
  TrackingRow và tổng nhãn CLI/heatmap. Classifier thô và CLI đánh giá từng
  box giữ nguyên. Không đổi ID, NMS, bộ lọc sân, guard, schema/API/dependency.
- Replay 5.215 quan sát: chuyển trực tiếp nhãn biết khác nhau 43 -> 0,
  mọi đổi nhãn (gồm unknown) 103 -> 92. Unknown 99 -> 624 (1,90 -> 11,97%).
  Đây là từ chối khi chưa chắc, không chứng minh mọi nhãn đúng/hết nhấp nháy.
- Fixture track_roles mới: tham chiếu 49 mẫu cũ để phát triển/hồi quy, thêm
  21 bbox trên 3 frame mới sau khóa quy tắc; nhãn agent chưa rà độc lập.
  Bộ cũ 48 ghép: đúng 46 -> 45, nhãn biết sai 2 -> 0, unknown 0 -> 3.
  Bộ mới 21 ghép: đúng 19 -> 18, sai 2 -> 0, unknown 0 -> 3. Cả 3 mẫu
  trọng tài mới đều unknown; không tuyên bố tăng accuracy/recall tổng thể.
- Chạy lại pipeline CUDA đủ 1.800 frame / 3 chunk, 6,78 FPS; guard giữ
  1499 ngoài hiệu chỉnh/30 chờ/271 cấp phép. Vẫn 5.215 dòng/30 ID tại
  1081–1350, khóa/tọa độ không đổi, nhãn khớp replay. Tổng A/B/ref/unknown
  2220/2232/139/624. Đọc lại đủ nguồn/đầu ra 1800 và cửa sổ 271 frame;
  schema, phạm vi, thời gian, heatmap và tổng nhãn đều qua.
- Xem 1140/1230/1290: mâu thuẫn được trả unknown, người ngoài sân vẫn lọc.
  Toàn bộ 115 test qua, 1 network deselected, cảnh báo Starlette cũ. Test
  gồm khởi tạo, nhiễu, sửa nhãn đầu sai, tách ID, hết hạn, bộ nhớ và pipeline.
- Báo cáo CV_TEAM_STABILITY.md, cập nhật CV_TRACKING/CV_TEAMS; fixture
  vid1_11f23eea_track_roles.json. Artifact cuối team_roles_final/ và video
  cùng tên dưới data/processed/clip_11f23eea/. Giữ kết quả cũ; lượt thử
  team_stabilized dừng giữa chừng không dùng nghiệm thu. Chưa qua bước 5;
  còn cải thiện trọng tài/độ phủ nhãn và nhiễu điểm chân trước đo chuyển động.

## Giảm nhiễu tọa độ và ngắt chuỗi chuyển động — 22/10/2026

- Thêm PitchSmoother và cờ tùy chọn --smooth-pitch (cần calibration +
  pitch-output). Lưu tracking_raw.jsonl, xuất tọa độ lọc vào tracking.jsonl,
  smoothing_quality.jsonl ghi trạng thái/ngắt mốc. Không đổi bbox/ID/nhãn,
  camera, guard, schema/API/dependency; cờ mặc định tắt để giữ phép so sánh.
- Lọc nhân quả từng segment/ID: trung vị 3 điểm + EMA tau 0,08 giây; chờ
  >=3 điểm và span >=0,08 giây, lịch sử <=0,2 giây. Gap >0,25 giây mở chuỗi
  mới, state vắng >1 giây xóa. Gate thô vmax 40 km/h + dung sai 0,5 m; điểm nhảy bị
  bỏ/ngắt mốc ngay, 3 điểm nhất quán mở chuỗi mới. Không ép tốc độ về 40.
- Thêm PitchMetrics.break_chain để không cộng quãng đường qua điểm lỗi.
  Replay 5215 điểm / 30 ID: 4935 điểm / 27 ID xuất, 177 chờ, 90 jump_rejected,
  13 reacquiring; 135 yêu cầu ngắt gồm khởi tạo/gap, không 135 biến cố thật.
  Cặp từng frame >40: 761 -> 16; đúng cùng 4847 cặp còn lại: 648 -> 16,
  p95 71,11 -> 23,47 km/h. Đây là diagnostic, chưa tốc độ thực.
- Mô phỏng điểm đứng yên có nhiễu: RMSE 0,0806 -> 0,0320 m. Đi 2 m/s rồi
  dừng: max lệch 0,1773 m, sau 250 ms còn 0,0078 m. Chưa có ground truth người
  đứng yên/vị trí thực trong clip; có trễ/cắt góc/thiếu đường khi ngắt chuỗi.
- Chạy lại CUDA đủ 1.800 frame / 3 chunk, 6,92 FPS; guard 1.499 ngoài / 30 chờ / 271 cấp
  phép không đổi. Toàn bộ 5.215 điểm thô khớp bản trước; 4.935 điểm lọc và state
  metrics khớp replay. Dữ liệu lọc 1086–1350, A/B/ref/unknown = 2176/2187/139/433;
  nhãn CLI vẫn 2220/2232/139/624 theo bbox, không đồng nhất hai coverage.
- Đọc lại đủ nguồn/video 1.800 frame và cửa sổ 271 frame; schema/phạm vi/thời
  gian/khóa/heatmap và đối chiếu nhãn thô qua. ID 1: 7,251 m / 4 s ->
  5,685 m / 3,5 s có cặp đo: số thấp hơn không tự chứng minh chính xác hơn.
- Toàn bộ 128 test qua, 1 network deselected, cảnh báo Starlette cũ. Test gồm
  nhiễu, trễ/dừng, chuyển động biết trước, teleport đơn/kéo dài, gap/segment,
  không ép tốc độ, pipeline codec/ByteTrack có và không smoothing.
- Báo cáo CV_PITCH_SMOOTHING.md, cập nhật CV_HOMOGRAPHY.md. Artifact cuối
  pitch_smoothed/ và video cùng tên dưới data/processed/clip_11f23eea/;
  biểu đồ coordinate_comparison.png ở pitch_smoothing_check/. Giữ bộ cũ.
  Nghiệm thu giảm nhiễu/ngắt mốc; chưa nghiệm thu chỉ số thực địa/chưa bước 5.
  Tiếp theo cần đối chiếu tọa độ tracking chuẩn độc lập và thêm tình huống khó.

## Benchmark tham chiếu Metrica — 22/10/2026

- Theo yêu cầu, thêm CLI backend.cv.metrica_benchmark, dùng CSV chuẩn từ
  Metrica Sports Sample Data, commit e706dd506b360d69d9d123d5b8026e7294b13996.
  Bốn file Home/Away Game 1/2 (~127 MB) lưu data/raw/metrica, khóa SHA256
  và protocol trong docs/fixtures/metrica_benchmark.json; không commit CSV.
- Metrica mô tả sân 105 × 68 m, gốc trái trên/tọa độ 0–1; đổi x*105,
  (1-y)*68 sang hệ dự án, không tự lật hướng tấn công. Bỏ bóng/NaN/ngoài sân,
  tách gap tự nhiên; ID Home/Away cục bộ ẩn danh, không liên kết StatsBomb.
- Khóa bộ lọc hiện tại, lấy hiệp 1, giây [60,120) ở cả hai trận, 25 FPS gốc,
  22 quỹ đạo mỗi trận, 65.051 điểm tham chiếu phân biệt. Chạy 26 lượt: clean
  một lượt/trận, noise sigma 0,15 m, spikes 1%, ba gap 0,6 s và relocation 0,6 s;
  các trường hợp lỗi dùng 3 seed 1729/2718/3141. Không nội suy dữ liệu lên 60 FPS.
- Đo RMSE cả raw-all và raw-common, coverage điểm, sai lệch quãng đường
  toàn cửa sổ/đúng phần metrics cộng, MAE tốc độ trọng số thời gian và lag
  lưới. Audit gọi PitchSmoother/PitchMetrics thật; không đổi thuật toán,
  pipeline, dependency hoặc schema/API. Đây không phải đo CV/homography.
- Kết quả không đồng đều: spikes RMSE median Game 1 1,289 -> 0,203 m;
  Game 2 1,239 -> 0,268 m. Nhưng noise nhẹ Game 2 0,212 -> 0,267 m (xấu hơn),
  clean tạo lệch 0,183/0,249 m; lag lưới thường 120 ms tại 25 FPS, không áp thẳng
  cho video 60 FPS. Không diễn giải giảm tốc độ nhiễu là vị trí chính xác hơn.
- Spikes giữ 98–99% điểm nhưng metrics đại diện 91–92% thời gian, thiếu khoảng
  8–11% distance so tham chiếu toàn cửa sổ. Relocation giữ 264/330 điểm lỗi
  mỗi lượt (80%), RMSE còn ~1,18 m dù covered-distance bias gần 0. Không coi
  bộ lọc là kiểm chứng vị trí hay dùng chỉ số coverage một mình để nghiệm thu.
- Toàn bộ 135 test qua, 1 network deselected, cảnh báo Starlette cũ. Test loader,
  hệ trục/gap, seed/không sửa reference, lỗi kéo dài, đường cong chuẩn,
  lag/coverage, hash và không ghi đè. Audit 26 lượt / 22 trajectory mỗi lượt,
  tổng/RMSE/coverage khớp; JSON finite. CLI tái tạo được từ manifest.
- Báo cáo METRICA_BENCHMARK.md, cập nhật CV_PITCH_SMOOTHING.md. Artifacts
  data/processed/metrica_benchmark/{results.json,summary.json,benchmark_comparison.png}.
  Giữ --smooth-pitch tùy chọn; chưa nghiệm thu bước 4 / chưa bước 5. Tiếp theo
  xử lý đánh đổi trễ và xác nhận lại vị trí sai kéo dài, đánh giá trên cửa
  sổ/trận mới nếu dùng bộ hiện tại để chỉnh phương pháp. Không gọi Metrica
  là ground truth tuyệt đối; nguồn chỉ là tọa độ tham chiếu do hãng công bố.

## Bộ lọc tọa độ v2.1 và holdout mới — 23/10/2026

- Theo yêu cầu tiếp tục, sửa PitchSmoother: thay median3 + EMA bằng fit
  tuyến tính nhân quả x/y trên 0,2 s, lấy vị trí tại timestamp hiện tại.
  Giữ warm-up 3 điểm/span 0,08 s; không ép vận tốc hoặc tọa độ vào sân.
- Với chuỗi đã xuất tọa độ, điểm vượt gate bị loại/ngắt metrics/xóa lịch sử;
  bỏ cơ chế tự nhận vị trí xa sau 3 điểm lặp lại. Gate giới hạn dt tối đa
  0,25 s, không mở bán kính vô hạn khi liên tục nhận điểm sai. Gap quan sát
  thật/ID/segment mới vẫn cho khởi tạo lại, không nối distance qua gap.
- V2 thử [180,240), seed 1618/5772/8119 phát hiện lỗi khóa ID vào nhiễu lúc
  khởi tạo: có trajectory không xuất điểm nào. Sửa v2.1: trước điểm xuất đầu
  tiên, gate thất bại thì hủy ứng viên và warm-up lại. Cửa sổ đó trở thành
  dữ liệu phát triển, không gọi holdout độc lập nữa; giữ manifest/artifact.
- Khóa v2.1 rồi đánh giá hiệp 1 [300,360), seed 1414/1732/2236 ở Game 1/2,
  65.443 điểm tham chiếu phân biệt. Manifest metrica_holdout_v2_1.json tạo
  trước chạy; không chỉnh phương pháp sau kết quả cuối. 26 lượt v2.1 và
  26 lượt baseline v1 db575e4 trên cùng raw/RNG, audit đầu vào khớp. Chạy
  thêm 26 lượt v2.1 trên bộ phát triển [60,120) để so với báo cáo cũ.
- Noise holdout: RMSE raw-common ~0,212 m -> 0,154/0,153 m (v1
  0,217/0,238 m). Clean lệch ~0,0034/0,0051 m. Lag lưới v2.1 0 ms,
  v1 thường 120 ms; lưới 40 ms, không khẳng định mọi chuyển động hết trễ.
  Cả 6 lượt relocation loại 330/330 điểm lỗi, v1 giữ 264/330 (80%).
- Đánh đổi: MAE tốc độ noise ~0,57–0,58 -> 0,84–0,85 km/h; covered-distance
  bias dương lớn hơn. Spikes giữ ~96,8–96,9% điểm nhưng metrics chỉ đại diện
  ~89–90% thời gian, thiếu ~8–9% đường toàn cửa sổ. Relocation Game 2 ID 4
  chỉ giữ ~71% điểm; chưa có chính sách xác minh lại danh tính độc lập.
- Replay clip cũ 5.215 dòng, không chạy lại detector/CUDA: 4.730 điểm/27 ID,
  363 warming_up, 122 jump_rejected, 206 yêu cầu ngắt mốc. Frame 1086–1350;
  A/B/ref/unknown = 2109/2097/139/385. Schema/khóa/nhãn/diagnostic/samples/
  heatmap khớp. Cặp suy tốc độ >40 tăng 16 -> 98, p95 23,47 -> 31,17 km/h
  so v1: vị trí ít trễ nhưng không có nghĩa tốc độ mượt/chính xác hơn.
- Toàn bộ 143 test qua, 1 network deselected, cảnh báo Starlette có sẵn.
  Có kiểm tra warm-up lỗi ở cả 25/60 FPS, timestamp không đều hai trục,
  trở về sau relocation, không tự mở lại nhờ thời gian, pipeline codec/
  ByteTrack. Test clip tĩnh dùng dung sai số thực 1e-10 m sau hồi quy.
- Không thêm thư viện hoặc đổi schema/API/guard/role/bbox, cờ --smooth-pitch
  vẫn tùy chọn tắt mặc định. Cập nhật CV_PITCH_SMOOTHING.md, đánh dấu báo cáo
  METRICA_BENCHMARK.md là baseline cũ; báo cáo mới METRICA_FILTER_V2.md.
  Artifacts data/processed/metrica_benchmark_v2/ (development_final,
  holdout_final, holdout_final_baseline, comparison_final_summary JSON) và
  clip_11f23eea/pitch_smoothing_v2_1_check/. Giữ bản cũ, không commit media.
- Chưa nghiệm thu bước 4 thực địa/chưa bước 5. Tiếp theo kiểm tra nhiễu
  tương quan camera/bbox, rẽ/dừng/ID đổi gần nhau và đánh đổi coverage/tốc độ;
  cần mốc video gán nhãn độc lập. Holdout cuối chỉ tách thời gian cùng hai
  trận, không tuyên bố tổng quát sang trận/camera khác; nếu chỉnh tiếp thì
  phải có cửa sổ đánh giá mới.

## Bộ lọc tọa độ v3: nhiễu tốc độ và hồi phục — 23/10/2026

- Theo yêu cầu tiếp tục công việc bước 4, tăng cửa sổ fit từ 0,2 lên 0,4 s;
  vẫn nhân quả tại timestamp hiện tại, warm-up 3 điểm/span 0,08 s. Fit điểm
  trừ trung bình để giảm triệt tiêu số thực; test tọa độ hằng tại biên sân.
- Sau lỗi liên tiếp, nếu thời gian từ raw point chấp nhận cuối trong
  (0,25;0,8] s, dùng vận tốc fit trước lỗi để kiểm tra điểm quan sát với
  residual <=0,5+6*dt²/2 m. Không học từ điểm loại, không xuất điểm dự báo,
  không cộng đường thiếu. Hết horizon dùng gate cũ; gap quan sát thật,
  ID/segment mới vẫn khởi tạo lại. Dung sai là heuristic, không chứng nhận
  gia tốc/vị trí hay danh tính. Giữ warm-up ứng viên của v2.1.
- Thêm scenario correlated_noise trong benchmark: AR(1) rho=exp(-dt/0,2),
  innovation sqrt(1-rho²), sigma biên 0,15 m/trục, reset ở gap tự nhiên.
  Không sửa reference, không mô phỏng đầy đủ camera chung/ID swap.
- Phát triển trên cửa sổ cũ [60,120); kiểm tra hồi quy ID 4 Game 2 ở
  [300,360) (không gọi holdout): coverage ~70,84–70,98 -> 98,24–98,52%,
  không giữ điểm relocation lỗi. Khóa phương pháp trước holdout mới.
- Holdout [420,480), hiệp 1 Game 1/2, seed 2449/3162/3873, manifest
  metrica_holdout_v3.json tạo trước chạy. 65.944 điểm tham chiếu, 22 quỹ
  đạo/trận, 32 lượt/bộ v3 và baseline ca85b08 (64 tổng); thêm correlated
  development riêng. Audit raw/RNG/count/RMSE/tổng trajectory khớp.
- Noise độc lập holdout: MAE tốc độ 0,83/0,86 -> 0,66/0,66 km/h; RMSE
  vị trí ~0,154 -> 0,121/0,122 m. Lag lưới chọn 0 ms (độ phân giải 40 ms,
  không áp thẳng sang video 60 FPS). Cả sáu lượt relocation loại toàn bộ
  330/330 điểm lỗi; ID 1024 Game 2/seed3873 coverage 49,87 -> 98,53%.
  Minimum coverage qua các lượt relocation Game 2: 49,87 -> 95,53%.
- Kết quả âm giữ rõ: clean RMSE ~0,005/0,009 -> 0,018/0,026 m. Nhiễu
  tương quan v3 RMSE ~0,216–0,217 m, hơi xấu hơn v2.1 và raw ~0,211–0,212 m;
  MAE tốc độ 1,13/1,17 -> 1,17/1,19 km/h, distance bias tăng. Minimum
  coverage vẫn có ID 84,33%; spikes thiếu ~9–10% distance toàn cửa sổ.
- Replay clip trên cùng 5.215 raw row: v3 giữ 4.735 điểm/27 ID, frame
  1086–1350; A/B/ref/unknown 2109/2097/139/390, 358 warming_up,
  122 jump_rejected, 206 yêu cầu ngắt mốc. Schema/khóa/nhãn/timestamp/
  diagnostic/samples/heatmap khớp. Trên cùng 4.658 cặp, >40 km/h 98 -> 30,
  p95 31,17 -> 24,20 km/h; vẫn chỉ diagnostic, chưa tốc độ thực địa.
- Test đi 2 m/s rồi dừng: max lệch 0,1116 m, sau 250 ms còn 0,0692 m,
  sau 400 ms bằng 0 trong sai số số thực. Đổi test bound sau 250 ms từ
  0,02 lên 0,08 m, thêm hội tụ sau 400 ms: ghi nhận đánh đổi phản ứng dừng.
- Toàn bộ 148 test qua, 1 network deselected, cảnh báo Starlette có sẵn.
  Thêm runner 8 m/s hồi phục sau burst 0,6 s ở 25/60 FPS, hết hạn dự báo,
  biên sân và AR tương quan/variance/gap; pipeline codec/ByteTrack qua.
- Cập nhật CV_PITCH_SMOOTHING.md và liên kết các báo cáo lịch sử; báo cáo
  mới METRICA_FILTER_V3.md có protocol, đầy đủ kết quả âm và lệnh tái tạo
  baseline từ Git trong tiến trình riêng. Không đổi dependency/schema/API/
  detector/role/guard, smoothing vẫn tùy chọn tắt mặc định. Không chạy lại
  CUDA hay ghi đè media; giữ artifacts cũ.
- Artifact cục bộ metrica_benchmark_v3/{development,development_correlated,
  development_correlated_baseline,holdout,holdout_baseline,summary,
  known_id4_development}.json; replay clip_11f23eea/pitch_smoothing_v3_check/.
  Tiếp theo cần mốc video gán nhãn độc lập và chốt chỉ số đủ tin cậy; phương
  án Metrica cho chiến thuật vẫn có trong ROADMAP. Chưa nghiệm thu bước 4
  thực địa/chưa bước 5; không chỉnh tiếp trên holdout mới rồi gọi độc lập.

## Bộ gán nhãn video thật — 23/10/2026

- Theo yêu cầu làm ngay bước đối chiếu độc lập, tạo CLI
  backend.cv.prepare_video_review và template HTML cục bộ. Không đổi mã
  tracking/guard/role/bộ lọc, schema/API hoặc dependency. Đây là công cụ QA,
  không tích hợp thêm tính năng vào frontend sản phẩm.
- Khóa raw video SHA11f23eea và clean SHA86f6f04c bằng hash đầy đủ trong
  docs/fixtures/video_review_plan.json; xác minh source chưa đổi. Mapping
  clean frame +600 = raw frame, raw time=10+clean_frame/60. Ảnh 1280×720,
  60 FPS nguồn; xử lý một lượt giải mã tuần tự, không giữ cả video trong RAM.
- Packet cục bộ data/processed/clip_11f23eea/human_review_v1/: 20 PNG gốc,
  ba clip early/middle/return 211/241/301 frame; ưu tiên tám ảnh return
  1105/1145/1185/1225/1255/1295/1325/1345 trong cửa sổ tạm hợp lệ. Hai đoạn
  còn lại không được coi là có chỉ số mét hợp lệ, chỉ QA tracking/hình học.
  Ảnh mẫu không trùng frame trong fixtures recalibration/checkpoint/ID cũ;
  vẫn cùng video, không tuyên bố tổng quát sang trận khác.
- Trang review.html không vẽ bbox/ID dự đoán, không tự điền nhãn chuẩn;
  người tự đặt mã cục bộ theo clip, chọn đội/độ chắc chắn, bấm chân hoặc
  mốc sân, đánh dấu từng ảnh đã kiểm tra rồi xuất JSON/CSV. Có tự lưu nháp
  và nạp JSON đúng packet; từ chối frame/pixel sai hoặc mã điểm trùng.
  Chỉ đánh dấu người trong vạch thi đấu, không staff/khán giả ngoài sân.
- review_frames.csv có 20 dòng ảnh, annotations_template.csv chỉ có header.
  Manifest chứa hash nguồn/ảnh/clip, timestamp/offset và 20 annotations rỗng,
  reviewed=false. Không tạo nhãn giả do agent rồi gọi độc lập. Chưa có sai
  số vị trí, ID switches hoặc độ đầy đủ dữ liệu từ nhãn người.
- Đã kiểm tra ảnh đại diện ba đoạn, hash/size cả 20 ảnh, giải mã đủ ba clip,
  metadata/offset và trạng thái nhãn trống. validation.json ghi kết quả QA
  file, không kết quả độ chính xác. Trình duyệt công cụ chặn protocol file://;
  không đi vòng, chưa kiểm tra trực tiếp bố cục/thao tác trong trình duyệt.
  Test Node cục bộ với DOM mô phỏng kiểm tra handler/đổi scale/lưu/nạp/xuất,
  không có tải file ra ngoài workspace hoặc nhãn thật trong kiểm thử.
- Toàn bộ 154 test qua, 1 network deselected, cảnh báo Starlette có sẵn.
  Test mới gồm PNG khớp pixel source, số frame clip, hash/offset/path/range,
  không ghi đè nhãn cũ và logic gán nhãn. CLI từ chối thư mục output đã có.
- Tài liệu VIDEO_HUMAN_REVIEW.md và README.md trong packet hướng dẫn làm
  tám ảnh return trước, xuất annotations_review.json về packet. Tọa độ
  nhãn người là pixel ảnh; tọa độ mét cầu thủ chưa có nên null. Mốc dùng
  sân 105×68 giả định, có thể ít/thẳng hàng, không mặc định đủ homography.
  Chưa có bộ bbox/MOT mọi frame, không tính MOTA/IDF1 hoặc tốc độ thực từ
  nhãn thưa. Bước tiếp theo phụ thuộc JSON của người kiểm tra, sau đó mới
  đối chiếu dự đoán khóa. Chưa nghiệm thu bước 4 thực địa/chưa bước 5.

## Agent tự đánh dấu bộ ảnh theo yêu cầu — 23/10/2026

- Người dùng không thao tác được và yêu cầu agent tự làm toàn bộ. Đã xem
  cả 20 PNG gốc, đánh dấu chân, đội, mã người cục bộ trong mỗi đoạn và mốc
  nhìn thấy. Không chép dự đoán của pipeline làm nhãn chuẩn. Nhãn ước lượng
  bằng mắt, qua che khuất có thể nhầm; ghi rõ không phải human ground truth.
- Fixture vid1_11f23eea_agent_review.json khóa source SHA86f6f04c, gồm
  411 quan sát người (A195/B196/ref20), 46 mốc sân; 375 điểm người visible,
  19 occluded, 17 uncertain. Người ngoài vạch sân/staff không đánh dấu;
  người ngoài ảnh/chân không thể xác định được bỏ và ghi chú.
- Exporter backend.cv.export_agent_review tạo JSON/CSV, 20 preview đã
  đánh dấu, summary và HTML đã điền tại human_review_v1/agent_review_v1.
  Từ chối output cũ, kiểm tra hash ảnh/nguồn/frame/bounds/ID trùng. Packet
  ban đầu và nhãn nháp cục bộ của người dùng giữ riêng; trang agent dùng
  namespace lưu nháp khác. Không tạo annotations_review.json mạo danh người.
- reviewed=true nghĩa agent đã xem; human_reviewed=false,
  annotation_provenance.author_type=agent, independent_ground_truth=false.
  Banner HTML/ảnh nêu nhãn agent. Sửa importer để không mất cờ agent khi
  nạp/xuất lại hoặc nhận cờ independent=true không hợp lệ cho nhãn agent.
- Tám ảnh return: 166 quan sát người theo agent, 153 tọa độ raw qua
  chiếu/guard, 140 tọa độ v3. Chưa ghép object, không gọi chênh lệch count
  là recall/FP/FN/ID switches. Không có RMSE mét, tốc độ thực hoặc MOTA/IDF1
  từ bộ nháp thưa. Hai đoạn còn lại chưa được coi là có chỉ số mét hợp lệ.
- 158 test qua, 1 network deselected, cảnh báo Starlette có sẵn. Kiểm tra
  exporter/provenance/import-export, đủ 457 điểm/20 frame và các path;
  xem preview đại diện ba đoạn. Trình duyệt công cụ vẫn chặn file://,
  không đi vòng; UI được test logic cục bộ, chưa test browser trực tiếp.
- Báo cáo VIDEO_AGENT_REVIEW.md, cập nhật hướng dẫn trước. Media/JSON xuất
  cục bộ không commit; fixture nhãn, exporter và test được commit để tái tạo.
  Không đổi tracking/guard/bộ lọc/dependency/schema/API. Đã làm xong phần
  agent được giao; chưa nghiệm thu bước 4 thực địa/chưa bước 5, không chờ
  người dùng nhập lại bộ ảnh để coi công việc này hoàn tất.

## Đối chiếu nhãn agent với đầu ra tracking — 23/10/2026

- Người dùng xác nhận đã ổn và yêu cầu tiếp tục. Giữ nguồn nhãn agent,
  không chuyển thành human/independent truth. Đánh giá tám ảnh return đã
  chọn; 166 nhãn người, gồm 154 visible và 12 occluded/uncertain bị loại
  khỏi ghép chính. Không chỉnh nhãn/gate theo kết quả.
- Kiểm tra cache bbox NMS 0,5 + ByteTrack có đủ 5.215 khóa frame/ID khớp
  production team_roles_final; lọc v3 có 4.735 khóa nằm trong raw. Bottom
  center bbox chiếu bằng ma trận frame khớp raw trong 1,37e-6 m, chỉ là
  kiểm tra tính nhất quán artifact, không sai số thực địa. Không chạy YOLO.
- Đóng băng 153 raw + 140 filtered observation ở tám ảnh trong fixture
  vid1_11f23eea_prediction_samples.json, kèm ma trận/hash input/filter commit.
  Protocol video_review_evaluation.json khóa canonical JSON SHA để không
  phụ thuộc newline Windows; ngưỡng chính 12 px, sensitivity 8/12/20 px.
- CLI backend.cv.evaluate_video_review ghép một-một tối đa số cặp rồi tối
  thiểu tổng khoảng cách Euclid, không dùng class/ID để chọn cặp. Loại
  trường hợp nhiều đối tác hoặc gần nhãn bị che khỏi đối chiếu ID/vai trò.
  Không nối chuỗi qua mẫu thiếu/mơ hồ hoặc gap >90 frame; chỉ là chỉ báo
  mẫu thưa, không MOT ID switches, MOTA/IDF1 hoặc detector recall.
- Gate 12 px: raw ghép 146/154 visible (143 không mơ hồ), v3 ghép 135
  (134 không mơ hồ). RMSE matched-only 2,997 -> 2,808 px nhưng tập điểm khác.
  Cùng 132 cặp cùng frame/nhãn/track ID không mơ hồ: 2,781 -> 2,786 px,
  không có bằng chứng cải thiện rõ vị trí. Không lấy việc bỏ điểm làm
  chứng minh lọc chính xác hơn.
- Hai trường hợp nghi đổi ID: B05 frame 1145->1185 ID 9->15, A02
  frame 1295->1325 ID 11->29. V3 chỉ đếm 1 ở gate 12 vì A02/1325 mơ hồ,
  vẫn có ID 29 nên không coi là sửa ID. Đã xem crop so sánh, thấy chen sát/
  che khuất phù hợp giả thuyết fragmentation; danh tính agent vẫn tentative.
- Gate 8/12/20: số ghép raw 145/146/146, v3 135/135/136; ID biểu kiến
  raw 2/2/0 và v3 2/1/0. Gate lớn loại nhiều khoảng mơ hồ, không chọn 20 px
  để tuyên bố không lỗi ID. Vai trò known trong tập chọn không bất đồng;
  raw còn 13 unknown trên 143 cặp, v3 11 unknown trên 134; không tuyên bố 100%.
- 167 test qua, 1 network deselected, cảnh báo Starlette có sẵn. Test tối ưu
  so vét cạn, phản ví dụ greedy, loại nhãn mơ hồ, không dùng class để ghép,
  không nối qua mẫu thiếu/gap, hash/nguồn/pixel/ID trùng và không ghi đè.
  Snapshot đã commit nên replay báo cáo không cần GPU/video; không tự đại
  diện cho pipeline mới nếu sau này sửa code. Không đổi dependency/schema/
  API/detector/tracker/role/homography/guard/bộ lọc hay media gốc.
- Báo cáo VIDEO_REVIEW_EVALUATION.md; artifacts cục bộ
  clip_11f23eea/agent_review_evaluation/{results.json,identity_candidates.jpg}.
  Chốt video cho demo tracking/phân đội/on-pitch/guard trong đoạn ngắn;
  chưa nghiệm thu vị trí/tốc độ/quãng đường thực địa hay định danh cầu thủ.
  Kết thúc đợt rà soát này, chuyển công việc kế tiếp sang bước 5 dùng Metrica
  theo ROADMAP dự phòng; không tự ghép danh tính Metrica ẩn danh/StatsBomb.

## Bước 5 — baseline hình dạng đội hình (23/10/2026)

- Thêm `backend/tactics/formation.py`: CLI JSON nội bộ, tái sử dụng loader
  Metrica, cửa sổ 10 giây, yêu cầu đúng 11 ID và >=80% khung đủ người đồng
  thời; chỉ định thủ môn/hướng tấn công, tách tuyến của 10 cầu thủ ngoài sân.
  Không ép kết luận khi thiếu người, đổi đội hình nhân sự hoặc tuyến mơ hồ.
- Xuất vị trí trung vị cầu thủ, tâm/chiều rộng/chiều sâu đội, thành viên
  từng tuyến, chất lượng cửa sổ và SHA256 nguồn. Chỉ là hình dạng quan sát,
  không phải sơ đồ chiến thuật có nhãn chuẩn. Không đổi schema/API/thư viện.
- Chạy Game 1/2 A/B hiệp 1 giây 60–120: 24 cửa sổ, 3 có hình dạng,
  21 chưa xác định. Artifacts `data/processed/formation_v1/game{1,2}_{A,B}.json`.
  Tỷ lệ từ chối cao; chưa chứng minh độ chính xác, không nghiệm thu toàn bộ
  bước 5. Chi tiết/giả định thủ môn và hướng ở `FORMATION_BASELINE.md`.
- Kiểm tra: 9 test mới; toàn bộ `pytest -q --basetemp .tmp/pytest_formation_full_v1`:
  **176 passed, 1 network deselected**; cảnh báo Starlette đã có từ trước.
- Còn lại: bộ so khớp sơ đồ có đánh giá bằng nhãn độc lập, đọc/đối chiếu
  lineup StatsBomb theo thời điểm trên cùng trận StatsBomb, chỉ số cầu thủ
  và tích hợp giao diện. Không ghép danh tính hai nguồn khác trận.

## Bước 5 — tham chiếu sơ đồ/lineup StatsBomb (23/10/2026)

- Thêm `backend/tactics/statsbomb_formation.py`: đọc CSV đã có, sắp sự
  kiện theo index, tra tactics theo hiệp/timestamp, giữ ID/vai trò cầu thủ.
  Không dùng lineup đầu trận cho mọi thời điểm. Thay người, Player Off/On,
  thẻ đỏ làm tham chiếu chưa xác định tới mốc tactics hợp lệ tiếp theo.
- Có hàm đối chiếu nhãn cùng trận; từ chối cửa sổ đi qua mốc thay đổi,
  thiếu tham chiếu hoặc quan sát chưa xác định. Không ghép ID hai nguồn.
- Chạy trên cache thật trận 8650: 14 mốc, Bỉ từ 4-3-3 sang 5-3-2 ở
  hiệp 2 giây 2234,280. JSON cục bộ
  `data/processed/formation_v1/statsbomb_8650_reference.json` giữ hash nguồn.
  Fixture trích 14 mốc được commit để kiểm thử ngoại tuyến. Chi tiết
  `STATSBOMB_FORMATION_REFERENCE.md`; không thêm thư viện/API/schema.
- 12 test mới; toàn bộ `pytest -q --basetemp .tmp/pytest_sb_formation_full_v1`:
  **188 passed, 1 network deselected**; cảnh báo Starlette đã có.
- Phần tham chiếu/đối chiếu nhãn đã làm, chưa có tracking cùng trận để
  báo accuracy; baseline Metrica vẫn 3/24 cửa sổ có kết quả. Chưa nghiệm
  thu bước 5. Còn nhận diện có đánh giá độc lập, chỉ số cầu thủ và giao diện.

## Bước 5 — hồ sơ cầu thủ và báo cáo hai đội (23/10/2026)

- Thêm `backend/tactics/metrica_report.py`: CLI JSON hai đội kết hợp các
  cửa sổ hình dạng và hồ sơ từng ID, khóa hash hai nguồn theo manifest.
  Xuất vị trí trung vị, heatmap, tỷ lệ khung/thời gian, quãng đường quan sát,
  tốc độ trên khoảng hợp lệ, số khoảng bị loại và số lần ngắt liên tục.
- Tái sử dụng PitchMetrics; thiếu một khung cũng ngắt, không nối khoảng
  trống, không ngoại suy, không ép vận tốc về 40. Tốc độ null nếu chưa đủ
  khoảng tính. Không gắn nguồn Metrica thành video, không đổi schema/API.
- Chạy Game 1 và 2 giây 60–120: 44 hồ sơ; Game 1 A có 2 khoảng vượt
  ngưỡng bị loại, các đội còn lại không có. Báo cáo cục bộ
  `data/processed/formation_v1/game{1,2}_tactics_profiles.json`.
  Có tỷ lệ dữ liệu/thời gian để tránh hiểu số từng phần là tổng cả trận.
- 7 test mới; toàn bộ `pytest -q --basetemp .tmp/pytest_step5_profiles_full_v1`:
  **195 passed, 1 network deselected**; cảnh báo Starlette cũ. Chi tiết
  phương pháp, lệnh chạy và số liệu ở `STEP5_PLAYER_PROFILES.md`.
- Chức năng bước 5 hiện có baseline hình dạng, tham chiếu StatsBomb và hồ
  sơ cầu thủ ngoại tuyến. Chưa nghiệm thu chất lượng nhận diện chiến thuật:
  vẫn 3/24 cửa sổ có hình dạng, thiếu nhãn độc lập cùng tracking. Giao diện
  ở bước 8; không báo hoàn thành phần đánh giá khi chưa có dữ liệu.

## Bước 5 — so khớp mẫu và đánh giá tái lập (23/10/2026)

- Thêm `formation_templates.py`: sáu mẫu hình học, chuẩn hóa vị trí tương
  đối và phép ghép một-một tối ưu bằng DP tập con, không thêm dependency.
  Từ chối co cụm, khớp kém hoặc hai mẫu quá gần; điểm không phải xác suất.
  `metrica_report` có `--formation-method template`, giữ `gap` mặc định.
- Giữ guard cửa sổ đúng 11 người, >=80% đồng thời và không trộn ID.
  Không thay metric chuyển động/API/schema. Đã chạy CSV thật hai trận,
  xuất 44 hồ sơ ở `formation_v1/game{1,2}_tactics_templates_v1.json`.
- Thêm evaluator và hai fixture: 72 ca hình học tự dựng có nguồn nhãn
  rõ ràng; 24 cửa sổ Metrica khóa vị trí/hash nguồn, tham chiếu thực đều
  `unreviewed`, không lấy dự đoán gap làm nhãn hoặc tự nhận nhãn độc lập.
- Giả lập: gap đúng 52/54 ca có sơ đồ, template 54/54; cả hai từ chối
  18 ca kỳ vọng chưa xác định. Chỉ kiểm tra giả thiết hình học, không phải
  accuracy thực tế. Metrica: gap xuất 3/24, template 2/24 ở hai cửa sổ
  khác; chưa có nhãn thật để kết luận cách nào đúng hơn. Ngưỡng margin
  0,04/0,08/0,12 cho 2/2/0 kết quả, chưa đủ căn cứ thay phương pháp mặc định.
- Artifacts: `formation_v1/template_comparison{,_frozen}_v1.json`.
  Phương pháp, nguồn nhãn, kết quả và lệnh ở `FORMATION_TEMPLATE_EVALUATION.md`.
- 12 test mới; toàn bộ `pytest -q --basetemp .tmp/pytest_templates_full_v1`:
  **207 passed, 1 network deselected**, cảnh báo Starlette cũ.
  Còn đánh giá chiến thuật bằng nhãn cùng tracking có tiêu chí thống nhất;
  chưa nghiệm thu chất lượng nhận diện bước 5, chưa chuyển sang bước 5b.

## Bước 5 — rà soát nháp 24 cửa sổ thật (23/10/2026)

- Đã xem bốn bảng vị trí trung vị và 15 ảnh thời điểm đủ người trên năm
  cửa sổ Game 2. Ghi fixture agent review với 5 nhãn nháp mức tin cậy vừa phải,
  14 cửa sổ không thể chấm rõ ràng và 5 thiếu dữ liệu. Không ép nhãn các
  cửa sổ còn lại hoặc coi không chấm là nhãn thật unknown.
- Nhãn do Codex rà, đã biết tổng hợp dự đoán từ trước; không phải đánh
  giá mù/độc lập/con người. Fixture giữ cờ nguồn nhãn, lý do và nhóm ID
  từng tuyến. 165 điểm ảnh thời điểm trùng frame/time/xy với CSV đã khóa.
- Thêm CLI `backend/tactics/review_formation.py`: kiểm tra nguồn/cấu trúc,
  đối chiếu và xuất JSON/bảng Markdown, tùy chọn tạo hình QA từ fixture.
  Không cần CSV lớn để chạy lại; không sửa API/schema/thuật toán/ngưỡng.
- Trên 5 nhãn nháp: gap từ chối 4, không đồng ý 1; template từ chối 3,
  không đồng ý 2. Mỗi phương pháp có 19 cửa sổ không chấm. Không tính
  đây là accuracy, không có căn cứ đổi phương pháp mặc định.
- Artifacts `data/processed/formation_v1/agent_review_replay_v1/` gồm
  evaluation.json, review.md, bốn bảng trung vị và năm bảng snapshot.
  Chi tiết `FORMATION_AGENT_REVIEW.md`; người dùng không cần nhập lại.
- 11 test mới; toàn bộ `pytest -q --basetemp .tmp/pytest_formation_review_full_v1`:
  **218 passed, 1 network deselected**, cảnh báo Starlette cũ.
  Chốt đợt rà nháp, giữ bước 5 ở mức thử nghiệm; đánh giá chiến thuật độc
  lập vẫn chưa đạt, không chỉnh cùng tập này rồi tuyên bố đã kiểm định.

## Bước 5 — kiểm tra thời gian trên 24 cửa sổ mới (23/10/2026)

- Khóa protocol giây 120–180 hiệp 1 cả hai đội Game 1/2 trước lần chạy,
  không trùng 24 cửa sổ giây 60–120 đã phát triển/rà nháp. Không có nhãn
  tham chiếu thực ở tập mới, không báo accuracy hoặc nhãn kiểm định độc lập.
- Thêm CLI chẩn đoán `backend/tactics/formation_stability.py`: giữ guard
  cũ, so nhãn trung vị với 5 ảnh thực ở offset 1/3/5/7/9 giây, dung sai
  0,08s, đủ 5 ảnh và >=4 ảnh cùng nhãn. Không bỏ unknown khỏi mẫu số,
  không dùng các ảnh để ép nhãn trung vị chưa xác định.
- Kết quả: gap có 2/24 nhãn trung vị, template 3/24; cả hai 0/24 đạt
  quy tắc thời gian. Ba cửa sổ bị guard loại; 104/105 thời điểm còn lại
  có khung trong dung sai. Không thay ngưỡng/mặc định/API/schema/thư viện.
- Artifact `data/processed/formation_v1/stability_120_180_v1.json` giữ
  nguồn/hash, protocol, tọa độ ảnh và các kết quả trung gian. Chi tiết
  `FORMATION_TEMPORAL_CHECK.md`. Chốt nhận diện sơ đồ còn thử nghiệm;
  sự không đồng thuận không tự chứng minh nhãn sai hoặc HLV không có sơ đồ.
- 6 test mới; toàn bộ `pytest -q --basetemp .tmp/pytest_formation_stability_full_v1`:
  **224 passed, 1 network deselected**, cảnh báo Starlette cũ.
  Không tác động hồ sơ chuyển động hoặc tham chiếu StatsBomb.

## Bước 5 — cải tiến tuyến nghiêng/lệch cánh (23/10/2026)

- Thêm `formation_aligned.py`: tìm kiếm độ nghiêng chung, phân tuyến theo
  thứ tự dọc, cho dịch tâm ngang mỗi tuyến, phạt độ linh hoạt, vẫn trả
  unknown khi khớp kém/mơ hồ. Giữ guard 11 người và >=80% bao phủ.
- Có `--formation-method aligned` trong báo cáo; `--include-aligned`
  trong đánh giá giả lập, đối chiếu nháp và chẩn đoán thời gian. Giữ gap
  mặc định, không đổi API/schema hoặc thêm dependency. Lưu policy trong JSON.
- Stress 72 ca tự dựng (54 có sơ đồ): gap đúng 0, template 28, aligned 54;
  cả ba từ chối 18 ca kỳ vọng chưa xác định. Bộ ca thiết kế theo giả thiết
  mô hình, không phải accuracy trận thật hoặc kiểm định độc lập.
- Trên 5 nhãn nháp phát triển: aligned đồng ý 1, không đồng ý 2, từ chối 2.
  Trên 24 cửa sổ 120–180 đã xem: aligned có 3 nhãn trung vị, 1 đạt 4/5
  ảnh thời điểm (Game 2 B 140–150s, 4-3-3); hai cách cũ vẫn 0 đạt. Không
  coi đồng thuận thời gian là xác nhận chiến thuật; chưa đổi mặc định.
- Đã xuất `game{1,2}_tactics_aligned_v1.json`, `aligned_comparison_with_stress_v1.json`,
  `aligned_draft_review_v1/`, `aligned_stability_120_180_v1.json` trong
  `data/processed/formation_v1/`. Cả 44 hồ sơ chuyển động giữ nguyên so báo
  cáo cũ. Chi tiết phương pháp/giới hạn/lệnh ở `FORMATION_ALIGNED.md`.
- 13 test mới; toàn bộ `pytest -q --basetemp .tmp/pytest_aligned_full_v1`:
  **237 passed, 1 network deselected**, cảnh báo Starlette cũ.
  Tiến bộ chức năng chưa thay thế yêu cầu đánh giá chiến thuật độc lập.

## Bước 5 — nguồn vai trò chính thức cùng Game 3 (23/10/2026)

- Kiểm tra nguồn Metrica tại commit khóa: Game 3 có EPTS XML chứa vai trò,
  hướng, ánh xạ cột và khoảng định dạng. Tải metadata/tracking, xác minh
  byte và Git blob SHA1 tại commit, khóa SHA256 trong manifest riêng.
  Không suy vai trò Game 3 cho Game 1/2 hoặc ghép người với StatsBomb.
- Thêm `backend/tactics/metrica_game3.py`: parser biến thể EPTS đã khóa,
  ánh xạ PlayerChannelRef tới ID/số áo, xử lý đổi roster, clock từng hiệp,
  tọa độ 105×68 và đoạn thiếu. Đọc tuần tự, giữ riêng khoảng yêu cầu.
  Không thêm thư viện/API/schema hoặc chỉnh thuật toán/threshold mặc định.
- Tham chiếu khai báo: A có cấp thô 4-5-1, độ sâu vai trò 4-2-3-1;
  B 4-4-2 cả hai cấp. Đây là cách nhóm vai trò từ XML, không phải nhãn
  chiến thuật từng thời điểm. Thủ môn Game 3 là A11/B1028.
- Chạy 24 cửa sổ hiệp 1 giây 60–180: gap khớp 0/khác 2/từ chối 22;
  template 0/0/24; aligned 2/1/21 so bố trí độ sâu vai trò đã chọn trước.
  Không báo accuracy chiến thuật hoặc gán mọi pha bóng theo metadata tĩnh.
- Artifact `data/processed/formation_v1/game3_role_comparison_60_180_v1.json`.
  Commit fixture XML gốc và 9 dòng tracking để test ngoại tuyến; giữ byte
  bằng .gitattributes. Chi tiết nguồn/lệnh/giới hạn `METRICA_GAME3_REFERENCE.md`.
- 9 test mới; toàn bộ `pytest -q --basetemp .tmp/pytest_game3_full_v1`:
  **246 passed, 1 network deselected**, cảnh báo Starlette cũ.

## Bước 5 — hồ sơ sự kiện StatsBomb cùng lineup (23/10/2026)

- Thêm `backend/tactics/statsbomb_profiles.py`: hồ sơ sự kiện theo ID,
  số áo/xuất phát, short_name theo helper cũ, Pass/hoàn thành/tỷ lệ,
  Carry/Shot/Shot Goal và index nguồn. Giữ cả cầu thủ lineup zero-event.
- Nối ngữ cảnh vai trò bằng cùng match/team/player ID và thứ tự index;
  không nhìn trước Tactical Shift có cùng timestamp. Nhân sự thay đổi
  làm vai trò unknown, không tự gán vai trò cũ cho cầu thủ thay vào.
- Thiếu cột outcome thì thống kê phụ thuộc outcome là null; không đồng
  nhất sự kiện với chạm bóng/phút thi đấu. Loại hiệp ngoài 1–4, Shot Goal
  không gồm own goal. Hai ID trùng tên không bị nhập chung; không ghép
  StatsBomb với Metrica hoặc đổi schema/API/thư viện.
- Cache thật 8650: 27 hồ sơ, 3.527 sự kiện quy ID. Brazil 532 Pass/459
  hoàn thành/25 Shot/1 Shot Goal; Belgium 385/310/8/1. Các tổng khớp
  đối chiếu trực tiếp cache, không đọc Shot Goal thành tỷ số trận.
- Artifact `data/processed/formation_v1/statsbomb_8650_player_profiles_v1.json`.
  Phương pháp/lệnh/giới hạn ở `STATSBOMB_PLAYER_PROFILES.md`.
- 6 test mới; toàn bộ `pytest -q --basetemp .tmp/pytest_event_profiles_full_v1`:
  **252 passed, 1 network deselected**, cảnh báo Starlette cũ.
  Nhận diện chiến thuật vẫn thử nghiệm; hồ sơ sự kiện không thay nhãn
  độc lập để nghiệm thu chất lượng phần đó.

## Bước 5b — fine-tune YOLO11 nano và so sánh mAP (23/10/2026)

- Thêm CLI chuẩn bị dataset và huấn luyện/đánh giá:
  `backend/cv/prepare_person_dataset.py`, `backend/cv/finetune_person.py`.
  Không thêm thư viện, API hoặc đổi hợp đồng dữ liệu.
- Dùng nguồn martinjolif/football-player-detection, revision
  `e8b8cea002692efd74c945fcdad63e729adc5671`, khai báo CC BY 4.0.
  Ghi công nguồn, bản sao, nhãn chuyển đổi và liên kết ở `CV_FINETUNE_YOLO.md`.
  Kiểm file theo inventory Git/LFS; gộp GK/player/referee thành person,
  bỏ ball, cắt hai box vượt biên.
- 15 nhóm tiền tố/ảnh trùng hoặc gần trùng; seed 20261023, train 199 ảnh
  (4.568 box), val 100 (2.358), test 73 (1.653). Không giao component/hash
  pixel giữa các tập; nhóm chỉ là heuristic, chưa xác minh trận độc lập.
- Huấn luyện CUDA trên RTX 3050 6 GB: 15 epoch, ảnh 640, batch 4, AdamW,
  lr0 0,001, AMP tắt. Chọn best theo validation; test chỉ dùng sau train.
  Validator riêng lọc person trước NMS cho cả baseline 80 class và mô hình
  một class, khắc phục validator bản 8.3.221 bỏ qua args.classes.
- Test: mAP50 0,710436 → 0,916667; mAP50–95 0,396201 → 0,563989;
  precision 0,742526 → 0,924402; recall 0,742287 → 0,857834.
  Precision/recall ở điểm F1 của từng mô hình; chỉ có một lượt một seed.
- Artifact: `data/processed/yolo_person_finetune_v1/comparison.json`,
  `training/weights/best.pt`; snapshot Git ở
  `docs/fixtures/yolo_person_finetune_result_v1.json`. Giữ trọng số gốc,
  chưa tự áp dụng best.pt vào pipeline tracking. Không suy mAP thành
  accuracy giữ ID/phân đội/sơ đồ hoặc độ chính xác trên vid1.mp4.
- Chín test mới; toàn bộ
  `pytest -q --basetemp .tmp/pytest_finetune_full_v1`:
  **261 passed, 1 network deselected**, cảnh báo Starlette cũ.

## Bước 5b — đối chiếu tracking video với trọng số mới (23/10/2026)

- Thêm runner `backend/cv/compare_person_video.py`, gọi nguyên track_video
  và chỉ bọc ByteTrack để ghi lại đầu ra. Khóa input/hash/cấu hình ở
  `yolo_person_video_protocol_v1.json`, giữ hai bản hiệu chỉnh/checkpoint
  return nguyên byte trong fixtures. Không sửa pipeline/API/schema.
- Chạy mới cả hai mô hình đủ 1.800 frame, ảnh suy luận 1280, conf 0,1,
  cùng mẫu áo/ByteTrack/NMS/camera guard/on-pitch-only. Hai lượt cùng
  270 frame có box, tám ảnh mẫu cùng guard tracked. Camera matrix có thể
  khác do loại vùng người theo bbox của từng mô hình.
- Tám ảnh return, 154 nhãn visible: ghép 146 → 150, quan sát dự đoán
  153 → 217; dự đoán chưa ghép khác 2 → 55. Montage cho thấy nhiều khung
  chồng/bộ phận cùng người ở bản fine-tuned; chưa gọi mọi unmatched là FP.
- Trên 87 khoảng ID chung: đổi ID biểu kiến 1 → 6. Gate 8/20 px cũng có
  nhiều đổi ID hơn ở ứng viên. Đây là chẩn đoán nhãn agent thưa, không phải
  IDF1/MOTA. Không thay mặc định; không chỉnh threshold theo tám ảnh này.
- Kết quả/video/montage: `data/processed/yolo_person_video_comparison_v1/`;
  snapshot Git `docs/fixtures/yolo_person_video_result_v1.json` và tài liệu
  `CV_FINETUNE_VIDEO.md`. Chốt so sánh 5b, chưa triển khai bước 6.
- Ba test mới; toàn bộ `pytest -q --basetemp .tmp/pytest_person_video_full_v1`:
  **264 passed, 1 network deselected**, cảnh báo Starlette cũ.

## Bước 6 — baseline xG XGBoost, AUC/Brier và tham chiếu StatsBomb (23/10/2026)

- Thêm `backend/tactics/xg.py`, `prepare_xg.py`, `train_xg.py`: chuẩn bị
  CSV cú sút, feature trước sút, train/validation/test, native model JSON,
  inference nội bộ và báo cáo JSON/CSV. Không đổi API/schema/cache cũ,
  không thêm thư viện hoặc giao diện.
- Nguồn StatsBomb Open Data (Hudl), revision
  `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`; inventory 185 file khóa
  kích thước/Git blob SHA1. Ghi công và điều kiện nguồn ở `XG_BASELINE.md`.
  Dữ liệu/trọng số giữ cục bộ, không commit bản ghi cú sút.
- Development World Cup 2018 + Euro 2020: 92 trận train (2.251 cú sút,
  214 Goal), 23 val (621/43), chia theo hash match ID seed 20261023.
  World Cup 2022 test riêng 64 trận (1.430/152), muộn hơn development.
  Không giao match/event ID. Loại 69 penalty trong trận và 118 period
  ngoài 1–4; không mô hình penalty hoặc luân lưu.
- Tám feature: khoảng cách/góc mở/lệch ngang, đánh đầu/bộ phận khác,
  sút phạt trực tiếp/first time/under pressure. Dùng tọa độ chung 105×68,
  cầu môn rộng 7,32 m. Không outcome/end location/xG nguồn/ID làm input;
  Goal là nhãn thật. Chưa dùng ngữ cảnh freeze frame thủ môn/hậu vệ.
- Một cấu hình depth 3/lr 0,03/min_child_weight 10/lambda 10, tối đa 600
  cây, early stopping 40 theo log loss val; best_iteration 65. Test không
  dùng chọn cấu hình hoặc calibration. Lưu/nạp dự đoán khớp <=1e-7;
  smoke inference năm cú sút thật đã bỏ outcome/xG nguồn khỏi input.
- Test AUC/Brier/log loss: XGBoost 0,766545/0,084666/0,293669;
  StatsBomb 0,814775/0,076192/0,266505; xác suất cố định train
  0,5/0,095121/0,339404. Baseline tốt hơn constant, kém StatsBomb.
- Bootstrap ghép cặp theo trận 500 lượt: chênh AUC dự án trừ StatsBomb
  khoảng 95% [-0,07735; -0,01658], Brier [+0,00501; +0,01215]. Không
  gồm bất định huấn luyện lại; không biết dữ liệu huấn luyện của provider.
  Mẫu giải quốc tế nam nhỏ, chưa chứng minh tổng quát hóa sang video.
- Artifact `data/processed/xg_dataset_v1/`, `data/processed/xg_model_v1/`;
  protocol/inventory/snapshot tổng hợp ở `docs/fixtures/xg_*_v1.json`.
  Phương pháp, số liệu, calibration và lệnh ở `XG_BASELINE.md`.
- Chín test mới; toàn bộ `pytest -q --basetemp .tmp/pytest_xg_full_v1`:
  **273 passed, 1 network deselected**, cảnh báo Starlette cũ.

## Bước 7 — advisor xG + SHAP, gợi ý có căn cứ (23/10/2026)

- Thêm `backend/advisor/shot_advisor.py`: CLI ngoại tuyến, model xG cũ,
  TreeExplainer raw/tree_path_dependent, ba luật rà soát lựa chọn vị trí,
  dứt điểm dưới áp lực và cách tạo cơ hội xG cao. Ngưỡng heuristic cố định
  trong `advisor_protocol_v1.json`, chưa HLV đánh giá. Không LLM hoặc
  policy chiến thuật được học, không thêm thư viện/API/schema dùng chung.
- Lọc penalty và period ngoài 1–4; không cần outcome/xG StatsBomb làm
  input. Theo team ID, giữ đội không có cú sút và trạng thái thiếu mẫu/
  không đủ luật. Mỗi gợi ý có event ID, tử số/mẫu số, xG/feature/SHAP trung
  bình; từng cú sút có player ID/tên ngắn, thời điểm/index để tra nguồn.
- Cắt Booster trong RAM tới best_iteration+1 (66 cây), không giải thích
  cả 106 cây đã lưu. Kiểm hash/feature/best iteration, cộng SHAP log-odds
  và sigmoid khôi phục margin/xG; từ chối xuất gợi ý nếu vượt ngưỡng.
- Trận 8650 có 33 cú sút: Brazil 25, xG tổng 2,990, nhóm thấp 13/25;
  Belgium 8, tổng 0,558, nhóm thấp 6/8. Mỗi đội một gợi ý rà vị trí;
  hai luật khác không tự sinh. Đây là trận val của bước 6, không đánh giá
  advisor độc lập hoặc suy luận tỷ số/khả năng dứt điểm.
- Tính lại 2/2 căn cứ khớp các event và trung bình. Max error SHAP
  9,54e-7 log-odds/1,79e-7 xác suất. Chỉ xác nhận số học, không hiệu quả
  chiến thuật. Không kết luận nhân quả hoặc gợi ý thay người/đổi sơ đồ.
- Artifact chốt `data/processed/advisor_8650_v1_final/`, snapshot/hash
  `docs/fixtures/advisor_result_v1.json`, tài liệu `ADVISOR_BASELINE.md`.
- Bảy test mới; toàn bộ `pytest -q --basetemp .tmp/pytest_advisor_full_v1`:
  **280 passed, 1 network deselected**, cảnh báo Starlette cũ và ba
  deprecation của bảng màu SHAP. Tiếp theo bước 8 frontend theo ROADMAP.

## Bước 8a — video và sân mini trên frontend (26/10/2026)

- Thay trang chờ `/video` bằng `VideoAnalysis.tsx`, dùng Pitch/toSvg hiện
  có; thêm type TrackingRow đúng contract và bộ đọc/tra frame
  `frontend/src/lib/videoTracking.ts`. Không sửa DATA_CONTRACT/backend API,
  thuật toán CV, dependency hoặc các trang hồ sơ/báo cáo chờ.
- Video dùng object URL, tracking đọc cục bộ, tối đa 20 MB/200.000 dòng.
  Kiểm schema/toạ độ trong sân, trùng ID, timestamp; đổi video bỏ tracking
  cũ. Có loading/lỗi codec hoặc dữ liệu, checkbox ID, marker khoảng có
  tọa độ, offset và kiểm sai thời lượng. Không upload lên dịch vụ ngoài.
- requestVideoFrameCallback/mediaTime và fallback; binary search tìm
  frame, giữ điểm tối đa một chu kỳ, không nội suy qua khoảng trống.
  Seek xóa điểm cho tới khi xong; video giữ hướng sân gốc. Không xuất thêm
  quãng đường/tốc độ thực địa chưa được nghiệm thu.
- Helper `backend/cv/prepare_video_demo.py` kiểm raw/frozen tracking hash,
  chuẩn bị static demo cục bộ, ignore khỏi Git. Dùng H.264 gốc vì clean
  FMP4 OpenCV không phù hợp trình duyệt, offset +10 giây; không cài codec.
  4.735 dòng/265 frame v3, frame 1086 tại video 28,1 giây có 17 đối tượng.
- Browser: clip phát được, tua đầu/cuối xóa điểm, quay lại tracking hiện
  đúng điểm; offset 999 báo lỗi/xóa điểm, trả 10 khôi phục; checkbox ID.
  Desktop 1280 hai cột, 375 một cột không tràn ngang, console không lỗi.
  Ảnh `data/processed/frontend_video_review_v1/desktop.jpg`.
- Bốn Node test mới, `npm run test` qua; `npm run build`/`npm run lint`
  exit 0, còn cảnh báo bundle/Fast Refresh. Toàn bộ Python:
  `pytest -q --basetemp .tmp/pytest_frontend_video_full_v1`: **280 passed,
  1 network deselected**, cảnh báo Starlette/SHAP cũ.
- Chi tiết cách chạy/giới hạn `FRONTEND_VIDEO.md`. Chưa triển khai 8b/8c;
  chất lượng tọa độ/sơ đồ/gợi ý trước đây không được nâng đánh giá nhờ UI.

## Bước 8b — hồ sơ cầu thủ trên frontend (26/10/2026)

- Thay trang chờ `/players` bằng `PlayerProfiles.tsx`; bộ đọc JSON hai
  kind nội bộ ở `playerProfiles.ts`. Không thêm API/schema dùng chung,
  thư viện, mô hình hoặc chỉ số chưa có. Trang báo cáo HLV vẫn chờ 8c.
- StatsBomb: player ID/short_name/đội/số áo/xuất phát, chuyền/tỷ lệ, Carry,
  cú sút thành bàn, ngữ cảnh vai trò và index sự kiện. Null hiện —, không
  giả 0/100%, không tính phút/tốc độ từ sự kiện. Metrica: ID theo dõi,
  chỉ số chuyển động trong cửa sổ, hai mức bao phủ, heatmap 21×14 và
  trung vị; không gán tên thật hoặc ghép với StatsBomb/video.
- Tìm tên/ID, lọc đội, nguồn mới reset bộ lọc, rỗng bỏ hồ sơ cũ; đọc file
  JSON cục bộ giới hạn 5 MB/1.000 hồ sơ, loading/error/retry. Kiểm ID,
  tỷ lệ/tổng/index, hệ sân và tổng heatmap/thời gian đại diện.
- Helper `prepare_player_demo.py` kiểm hash và tính lại toàn bộ 27 hồ sơ
  StatsBomb từ CSV, 22 hồ sơ Metrica từ tracking, các bản tính khớp báo cáo
  cũ. Sao chép public asset cục bộ, ignore Git, không ghi đè nguồn.
- Browser đối chiếu De Bruyne 42/33 chuyền, 3 Shot/1 Goal, index Shot
  85/1214/1567, mở đủ 42 index Pass. Metrica A4 117,8 m/7,6 km/h/55,6 s;
  heatmap gốc trái dưới đúng. Lọc không khớp và đổi nguồn không giữ người
  cũ; 1280 px hai cột/375 px một cột không tràn, console không lỗi.
- Bốn test Node mới (tổng 8 qua), build/lint exit 0, cảnh báo bundle/
  Fast Refresh còn. Python `pytest -q --basetemp
  .tmp/pytest_frontend_players_full_v1`: **280 passed, 1 network deselected**,
  cảnh báo Starlette/SHAP cũ. Tài liệu `FRONTEND_PLAYERS.md`, ảnh cục bộ
  trong `data/processed/frontend_player_review_v1/`. Tiếp theo 8c.

## Quyết định đã chốt

- Python 3.11; FastAPI; Pydantic v2.
- Gốc tọa độ sân chuẩn ở góc trái dưới, đơn vị mét, sân 105 × 68.
- Người dùng xác nhận tiếp tục dùng 105 × 68 m làm kích thước sân mặc định
  cho bước 4, không chờ xác minh danh tính sân trong clip.
- Không cài PyTorch trong requirements ở bước này; phần CV có file dependency riêng.
- Frontend dùng dark mode mặc định, nền xám than và màu nhấn xanh lá.
- Tailwind CSS: `4.3.3`; shadcn CLI/UI: `4.21.4` (khởi tạo thành công ngày 2026-10-08).
