# Bước 3: phân loại đội theo màu áo

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
