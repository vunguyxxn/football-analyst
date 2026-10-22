# Kiểm tra clip lia máy — 22/10/2026

## Kết luận

Baseline bù chuyển động camera chạy được trên đoạn 5 giây đã chọn, nhưng
chưa nghiệm thu độ chính xác quãng đường/tốc độ. Sai số hình học theo mốc
quan sát còn cỡ mét ngay ở frame hiệu chỉnh; không coi trạng thái `tracked`
hoặc sai số RANSAC nhỏ là bằng chứng tọa độ sân chính xác.

Không sửa mã nguồn thuật toán, không nới ngưỡng sau khi xem kết quả.

## Nguồn và phương pháp

- Nguồn: `data/processed/clip_11f23eea/vid1_11f23eea_clean.mp4`,
  SHA256 `86f6f04ce05ac464269dfa4d831bef0c12c3654acdd2fa3c1b6379f864597b2e`.
  1280 × 720, 60 FPS. Frame 600–900 bao gồm hai đầu, 301 ảnh, 300 bước
  chuyển động, tương ứng giây 20–25 video gốc (bản cắt bắt đầu ở giây 10).
- Frame chọn tay: 600. Mốc: góc sân trái phía xa, góc phía xa của đường
  trước vùng cấm trái, hai giao đường giữa sân với hai đường biên dọc.
- Fixture tại `docs/fixtures/vid1_11f23eea_homography_check.json` lưu các
  cặp tọa độ và provenance. Điểm ảnh do agent quan sát ảnh, chưa được người
  gán nhãn độc lập xác nhận. Không chạy thao tác click GUI trong lượt này.
- Giả định sân thực 105 × 68 m, chưa xác minh kích thước sân cụ thể trong
  video. Vùng cấm dùng khoảng sâu 16,5 m và rộng 40,32 m; vòng giữa sân bán
  kính 9,15 m theo [IFAB Law 1](https://theifab.com/laws/latest/the-field-of-play/).
  Do đó góc vùng cấm phía xa là `(16.5, 54.16)` trong hệ chuẩn đang dùng.
  Đây là giả định hình học cần xác minh, không phải phép đo thực địa.
- Giữ nguyên `CameraMotion`, YOLO11n thật, CUDA device 0, inference 1280,
  person confidence 0,1; loại bbox person trước ước lượng chuyển động.
  Lượt này chỉ đánh giá camera/mốc sân, không chạy ByteTrack hay tính chỉ số
  cầu thủ. Mỗi frame xử lý riêng, không giữ ảnh toàn clip trong RAM.
- Hai giao điểm vòng tròn với đường giữa sân là mốc kiểm tra hình học ở
  frame 600, 750, 900; không dùng fit ma trận. Hai giao đường biên được kiểm
  tra ở frame 750, 900 để đánh giá duy trì mốc theo thời gian; chúng thuộc
  loại mốc đã fit ở frame 600, không phải kiểm tra hình học độc lập hoàn toàn.
  Mốc kiểm tra không dùng để tinh chỉnh bộ 4 điểm hay thuật toán/ngưỡng.

## Kết quả

| Hạng mục | Kết quả |
|---|---:|
| Mốc hiệu chỉnh tay | 1 frame |
| Bước camera `tracked` | 300/300 |
| Mất dấu | 0 trong đoạn thử |
| Inlier ít nhất mỗi bước | 34 |
| Tỷ lệ inlier nhỏ nhất | 90,32% |
| Diện tích bao điểm nhỏ nhất / ảnh | 20,41% |
| Sai số median RANSAC lớn nhất giữa hai frame | 0,387 px |
| Video diagnostic đọc lại | đủ 301 frame |

Sai số dưới đây là khoảng cách Euclid trong hệ sân giả định, dựa trên điểm
ảnh được gán nhãn bằng mắt; chưa phải ground truth đo đạc.

| Mốc kiểm tra vòng tròn | Frame | Sai số mét |
|---|---:|---:|
| Phía xa | 600 | 0,95 |
| Phía gần | 600 | 1,24 |
| Phía xa | 750 | 0,77 |
| Phía gần | 750 | 1,24 |
| Phía xa | 900 | 1,35 |
| Phía gần | 900 | 1,62 |

6 điểm vòng tròn: trung bình **1,20 m**, lớn nhất **1,62 m**.
4 điểm duy trì giao đường biên ở frame 750/900: trung bình **0,54 m**,
lớn nhất **1,02 m**. Không trộn hai nhóm để tuyên bố một con số độ chính xác.

Các lỗi ban đầu 0,95–1,24 m cho thấy hiệu chỉnh ban đầu/giả định sân đã có
sai số. Sai lệch ở frame 900 có thể gồm trôi tích lũy và nhiễu chọn điểm.
Chưa tách định lượng từng nguyên nhân. Đây là một đoạn ngắn, góc rộng,
không có chuyển cảnh trong mẫu; chưa suy rộng sang cả clip hoặc trận khác.

## Artifact và chạy lại

Kết quả cục bộ, không commit video/ảnh:

```text
data/processed/clip_11f23eea/homography_check_600/
  calibration.json
  camera_quality.jsonl     # có ma trận và bbox từng frame của lượt kiểm tra
  summary.json
  evaluation.json         # từng điểm, tọa độ chiếu và sai số
  diagnostic.mp4
  check_600.jpg
  check_750.jpg
  check_900.jpg
```

Ảnh check: đỏ là sân dự đoán (vòng tròn/mốc); xanh lơ là điểm ảnh kiểm tra
được quan sát bằng mắt. Các ảnh đầu vào/overlay không thay đổi nguồn video.
Script chạy khảo sát nằm ở `.tmp/check_camera_real.py` và
`.tmp/evaluate_camera_check.py` trong workspace hiện tại, không phải lệnh
được đóng gói cho fresh checkout. Fixture và các tham số ở trên cho phép
chạy lại chế độ sản phẩm bằng CLI sẵn có (tên đầu ra phải mới):

```powershell
$env:YOLO_CONFIG_DIR = "$PWD\data\processed"
$env:MPLCONFIGDIR = "$PWD\.tmp\matplotlib"
.\.venv\Scripts\python.exe -m backend.cv.track_video data/processed/clip_11f23eea/vid1_11f23eea_clean.mp4 data/processed/clip_11f23eea/pitch_check_full.mp4 --weights data/raw/yolo11n.pt --device 0 --image-size 1280 --calibration docs/fixtures/vid1_11f23eea_homography_check.json --pitch-output data/processed/clip_11f23eea/pitch_check_full --compensate-camera
```

Lệnh này đọc toàn bản cắt 1800 frame, nhưng chỉ hiệu chỉnh phạm vi 600–900;
ngoài phạm vi đó không xuất tọa độ. Lệnh CLI toàn bản cắt chưa chạy trong
lượt khảo sát này; video diagnostic 301 frame đã được chạy và đối chiếu.

## Việc tiếp theo

Rà soát điểm hiệu chỉnh ở ảnh phóng lớn và xác minh kích thước sân. Dùng
các điểm kiểm tra hiện tại làm dữ liệu phát triển nếu chỉnh hiệu chỉnh,
rồi chọn frame/mốc kiểm tra mới để đánh giá cuối; không báo lại chúng như
tập kiểm tra chưa từng thấy. Sau đó kiểm tra thêm các đoạn lia/zoom khác,
khoảng mất dấu và chuyển cảnh trước khi mở rộng ra toàn clip hoặc tính
chỉ số cầu thủ. Chưa cần yêu cầu đổi sang camera cố định.
