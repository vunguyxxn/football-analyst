# Xác minh và cải thiện mốc sân tự động

Phiên tiếp theo: [hiệu chỉnh từ giao vạch sân](AUTOMATIC_PITCH_LINES.md),
thêm kiểm cạnh vùng cấm và thử trên ba clip khác. Số liệu bên dưới
là lịch sử của nhánh conic v2.

Ngày 31/10/2026. Phạm vi được giao: xác minh checkpoint và cải thiện
thử nghiệm ngoại tuyến. Chưa tích hợp vào video tải lên; kết quả hiệu
chỉnh tay và DATA_CONTRACT giữ nguyên.

## Đã xác minh được gì

Đọc metadata **ngay trong checkpoint đã khóa SHA256**, không suy phiên
bản từ tên file. Checkpoint ghi ngày 07/05/2024, Ultralytics 8.2.10,
YOLOv8x-pose, 32 keypoints, train 600 epochs, imgsz 640, rect=false,
đường dẫn data.yaml thuộc `football-field-detection-9`. Đường dẫn này
là dấu vết huấn luyện, chưa phải manifest nhãn gốc đầy đủ.

[Bài hướng dẫn của Roboflow](https://roboflow.com/blog/camera-calibration-sports-computer-vision)
dùng dataset 14 và mô tả kéo giãn ảnh 640×640. Không coi checkpoint đã
tải là đúng bản model trong bài đó. Diagram chính thức xác nhận cấu
trúc các mốc quanh vòng tròn/đường giữa sân; thứ tự mảng lấy theo
[cấu hình đã khóa commit](https://github.com/cepat-ai/football-ai/blob/66a3f32ed6297fb3a06ec377448ef78e03b04db6/sports/configs/soccer.py).
Chuỗi labels của cấu hình không phải thứ tự index số tăng dần.

Đã đối chiếu ảnh thật ở frames 0/300/600/900/1200/1500. Nhánh mới chỉ
dùng nhóm mốc sau để **gợi vùng tìm kiếm**, không dùng tọa độ model
trực tiếp làm chuẩn mét:

| Index trong model, từ 0 | Số hiển thị | Vai trò |
|---|---|---|
| 13 | 14 | Gần giao đường giữa sân với biên xa |
| 14, 15 | 15, 16 | Hai giao đường giữa sân với vòng tròn |
| 16 | 17 | Gần giao đường giữa sân với biên gần |
| 24 | 25 | Gợi hướng biên xa khi góc phải sân hiện rõ |
| 30, 31 | 31, 32 | Gợi kích thước vùng tìm vòng tròn |

Không có manifest nhãn nguyên gốc dataset 9 để chứng nhận toàn bộ
32 mốc. Các index 10/11/18/19 có ngữ nghĩa vạch còn mơ hồ; nhánh mới
không dùng chúng. Điểm trái/phải của ellipse trong ảnh không tự tương
ứng với hai điểm x=52,5±9,15m: phép chiếu phối cảnh không bảo toàn cực
trị ảnh. Hồ sơ xác minh: `fixtures/roboflow_pitch_checkpoint_verification_v1.json`.

## Phần đã cải thiện

Thêm `backend/cv/pitch_circle_keypoints.py`. Mô hình chỉ gợi vùng tìm
vòng tròn và hướng đường giữa sân; sau đó OpenCV tìm pixel trắng gần
cỏ, đường thẳng có hỗ trợ thực tế và ellipse của vạch vòng tròn.

- Lọc confidence ≥0,6, điểm hữu hạn và nằm trong ảnh.
- Fit đường giữa sân và biên bằng Hough + fitLine; không thêm giao
  biên nằm ngoài ảnh làm bằng chứng quan sát.
- RANSAC ellipse 700 lần, tối đa 4.000 pixel; cần ≥300 inlier, ≥10/24
  cung góc có hỗ trợ. Refit cả bề rộng vạch để tránh chỉ bám một mép sơn.
- Khôi phục phép chiếu từ conic và đường kính. Khi chỉ thấy một biên,
  dùng đúng một giao biên quan sát cùng hai giao vòng tròn để xác định
  projectivity trên đường kính; không điền biên khuất. Nếu thấy cả hai,
  giữ kiểm tra đường kính ≤3px của `circle_matrix` hiện có.
- Sân 105×68m, vòng tròn bán kính 9,15m. Loại ma trận suy biến, horizon
  cắt sân, prior/refit bất hợp lý hoặc thiếu bằng chứng.

Một vòng tròn khớp tốt vẫn có thể cho tỉ lệ sai ở xa giữa sân. Vì thế
thêm bước **kiểm tra vạch vùng cấm, không refit**: chiếu đường x=16,5m
hoặc 88,5m, y=13,84…54,16m về ảnh. Cần đoạn nhìn thấy ≥120px và ≥30
mẫu, median khoảng cách tới pixel trắng ≤4px, ≥65% mẫu cách vạch ≤5px.
Không nhìn được vạch này thì giữ trạng thái thiếu kiểm chứng, không
cho qua. Bằng chứng này tách khỏi vòng tròn/đường giữa sân dùng để fit,
nhưng chưa phải đánh giá độc lập về chuyên môn hay kích thước sân.

Nhánh RANSAC keypoints cũ giữ nguyên ngưỡng và mặc định CLI. Đây là
phương pháp conic khác có đủ ràng buộc hình học riêng, không giảm yêu
cầu 6 điểm của nhánh cũ xuống 3 để ép kết quả đạt.

## Số liệu trên cùng clip mẫu

Video/weights/reference giữ nguyên hash ở báo cáo v1. Mỗi lượt đọc đủ
1.571 frames, thử cùng 66 ảnh: stride 30 cộng 17 checkpoint v4.

| Phương pháp | Ứng viên hình học | Checkpoint ≤1m | Checkpoint >1m | Không có ứng viên để đo |
|---|---:|---:|---:|---:|
| Keypoints v1, letterbox | 0/66 | 0/17 | 0/17 | 17/17 |
| Conic thử ban đầu, chưa kiểm vạch vùng cấm | 53/66 | 8/17 | 4/17 | 5/17 |
| Conic cuối, refit vạch và kiểm vùng cấm | 10/66 | 2/17 | 0/17 | 15/17 |

Lượt giữa là chẩn đoán development, không phải phiên bản để sử dụng.
Bản cuối từ chối 31 ảnh thiếu hỗ trợ vạch vùng cấm, 12 ảnh không thấy
đủ vạch đó, 5 ảnh không tìm được đường trắng, 4 thiếu seed, 2 refit
ellipse vượt prior, 1 thiếu giao biên và 1 horizon cắt sân.

Hai checkpoint bản cuối:

| Frame | Thời điểm | Sai số lớn nhất với mốc nội bộ |
|---|---:|---:|
| 601 | 20,033s | 0,977m |
| 1350 | 45,000s | 0,200m |

Trong 10 ứng viên, 8 ảnh khác chưa có mốc tham chiếu mét; không được
coi là đã đạt 1m. 15 checkpoint bị từ chối không được tính thành pass.
Không suy ra accuracy 100% từ hai lần đạt. Frame 601 còn sát ngưỡng.
Ngưỡng đối chiếu mét vẫn là 1m, không fit lại theo điểm tham chiếu.

Đã xem lỗi và thiết kế guard trên chính clip này; các điểm kiểm là
nhãn rà ảnh nội bộ của agent, tương quan theo thời gian và giả định
sân 105×68m. Đây là kết quả development/hồi quy, **không phải test mù
hay ground truth độc lập**. Chưa kiểm tra tính liên tục/độ trôi giữa
các ảnh mẫu. Chưa xuất TrackingRow, heatmap, quãng đường hoặc kết quả
chiến thuật từ các ứng viên này.

Ảnh minh họa cục bộ ở
`data/processed/automatic_pitch_v2/frame1350-review.jpg`: phía trên là
seed model; dưới là vòng tròn khớp vạch xanh lá, đường chiếu xanh cyan,
hai mốc kiểm màu tím. Sai số 0,200m chỉ áp dụng các mốc của frame này.

## Chạy lại và kiểm thử

Từ gốc repo; cần video và checkpoint cục bộ như tài liệu v1. Chọn một
output mới, không ghi đè kết quả đã có:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.evaluate_pitch_keypoints --source "data/raw/Video Project 15.mp4" --weights data/raw/pitch_keypoints/roboflow-football-pitch.pt --checks docs/fixtures/clip_f51735_landmark_checks_v4.json --output data/processed/automatic_pitch_v3/check --stride 30 --device 0 --preprocess letterbox --method circle
.\.venv\Scripts\python.exe -m pytest -v --basetemp=.tmp/pytest_pitch_verification
```

Kết quả cuối: `data/processed/automatic_pitch_v2/verified/frames.jsonl`
và `report.json`. Bản báo cáo ban đầu và cuối đã lưu Git trong
`fixtures/clip_f51735_automatic_pitch_benchmark_v2.json`. Báo cáo ghi
riêng thời gian predict và hiệu chỉnh; không lấy FPS predict làm FPS
pipeline. Không thêm thư viện, cài lại Torch hoặc gửi video lên cloud.
Lượt cuối mất 35,94s cho việc quét clip và hiệu chỉnh 66 ảnh; predict
trung bình sau lần đầu 89,00ms/ảnh, hiệu chỉnh trung bình 361,57ms/ảnh.
VRAM tensor PyTorch cao nhất 384,71MiB, không phải tổng VRAM driver.

Test mới kiểm khôi phục camera phối cảnh với một biên từ cả hai phía,
thiếu pixel/seed, sai phía biên, đường không cắt vòng tròn, ảnh tổng
hợp có seed lệch, vạch vùng cấm đúng/sai và trường hợp fit vòng tròn
rất tốt nhưng tỉ lệ ở xa sai. Không nới ngưỡng để làm test đạt.

## Trạng thái và việc còn lại

Đã có tiến bộ ở việc tìm mốc và từ chối phép chiếu sai, nhưng độ phủ
còn thấp: chưa đủ thay hiệu chỉnh tay trong ứng dụng. Cần tập clip và
nhãn kiểm riêng, thêm ràng buộc giao vạch để tăng độ phủ, kiểm độ nhạy
của conic khi thiếu nhiều vòng tròn, rồi mới nối kiểm chuyển động
camera liên tục. Chưa thực hiện các bước tích hợp đó trong phiên này.
Các ngưỡng pixel đang kiểm trên độ phân giải của clip mẫu, chưa được
nghiệm thu cho mọi độ phân giải, ánh sáng hoặc góc quay.
