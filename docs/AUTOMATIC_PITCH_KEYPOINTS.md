# Thử nghiệm nhận diện mốc sân tự động

Ngày31/10/2026, người dùng yêu cầu bắt đầu ưu tiên nghiên cứu thứ nhất
sau đánh giá cepat-ai/football-ai. Phạm vi: chương trình ngoại tuyến,
chưa tích hợp vào upload/API và chưa thay hiệu chỉnh tay.

## Kết quả hiện tại

Đã chạy checkpoint thật trên RTX3050 6GB với Video Project15.mp4,
1920×1080,30fps,1571frames. Lấy một ảnh mỗi30frames và thêm toàn bộ17
checkpoint đang hoạt động trong fixture v4:66ảnh khác nhau mỗi lượt.

| Chỉ tiêu | Kéo giãn640×640 | Giữ tỉ lệ/letterbox640 |
|---|---:|---:|
| Ảnh thử | 66 | 66 |
| Thiếu ít nhất6 mốc tin cậy trong ảnh | 21 | 3 |
| Không đủ số/tỉ lệ inlier RANSAC | 45 | 52 |
| Không đạt kiểm tra bỏ từng điểm | 0 | 11 |
| Homography ứng viên vượt mọi kiểm tra hình học | 0 | 0 |
| Checkpoint có homography để đánh giá sai số mét | 0/17 | 0/17 |
| Lần dự đoán đầu, giây | 2,765 | 1,812 |
| Trung bình65 lần sau, mili giây | 79,50 | 49,42 |
| VRAM tensor được PyTorch cấp phát cao nhất, MiB | 385,23 | 384,71 |

Số liệu hiệu năng là một lần chạy trên các ảnh lấy mẫu, bao gồm gọi
predict/tiền xử lý/đồng bộ GPU; không phải tốc độ toàn pipeline video.
VRAM này không phải tổng bộ nhớ GPU mà driver/các tiến trình sử dụng.
Môi trường: torch2.8.0+cu128, Ultralytics8.3.221, Windows/Python3.11.

**Chưa đạt để đưa vào sản phẩm.** Không có số đo sai số mét hợp lệ để
công bố;0/66 là tỉ lệ vượt bộ kiểm tra trên mẫu này, không phải mAP
hoặc độ chính xác tổng quát của mô hình.17checkpoint chưa được đánh giá
sai số vì không có ứng viên hợp lệ, không được tính thành17 lần đạt.
Quan sát ảnh900 cho thấy nhiều mốc vẫn lệch vạch dù confidence cao.
Chưa đủ bằng chứng quy lỗi riêng cho model, domain hay template nhãn.
Không hạ ngưỡng cho vừa kết quả; không xuất tracking/heatmap/quãng đường.

## Nguồn và khóa đầu vào

- Tham khảo thứ tự32 vertices của SoccerFieldConfiguration trong
  [cepat-ai/football-ai, commit66a3f32](https://github.com/cepat-ai/football-ai/blob/66a3f32ed6297fb3a06ec377448ef78e03b04db6/sports/configs/soccer.py),
  có nguồn từ Roboflow. Giữ thông báo tại
  [giấy phép MIT](third_party/roboflow-sports-LICENSE.txt).
- Trọng số được nhà cung cấp liên kết trong
  [setup.sh chính thức](https://github.com/roboflow/sports/blob/main/examples/soccer/setup.sh):
  [football-pitch-detection.pt](https://drive.google.com/uc?id=1Ma5Kt86tgpdjCTKfum79YMgNnSjcoOyf).
  Chỉ tải checkpoint này về cục bộ, không chạy setup/notebook bên ngoài.
  File140212306bytes, SHA256
  `28f68f7c4056d6d9b137efd2e7ab5f3c494039380c63831649126ced25628b36`.
  Không đưa weights vào Git; quyền code MIT không tự chứng minh quyền
  phân phối mọi weights/dataset. Không khẳng định version dataset của
  checkpoint khi nguồn tải chưa khóa version đó.
- Video SHA256:
  `f51735a042b493eba3cced891209fe1b6beb20ca80e20c340c7ede51900495d0`.
- Tham chiếu: `docs/fixtures/clip_f51735_landmark_checks_v4.json`, SHA256
  `830f11a7c94a3d72a99a4720cfefc77eea0b2547b162431c2054b554a4b73685`.
  Chỉ17checkpoints trong trường `checkpoints`; không lấy điểm599 đã
  loại để thay đổi fit hay đánh giá. Đây là nhãn rà ảnh nội bộ của agent,
  không phải ground truth độc lập hay kích thước sân đã khảo sát.

## Ánh xạ và bộ kiểm tra

`backend/cv/pitch_keypoints.py` định nghĩa layout
`sports32-105x68-bottom-left-v1`: lấy thứ tự mảng vertices, không sắp
lại theo chuỗi labels của repo. Nhãn hiển thị đánh số index+1. Sân dùng
105×68m, gốc trái dưới/y hướng lên; vùng cấm16,5×40,32m, cầu môn5,5×18,32m,
chấm phạt đền11m, bán kính vòng tròn9,15m. Không scale toàn bộ template
120×70m. Điểm11/12/19/20 giữ ngữ nghĩa template: trên đường vùng cấm,
cùng tung độ mép vùng cầu môn; không tự đổi thành giao cung phạt đền.
Cần xác minh thêm tài liệu nhãn checkpoint trước khi coi mapping đã
được kiểm chứng đầy đủ trên dataset gốc.

Chính sách cố định trước lượt benchmark đầu:

1. Chỉ dùng điểm hữu hạn, nằm trong ảnh, confidence≥0,6; cần ít nhất6.
2. Loại điểm ảnh trùng/gần nhau<2px; hull ảnh≥2% ảnh và hull sân≥3% sân.
3. RANSAC sân→ảnh với ngưỡng5px; ít nhất6 inlier và tỉ lệ≥70%; kiểm lại
   độ phủ trên inlier. Nghịch đảo mới thành ảnh→mét.
4. Loại horizon cắt qua sân và ma trận không khả nghịch/hữu hạn.
5. Fit lại lần lượt bỏ một inlier, dự đoán điểm bị bỏ; median≤4px,
   max≤12px. Đây chỉ là tính nhất quán của dự đoán, chưa phải accuracy.
6. Nếu có ứng viên tại checkpoint, đối chiếu điểm ảnh đã rà với tọa độ
   tham chiếu, max≤1m. Điểm đối chiếu không tham gia fit/refit.

Không có ma trận identity dự phòng, không điền điểm khuất. Chưa kiểm
tính ổn định giữa các ảnh mẫu, chưa chạy CameraMotion/LandmarkGuard
liên tục; một ảnh vượt kiểm tra cũng không cấp quyền suy ra cả đoạn.
Không đổi DATA_CONTRACT hoặc thêm dependency/API cloud.

## Chạy lại

Đặt đúng checkpoint nói trên tại
`data/raw/pitch_keypoints/roboflow-football-pitch.pt`. Lệnh không tải
model ngầm; sai hash, sai video/fixture hoặc output đã tồn tại sẽ dừng.
Từ thư mục gốc dự án, chọn output mới mỗi lần:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.evaluate_pitch_keypoints --source "data/raw/Video Project 15.mp4" --weights data/raw/pitch_keypoints/roboflow-football-pitch.pt --checks docs/fixtures/clip_f51735_landmark_checks_v4.json --output data/processed/automatic_pitch_v2/stretch --stride 30 --device 0 --preprocess stretch
.\.venv\Scripts\python.exe -m backend.cv.evaluate_pitch_keypoints --source "data/raw/Video Project 15.mp4" --weights data/raw/pitch_keypoints/roboflow-football-pitch.pt --checks docs/fixtures/clip_f51735_landmark_checks_v4.json --output data/processed/automatic_pitch_v2/letterbox --stride 30 --device 0 --preprocess letterbox
.\.venv\Scripts\python.exe -m pytest -v --basetemp=.tmp/pytest_auto_pitch_verify
```

Mỗi lượt ghi `frames.jsonl` (mốc/confidence thô, lý do từ chối, ma trận
ứng viên nếu có) và `report.json` (hash/chính sách/số liệu). Đọc video
tuần tự, chỉ giữ một ảnh/kết quả trong RAM. JSON nghiên cứu nội bộ,
không phải TrackingRow hay hợp đồng API mới. Không ghi đè job đã xuất.

Kết quả cục bộ đã chạy nằm dưới
`data/processed/automatic_pitch_v1/evaluation/` (stretch) và `letterbox/`.
Bản sao hai báo cáo được lưu trong Git tại
`docs/fixtures/clip_f51735_automatic_pitch_benchmark_v1.json`.
`evaluation/report.json` được tạo trước khi bổ sung lựa chọn CLI
letterbox nên trường preprocess ghi đầy đủ tên phép kéo giãn thay vì
chuỗi ngắn `stretch`; các ngưỡng và hình học không đổi.

## Việc cần làm trước khi tích hợp

Xác minh ngữ nghĩa32 nhãn từ dữ liệu gốc; rà độ bám vạch trên ảnh mẫu và
thêm tập kiểm độc lập cho nhiều góc quay. Sau đó thử ràng buộc đường
thẳng/vòng tròn hoặc fine-tune có split kiểm riêng. Chỉ khi đạt chất
lượng mới nối với kiểm tra chuyển động camera và rà độ trôi liên tục;
giữ hiệu chỉnh tay khi thiếu mốc hoặc chất lượng thấp.

Bản này cung cấp công cụ và kết quả nghiên cứu có thể chạy lại. Chưa
giải quyết tự động hiệu chỉnh sân cho video mới tải lên.
