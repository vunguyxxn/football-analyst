# Bước 3: phân loại đội theo màu áo

**Lưu ý nguồn:** `data/raw/vid1.mp4` đã được thay bằng clip mới SHA256 bắt đầu
`11f23eea`. Fixture `vid1_team_samples.json` và số liệu 24/28 bên dưới thuộc
clip cũ SHA256 bắt đầu `fa6ea680`; cố dùng fixture cũ cho nguồn mới sẽ báo lỗi
SHA256. Hướng dẫn và kết quả nguồn mới ở cuối tài liệu.

## Phạm vi

Giữ YOLO + ByteTrack của bước 2, thêm tùy chọn `--team-samples`. Không truyền
tùy chọn này thì chương trình giữ cách vẽ ID của bước 2. Không thêm thư viện,
không đổi API FastAPI hay schema trong `DATA_CONTRACT.md`.

Với `vid1.mp4`, người dùng xác nhận A là áo tím/trắng, B là áo xanh ngọc,
trọng tài là áo vàng chanh. Khung A màu tím, B xanh ngọc, `referee` vàng,
`unknown` xám. Trọng tài vẫn có khung riêng để kiểm tra, nhưng không thuộc
nhóm A/B. Các nhãn thể hiện nhận định theo màu áo, chưa phải định danh người.

## Phương pháp

- Lấy vùng thân áo ở 20–80% chiều ngang và 20–50% chiều cao bounding box.
- Lấy trung vị màu Lab của pixel có saturation/value tối thiểu 40 (HSV
  OpenCV 8-bit); loại pixel xanh có hue 35–85 và value dưới 240 để giảm cỏ.
  Giữ pixel sáng gần bão hòa nhằm tránh loại nhầm áo trọng tài huỳnh quang.
- K-means hai cụm, `random_state=42`, `n_init=10`, chỉ fit mẫu cầu thủ trong
  tập hiệu chỉnh. Nhãn A/B của mẫu hiệu chỉnh ánh xạ số cụm sang tên đội.
- Màu tham chiếu trọng tài là trung vị các mẫu trọng tài hiệu chỉnh riêng;
  trọng tài không tham gia K-means hai đội.
- So sánh với ba tâm màu; trả `unknown` nếu không có đủ pixel, khoảng cách
  Lab 8-bit lớn hơn 45 hoặc chênh lệch giữa hai tâm gần nhất nhỏ hơn 5.
  Đây là ngưỡng heuristic cố định, không phải xác suất tin cậy hay Delta E
  chuẩn. Không tự gán đội cho áo khác màu như áo thủ môn.

Hiệu chỉnh một lần trước xử lý video; đọc/ghi từng frame, giữ tracker qua đoạn.
`team_observations` trong JSON là số lần quan sát theo frame, không phải số
cầu thủ duy nhất. Chưa dùng bỏ phiếu theo track nên nhãn có thể dao động.

## Mẫu tham chiếu và đánh giá

`docs/fixtures/vid1_team_samples.json` gồm 101 box có nhãn:

- 15 mẫu hiệu chỉnh tại frame 0 và 50: 9 A, 4 B, 2 trọng tài.
- 58 mẫu phát triển dùng chẩn đoán lỗi bộ lọc cỏ/áo huỳnh quang.
- 28 mẫu kiểm tra cuối tại frame 125, 225, 325, 425, 525, 625, 725, 825,
  không dùng chỉnh thuật toán sau khi xem kết quả. Loại hai proposal gần
  trùng cùng người/frame trước khi đánh giá (ID 46 và 62).

Box do YOLO đề xuất, nhãn do Codex gán bằng quan sát ảnh; hai mẫu trọng tài
hiệu chỉnh được chọn box bằng quan sát toàn frame. Người dùng đã xác nhận
quy ước màu đội, **chưa rà soát độc lập từng nhãn/box**. Nhóm cần kiểm tra
lại các nhãn trước khi dùng số liệu trong báo cáo chính thức.

Frame của ba tập không trùng nhau, nhưng đều thuộc cùng clip 17,34 giây và có
những người lặp lại. Đây không phải kiểm thử tổng quát hóa sang trận khác.
Tên và SHA256 video được kiểm tra để tránh dùng nhãn cho clip khác trùng tên.
`bbox` là tọa độ pixel nội bộ `[x1, y1, x2, y2]` để cắt ảnh, không phải vị trí
sân hay bản ghi `TrackingRow`. Video/ảnh mẫu không được commit.

Kết quả kiểm tra cuối với phiên bản hiện tại:

| Nhãn thật | Dự đoán A | B | referee | unknown | Tổng |
|---|---:|---:|---:|---:|---:|
| A | 8 | 0 | 0 | 1 | 9 |
| B | 0 | 9 | 0 | 2 | 11 |
| referee | 0 | 0 | 3 | 0 | 3 |
| unknown | 0 | 1 | 0 | 4 | 5 |

- Chính xác chung: 24/28 = 85,71%.
- Chính xác phân đội trên mẫu A/B, tính `unknown` là sai: 17/20 = 85%.
- Trọng tài: precision và recall đều 3/3; chỉ có ba mẫu, chưa đủ kết luận rộng.
- Đây là phân loại màu trên box đã chọn, không đo mAP detection, IDF1 tracking
  hay tỷ lệ phát hiện đủ người trong toàn bộ video.

## Chạy và nghiệm thu

Từ gốc repository, dùng môi trường CV/CUDA theo `CV_TRACKING.md`:

```powershell
$env:YOLO_CONFIG_DIR = (Resolve-Path data/processed).Path
$env:MPLCONFIGDIR = Join-Path $env:YOLO_CONFIG_DIR '.matplotlib'
.\.venv\Scripts\python.exe -m backend.cv.team_classifier data/raw/vid1.mp4 --samples docs/fixtures/vid1_team_samples.json --report data/processed/team_evaluation_new.json
.\.venv\Scripts\python.exe -m backend.cv.track_video data/raw/vid1.mp4 data/processed/vid1_teams_new.mp4 --weights data/raw/yolo11n.pt --device 0 --chunk-seconds 10 --team-samples docs/fixtures/vid1_team_samples.json
pytest -v
```

Tên đầu ra phải mới để tránh ghi đè. Muốn xem lại tập phát triển, thêm
`--split development` vào lệnh đánh giá và dùng tên report mới.
Khi dùng clip khác, cần bộ mẫu hiệu chỉnh/đánh giá mới theo cấu trúc fixture.

## Giới hạn cần giữ khi bàn giao

- Áo xanh giống cỏ, áo gần trắng/đen, che khuất và motion blur có thể gây sai.
- Thủ môn mặc khác màu và người ngoài sân mặc giống màu đội chưa được xử lý
  bằng ngữ cảnh. Trên tập phát triển, 4/13 mẫu `unknown` bị nhầm trọng tài;
  không được suy từ 3/3 mẫu kiểm tra cuối rằng lỗi này đã được giải quyết.
- Nhãn ảnh chưa được người gán nhãn độc lập rà soát; chưa có bộ test nhiều trận.
- Không thay đổi ngưỡng theo kết quả tập kiểm tra rồi báo lại cùng điểm như
  một phép đo độc lập; các thay đổi sau cần bộ kiểm tra mới.

Tham khảo API: [scikit-learn KMeans](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html),
[supervision annotators](https://supervision.roboflow.com/0.26.1/detection/annotators/).

## Clip mới: áo trắng và áo sẫm — 22/10/2026

- Nguồn gốc mới: 3077 frame, 1280 × 720, 60 FPS, 51,28 giây; SHA256
  `11f23eead918e838cb39fdb1ef98179dc93f86574fdb6d38bb6cd8ced3e01ed1`.
- Có giao diện OBS đầu/cuối và camera lia. Tạo bản thử từ frame 600 đến trước
  frame 2400 (giây 10–40), ghi MP4V bằng OpenCV 5.0.0, giữ nguyên 720p/60 FPS:
  `data/processed/clip_11f23eea/vid1_11f23eea_clean.mp4`.
  SHA256 bản cắt: `86f6f04ce05ac464269dfa4d831bef0c12c3654acdd2fa3c1b6379f864597b2e`.
  File gốc và media kết quả cũ không bị ghi đè. Media không được commit;
  nếu tái tạo bản cắt khác bitstream, phải kiểm tra lại lineage và bộ nhãn.
- Người dùng xác nhận A áo trắng, B áo sẫm/đen, trọng tài xanh nhạt. Trợ lý
  trọng tài cùng màu áo được xếp nhóm referee; staff/quay phim là unknown.

Fixture mới `docs/fixtures/vid1_11f23eea_team_samples.json` chọn
`"feature_mode": "foreground"`. Chế độ này giữ pixel ít bão hòa và tối,
không nhầm toàn bộ áo trắng/đen là thiếu màu. Vẫn loại cỏ theo hue 35–85,
saturation tối thiểu 40, nhưng chỉ khi value nằm trong [100, 240); pixel tối
được giữ vì áo đen bị ám xanh do cỏ/nén video. Chấp nhận box tối thiểu 8 × 16
pixel và tối thiểu 8 pixel áo hợp lệ; mẫu quá nhỏ trả unknown. K-means, màu
trọng tài và ngưỡng khoảng cách vẫn như trước. Không có khóa feature_mode thì
giữ chế độ chromatic cũ với các ngưỡng cũ.

Fixture có 134 box quan sát ảnh: 22 hiệu chỉnh tại frame 0/60 (10 A, 10 B,
2 referee); 45 phát triển tại frame 300/900; 67 kiểm tra tại frame
600/1200/1500. Frame tính từ bản cắt. Một proposal gần trùng ID 90 bị loại
trước đánh giá; mẫu hiệu chỉnh chọn người trên sân có áo nhìn rõ. Không dùng
nhãn tập kiểm tra để fit hoặc chỉnh ngưỡng. Nhãn từng box chưa được người
gán nhãn độc lập rà soát; cùng clip có người lặp lại.

| Nhãn thật | Dự đoán A | B | referee | unknown | Tổng |
|---|---:|---:|---:|---:|---:|
| A | 27 | 0 | 0 | 0 | 27 |
| B | 0 | 27 | 0 | 0 | 27 |
| referee | 0 | 0 | 4 | 0 | 4 |
| unknown | 0 | 3 | 1 | 5 | 9 |

Đúng chung 63/67 (94,03%); A/B 54/54; recall referee 4/4 nhưng precision
4/5 do một unknown bị nhầm referee. Đây là số đo sơ bộ có điều kiện trên box
đã chọn, không phải bằng chứng hệ thống phát hiện đủ hoặc phân loại đúng mọi
người trong video. Người ngoài sân mặc áo giống đội vẫn có thể bị nhầm.

Chạy lại trên bản cắt cục bộ, dùng tên đầu ra mới:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.team_classifier data/processed/clip_11f23eea/vid1_11f23eea_clean.mp4 --samples docs/fixtures/vid1_11f23eea_team_samples.json --report data/processed/clip_11f23eea/evaluation_repeat.json
.\.venv\Scripts\python.exe -m backend.cv.track_video data/processed/clip_11f23eea/vid1_11f23eea_clean.mp4 data/processed/clip_11f23eea/teams_repeat.mp4 --weights data/raw/yolo11n.pt --device 0 --image-size 1280 --chunk-seconds 10 --team-samples docs/fixtures/vid1_11f23eea_team_samples.json
```

Kích thước inference 1280 nhằm giữ người ở xa trong clip góc rộng. Camera
lia rõ nên không sử dụng một homography bốn điểm cố định cho toàn bộ đoạn;
bước 4 cần hiệu chuẩn phù hợp từng đoạn/góc máy trước khi tính tốc độ mét/giây.
