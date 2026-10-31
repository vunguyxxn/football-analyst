# Hiệu chỉnh ngoại tuyến từ giao vạch sân

Ngày 31/10/2026, tiếp tục thử nghiệm sau nhánh conic. Mục tiêu là tăng
độ phủ và kiểm tra sai số ngoài giữa sân; chưa tích hợp upload/API.

## Cách làm

Nhánh `--method lines` trong `evaluate_pitch_keypoints.py` gọi module
`pitch_line_calibration.py`. Hypothesis conic/model chỉ gợi vùng tìm
đường trắng. Ma trận cuối được tính lại từ **bốn đường quan sát được**:

- Đường giữa sân: x=52,5m.
- Đường trước vùng cấm: x=16,5m hoặc x=88,5m.
- Biên xa và biên gần: y=68m và y=0m.

Hough + fitLine cần hỗ trợ pixel trắng gần cỏ. Đoạn hữu hạn chiếu vào
ảnh phải có ít nhất 30 mẫu và trải dài ≥120px; không dùng một mẩu vạch
ngắn để suy ra cả đường. Các giao điểm đại số của bốn đường có thể nằm
ngoài ảnh; đó là phép kéo dài đường đã quan sát, không phải mốc nhìn
thấy, cầu thủ khuất hay TrackingRow được bổ sung.

Bốn giao điểm tương ứng xác định homography trên sân 105×68m. Loại
giao gần song song, ma trận suy biến, horizon cắt sân và nghiệm phản
chiếu. Nếu hai phía sân cùng cho nghiệm hợp lệ, bản thử từ chối vì
chưa có bộ phân xử nhất quán; không chọn theo checkpoint mét.

Kiểm tra sau fit, không refit:

1. Chiếu vòng tròn giữa sân bán kính 9,15m về ảnh. Bỏ các mẫu cách đường
   đã fit ≤8px; cần ≥40 mẫu còn lại, median khoảng cách tới vạch trắng
   ≤4px và ≥65% mẫu cách pixel trắng ≤5px.
2. Kiểm hai cạnh ngang vùng cấm y=13,84m và y=54,16m, từ đường vùng cấm
   tới đường biên ngang. Cần ít nhất một cạnh nhìn thấy đủ ≥120px/
   ≥30 mẫu; các cạnh đủ điều kiện đều phải đạt cùng ngưỡng 4px/65%/5px.

Đường vùng cấm x cố định tham gia **fit** trong nhánh mới nên không còn
được gọi là bằng chứng kiểm riêng như nhánh conic v2. Cạnh y cố định
mới là bằng chứng bổ sung không dùng trong fit bốn đường. Vòng tròn
vẫn có tham gia tạo hypothesis tìm kiếm ban đầu; các kiểm tra này là
kiểm hình học nội bộ, không phải tập test độc lập về thống kê.

Giữ nguyên nhánh `keypoints`, nhánh `circle` và ngưỡng đối chiếu mét
1m. Tách `circle_hypothesis` khỏi guard của conic để tái sử dụng vùng
tìm; helper trả hypothesis chưa được nghiệm thu, không dùng để xuất
tọa độ sản phẩm. Kiểm hồi quy trên 66 dự đoán lưu của v2: toàn bộ
status/reason bằng nhau, vẫn 10 ứng viên, chênh ma trận lớn nhất 0.

## Kết quả development trên clip mẫu

Cùng Video Project15.mp4, cùng SHA256/weights và 17 checkpoint v4 như
các phiên trước; 66 ảnh được thử từ 1.571 frames, stride30 cộng mọi
checkpoint. Không sửa điểm đối chiếu để làm kết quả đạt.

| Nhánh | Ứng viên hình học | Checkpoint ≤1m | >1m | Chưa có ứng viên để đo |
|---|---:|---:|---:|---:|
| Conic v2 | 10/66 | 2/17 | 0/17 | 15/17 |
| Bốn đường, mới kiểm vòng tròn | 30/66 | 4/17 | 1/17 | 12/17 |
| Bốn đường + vòng tròn + cạnh ngang vùng cấm | 13/66 | 2/17 | 0/17 | 15/17 |

Lượt chẩn đoán ở giữa sai **1,541m tại frame601**, dù median lệch vòng
tròn chỉ 2px. Sau khi thêm kiểm cạnh ngang vùng cấm, ảnh này bị từ
chối. Bản cuối đạt frame1 (0,132m) và frame751 (0,388m). 11 ứng viên
khác chưa có đối chiếu mét; không gọi cả 13 ảnh là đạt sai số 1m.
Các ảnh được giữ khác v2, không có cơ sở nói mọi mặt đều tốt hơn v2.

Thử dẫn đường chỉ từ các keypoint thô thay vì hypothesis conic đã làm
độ phủ thấp hơn trên các mẫu này, nên không giữ biến thể đó trong mã
cuối. Không hạ ngưỡng confidence hay ngưỡng kiểm mét.

Đây vẫn là development trên cùng clip/nhãn agent đã xem; guard được
thiết kế sau khi quan sát lỗi. Không phải test mù hay accuracy độc lập.
Lượt cuối mất 31,66s cho quét clip và hiệu chỉnh các ảnh mẫu; không
dùng số này so FPS pipeline vì các lượt chạy không phải benchmark
hiệu năng được cô lập. Chưa kiểm độ trôi liên tục giữa các ảnh mẫu.

## Thử ba clip khác trong data/raw

Khóa hash nguồn và lịch lấy mẫu stride150 trước khi chạy. Chưa có mốc
mét, nên các manifest `pitch_crossclip_*_v1.json` ghi rõ unlabelled,
checkpoints rỗng; không tạo nhãn giả để có accuracy.

| Clip | Số frames | Ảnh thử | Vượt kiểm hình học |
|---|---:|---:|---:|
| Video Project12.mp4 | 1.408 | 10 | 0 |
| Video Project15 (1).mp4 | 1.077 | 8 | 0 |
| Video Project15 (2).mp4 | 2.428 | 17 | 1 |

Thiếu vòng tròn/giao biên, kiểm đường kính hoặc hình học không đạt vẫn
làm mất hypothesis ban đầu. Do đó, nhánh mới **chưa giải quyết độ phủ
cho video mới**. Không coi 0 ứng viên là accuracy0% hay video kém chất
lượng; chưa có nhãn chuẩn để kết luận nguyên nhân toàn diện.

Đã rà thêm bốn mốc trên **ảnh duy nhất được chọn**, frame900/30s của
clip15 (2): hai giao giữa sân/vòng tròn và hai giao cung phạt đền/vùng
cấm. Tọa độ được chốt từ ảnh thô trước khi so ma trận; giả định sai số
chọn điểm khoảng3px, sân105×68m chưa khảo sát. File:
`fixtures/pitch_crossclip_project15_2_visual_audit_v1.json`.

Sai số lớn nhất **0,292m**, trung bình0,252m; không dùng mốc này để fit
hoặc chỉnh ngưỡng. Đây là rà có điều kiện sau khi chọn ứng viên, không
phải 1/1 accuracy, không đại diện cho 35 ảnh thử hay toàn bộ video.
Ảnh minh họa cục bộ:
`data/processed/automatic_pitch_v3/crossclip-frame900-review.jpg`.

## Chạy và kiểm lại

Từ gốc repo, dùng trọng số đã khóa như tài liệu v1; chọn output mới:

```powershell
.\.venv\Scripts\python.exe -m backend.cv.evaluate_pitch_keypoints --source "data/raw/Video Project 15.mp4" --weights data/raw/pitch_keypoints/roboflow-football-pitch.pt --checks docs/fixtures/clip_f51735_landmark_checks_v4.json --output data/processed/automatic_pitch_v4/lines --stride 30 --device 0 --preprocess letterbox --method lines
.\.venv\Scripts\python.exe -m backend.cv.evaluate_pitch_keypoints --source "data/raw/Video Project 15 (2).mp4" --weights data/raw/pitch_keypoints/roboflow-football-pitch.pt --checks docs/fixtures/pitch_crossclip_project15_2_v1.json --output data/processed/automatic_pitch_v4/crossclip --stride 150 --device 0 --preprocess letterbox --method lines
.\.venv\Scripts\python.exe -m pytest -v --basetemp=.tmp/pytest_pitch_lines_verify
```

Báo cáo khóa đầu vào được lưu Git trong
`fixtures/pitch_line_calibration_benchmark_v3.json`. JSONL/ảnh cục bộ
dưới `data/processed/automatic_pitch_v3/`. Kiểm thử mới gồm khôi phục
phối cảnh từ cả hai phía sân, nghiệm phản chiếu/giao suy biến, vòng
tròn vắng, seed lệch, thiếu một biên, cạnh vùng cấm sai tỉ lệ, không
refit theo điểm kiểm và từ chối nhiều nghiệm. Không thêm dependency.

## Trạng thái

Giữ thử nghiệm ngoại tuyến. Không thay app upload, hiệu chỉnh tay,
DATA_CONTRACT, TrackingRow, heatmap hay báo cáo chiến thuật. Còn cần
tìm đường sân khi không đủ vòng tròn/biên, xử lý nhiều nghiệm nhất
quán, chuẩn hóa theo độ phân giải và đánh giá bằng nhãn kiểm riêng.
Chưa nối kiểm chuyển động camera liên tục hoặc xuất tọa độ cho cả đoạn.
